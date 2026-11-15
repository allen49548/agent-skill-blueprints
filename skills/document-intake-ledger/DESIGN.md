# Design: Document Intake Ledger

## Architecture

```
 [ChannelReader] --> messages + attachments (sender identity preserved)
        |
 [DocumentClassifier] --> class + confidence
        |  unsupported class --> resubmission request, no value extraction
        v
 [Extractor] --> structured fields (value, timestamp, business key, description)
        |
 [AttributionResolver] --> entity / conflict / unresolved
        |
 [Deduper] L1 message id -> L2 content hash -> L3 perceptual hash -> L4 business key
        |  duplicate --> transparent report, no registration
        v
 [DetailSheetWriter] append-only, part-level, backup + verify + rollback
        |
 [Ledger.add] registered (only after verified write) or record_without_write
        |
 [TaskAdapter] one task per entity per run, editor + viewer
        |
 [NotificationAdapter] channel overview + operator detail
        |
 run log + backups + notifications.log
```

## Document classes

Classes are configuration, not code. Each class declares whether values may be extracted and what happens when the class is matched.

| Class | Extract values | Register in ledger | Additional action |
| --- | --- | --- | --- |
| `structured_evidence` | Yes | Yes | Normal flow |
| `unstructured_or_handwritten` | No | No | Resubmission request with a file reference and timestamp only |
| `text_only_claim` | No | No | Log as a skipped item |
| `non_document_image` | No | No | Ignore, not an anomaly |
| `low_confidence` | No | No | Manual review |

Low confidence, a missing timestamp, an altered document and an unresolvable sender all route to manual review. An operator may grant a one-off exception for a specific document, recorded as a run-level note; it never edits the class rules.

## Attribution

```
resolve(sender_id, sender_name, document_names, message_text)
    -> { entity, matched_by, is_new_entity, has_workbook, action }
```

| Case | Result |
| --- | --- |
| Sender identifier in `attribution.entity_map` | Mapped entity |
| Sender not mapped but valid channel identity | New entity from that objective identity; `record_without_write` if no workbook |
| Document or text name conflicts with sender | `conflict` -> manual review |
| Sender is an automated identity, owner, or an invalid name form | `unresolved` -> manual review |

Never assign a default entity. Never infer ownership from a channel name. The registry is elastic: reports include only entities that submitted documents in the period.

## Four-layer deduplication

| Layer | Key | Hit means |
| --- | --- | --- |
| L1 | Source message identifier | Same message replayed |
| L2 | Content hash of the document bytes | Same file posted again |
| L3 | Perceptual hash | Visually near-identical rendering |
| L4 | Business key | Same underlying real-world item |

Business key composition:

```
business_key = document_business_id + timestamp
if no document_business_id:
    business_key = entity + period + value + class + content_hash
```

Rules:

- Equal values alone never constitute a duplicate.
- L3 hit with a different business key is a false positive and does not block registration.
- The composite fallback includes the entity, so two entities with identical values are distinct.
- A duplicate verdict carries `original_created_at`, `original_status`, `original_value` and the original task reference.
- The original message identifier stays in the ledger. Entries are marked, never physically deleted.
- A resubmission while the original is still `registered` is the common case and must be reported explicitly as "already registered, no value added".

## Ledger schema

```
entries(
  entry_id, message_id, content_hash, perceptual_hash, business_key,
  entity, period, value, class, source_channel_id,
  status,              -- confirmed | registered | needs_material | duplicate | voided
  record_without_write,
  workbook_file, sheet,
  task_id, created_at, updated_at
)
```

Constraints:

- Append-oriented. No physical deletes.
- Unique index on `business_key` for non-voided entries.
- `balance(entity)` returns only `status = registered AND voided = 0`.
- Channel allowlists never appear in aggregation queries; grouping is by `entity`.

## Status state machine

```
   +---------------------------+
   |                           v
NEW --> REGISTERED --> CONFIRMED --> VOIDED (explicit only)
 |          |
 |          +--> DUPLICATE (terminal, never registered)
 +--> NEEDS_MATERIAL --> (manual review) --> NEW
```

| State | Counts as outstanding | Who transitions out |
| --- | --- | --- |
| `registered` | Yes, the only one | Editor completing the task |
| `confirmed` | No | - |
| `needs_material` | No | Manual review |
| `duplicate` | No | - |
| `voided` | No | Explicit operator action |

Only `registered` enters any outstanding total. This prevents duplicates and unsupported material from inflating totals.

## Append-only write strategy

The workbook is a package of parts. Adding one sheet requires changes to only a small set of parts; every other part must remain byte-identical.

1. Verify the target workbook already exists. If not, take the `record_without_write` path.
2. Create and verify a backup checkpoint of the whole file.
3. Reuse the canonical detail sheet if present; otherwise add exactly one sheet part and update only the minimum required package parts.
4. Append rows for newly registered records. Never touch existing cells, other sheets, formulas, comments, custom parts or cached values.
5. Write to a temporary file in the same directory and atomically replace the original path.
6. Verify: untouched parts byte-identical against the backup, workbook opens, appended row count and values match.
7. On failure, restore from the backup checkpoint and do not register the ledger entries.
8. Idempotency key is `message_id`; a rerun never appends the same row twice.

`record_without_write` still registers the ledger entry, creates a task and reports that a target must be assigned. It never creates a workbook file and never creates a backup.

## Task model

```
task(entity, period, entries) with
    editor  -> may edit and complete
    viewer  -> may view and comment only
```

- One task per entity per run, grouping that run's newly registered entries.
- Task description: entity, record count, total value, statistic window, action deadline, where the detail rows live, and a one-line permission note. No local paths.
- A missing viewer identifier is skipped silently and recorded in the run log; it is not an anomaly or a follow-up task.
- Completion polling marks the corresponding entries `confirmed` and emits a short acknowledgement to the submitter, idempotent per task identifier.
- Task links appear in both notification tiers.

## Notification tiers

| Tier | Trigger | Contains | Never contains |
| --- | --- | --- | --- |
| Channel overview | Every run, including no-change runs | One line per submitting entity with value and document dates, a total, viewer mention, task link | Ledger states, outstanding totals, period comparisons, record counts, business identifiers, file names, ledger paths, reasons for missing workbooks |
| Operator detail | Every run | Per-entity values and destinations, duplicate details with original time and status, anomalies, task links and deadlines, ledger state counts, log and backup paths | Nothing excluded; this is the audit channel |

A no-change run still sends a compact status line. A policy hook may add neutral tone text, disabled by default; it never adds operational fields.

The send layer must hard-block any per-entity private delivery flag, even if an older scheduled prompt still passes one. A blocked attempt is recorded as `blocked`, never downgraded to a channel message.

## Period aggregation

- Group by `entries.entity`, independent of channel allowlists. Retired channels' historical entries remain in scope.
- Include only entities with documents in the period; no zero-value padding and no "missing participants" note.
- Period membership: document timestamp, then a configured fallback, then registration timestamp. Never the run date.
- Split into `confirmed` and `registered`; only `registered` is outstanding.
- A comparison with the previous period appears only in the operator tier.
- Guard against sending the period report twice with a per-period marker.

## Failure matrix

| Stage | Failure | Behavior | Logged as |
| --- | --- | --- | --- |
| Read | Channel unavailable | Abort run, no writes | `channel_read_failed` |
| Classify | Unknown class | Treat as unsupported, request resubmission | `class_unrecognized` |
| Extract | Low confidence or missing timestamp | Manual review, no registration | `extraction_low_confidence` |
| Attribute | Conflict or unresolved sender | Manual review, no registration | `attribution_unresolved` |
| Dedup | L3 hit with different business key | Treat as false positive, continue | `perceptual_false_positive` |
| Dedup | L4 hit | Skip registration, report original entry | `duplicate_ignored` |
| Write | Target workbook missing | `record_without_write`, still register and task | `record_without_write` |
| Write | Backup or verification fails | Roll back, do not register | `write_failed` |
| Task | Creation fails | Record failure, still notify | `task_failed` |
| Notify | Any tier fails | Record reason, no loop retry | `notification_degraded` |
| Send guard | Per-entity private flag passed | Hard block | `private_delivery_blocked` |

## Extension points

| Interface | Must not do |
| --- | --- |
| `ChannelReader` | Read retired or non-allowlisted channels |
| `DocumentClassifier` | Extract values from unsupported classes |
| `Extractor` | Guess unreadable values |
| `AttributionResolver` | Assign a default entity |
| `Deduper` | Treat equal values as duplicates |
| `DetailSheetWriter` | Create a workbook, modify existing cells or other sheets |
| `Ledger` | Delete entries physically |
| `TaskAdapter` | Give a viewer edit permission |
| `NotificationAdapter` | Send per-entity private messages |
| `PolicyHook` | Add operational fields to the channel overview |

## Testing checklist

- [ ] An exact replay of one message registers once.
- [ ] A different business key with an identical value registers both records.
- [ ] A perceptual-hash hit with a different business key is not dropped.
- [ ] Two entities with identical values register two records.
- [ ] A duplicate report includes original registration time and current status.
- [ ] Only `registered` entries appear in outstanding totals.
- [ ] A missing workbook yields `record_without_write` and no new file.
- [ ] Every untouched package part is byte-identical after an append.
- [ ] A rerun never appends the same row twice.
- [ ] A viewer cannot complete a task or change a value.
- [ ] Both notification tiers are sent on a no-change run.
- [ ] An accidental per-entity private delivery flag is hard-blocked.
- [ ] Period aggregation includes historical entries from retired channels.

## Configurable input and output

The config separates **what** the pipeline works with from **how** it gets and delivers it.

- Top-level groups (`channels`, `document_classes`, `workbooks`, `ledger`, `tasks`, `notifications`, `safety`, `output`, ...) hold **parameters** and are the single source of truth.
- `adapters.input` and `adapters.output` hold **mechanism selection**: source family, read client and identity, document shapes, pull window, write target, notification channels, task backend, and per-tier renderers with field visibility.
- Every `*_ref` field is a pointer to a parameter group, not a copy of its value. Two sources of truth are never allowed to diverge.

The current state is `adapters.resolution = "declarative"`. The section is a contract, not a dispatcher: the reference pipeline runs its built-in default adapters and the config records exactly which defaults those are. Switching a `type` to an entry in `alternatives` requires implementing the matching interface from "Extension points" and adding a dispatcher. Until then, changing a `type` without an implementation must be rejected at startup. This is what keeps the default behaviour byte-for-byte identical while the configuration surface becomes explicit.

### Dimension coverage

| Dimension | Config path | Default |
| --- | --- | --- |
| Message source family | `adapters.input.source` | `channel_messages` |
| Read identity and client | `adapters.input.client` | registered client, explicit read identity, full pagination |
| Document shapes | `adapters.input.documents` | accepted classes plus a registered extractor |
| Pull window and incremental strategy | `adapters.input.window` | full-window rescan on every run |
| Write target | `adapters.output.write` | append-only detail sheet in an existing workbook |
| Notification channels | `adapters.output.notifications` | channel overview plus operator detail |
| Task backend | `adapters.output.tasks` | registered task adapter, one task per entity per run |
| Render format and field visibility | `adapters.output.rendering` | per-tier renderer registry and field allowlist |

### Switching an adapter

1. Implement the corresponding interface listed under "Extension points".
2. Register it under the relevant `alternatives` entry and set the `type` or adapter field.
3. Keep every `*_ref` pointer unchanged unless the new adapter genuinely needs different parameters.
4. Put real parameters into the referenced group, never into `adapters` itself.
5. Run in dry-run mode, then walk the failure matrix for the new path.

### Invariants that survive any adapter change

Switching an input or output mechanism must not change any of these: four-layer deduplication, the `registered`-only outstanding rule, `record_without_write`, backup plus verification plus rollback, the hard block on per-entity private delivery, and the rule that both notification tiers are sent on a no-change run.

### Additional tests

- [ ] Every `*_ref` resolves to an existing config path.
- [ ] No value inside `adapters` duplicates the value it references.
- [ ] A `type` outside `alternatives` is rejected at startup.
- [ ] A `hard_blocked` tier stays blocked even when a legacy delivery flag is passed.
- [ ] Enabling a new output adapter leaves the dedup and outstanding-total results unchanged.
