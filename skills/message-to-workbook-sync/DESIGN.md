# Design: Message to Workbook Sync

> **Implementation status: mixed.** The generic runtime (ingest, dedupe, write, notify) is implemented; most capability-specific mechanisms below are target design. See [docs/capability-matrix.md](../../docs/capability-matrix.md) before relying on any invariant here.

## Architecture

```
 [ChannelReader] --> raw messages (sender, timestamp, shape)
        |
 [MessageParser] x N shapes --> raw records
        |
 [Normalizer] alias map + glued-value splitting + numeric cleanup
        |
 [OwnershipResolver] mapping > record field > source channel
        |
 [Deduplicator] key (business_period, entity, group), latest wins
        |
 [WorkbookLocator] file -> sheet -> row -> target cells
        |
 [Backup] checkpoint --> [CellWriter] surgical part-level replace --> [Verifier]
        |
 [Aggregator] per-group summaries --> [PolicyHooks] --> [NotificationAdapter]
        |
 change-log.md + state.json + notifications.log
```

## Parsing and normalization

### Canonicalization steps

1. Trim, remove whitespace inside field names, unify full-width and half-width separators.
2. Split a multi-record message on a configured boundary field.
3. Apply `alias_map` to resolve synonyms.
4. Detect glued `fieldvalue` strings by longest-prefix matching against the canonical field-name set, ordered by descending length.
5. Strip units and separators, then parse the remainder as a single numeric value.
6. Apply `normalization.empty_value_policy`.
7. Map canonical fields to target cells through `field_map`. Fields with no target are "ignored fields", recorded but not treated as failures.

### Glued-value splitting

Longest-prefix matching exists because some field names begin with a digit. Example: a field named `2-unit-count` followed by the value `2` produces the string `2-unit-count2`. Greedy numeric parsing would read the leading `2` as the value; correct behavior matches the whole field name first and parses only the trailing `2`.

Rules:

- Match canonical names in descending length order.
- The matched prefix is never shortened to make a numeric parse succeed.
- Write only when the remainder parses uniquely as one numeric value.
- If the remainder is ambiguous, skip the field, keep the cell value, and record an anomaly.

### Ambiguity policy

| Condition | Action | Anomaly escalation |
| --- | --- | --- |
| Synonym, spacing, punctuation or unit difference | Normalize and write | No |
| Glued value with a unique parse | Normalize and write | No |
| Present field with empty value | Apply configured empty-value policy | No |
| Missing optional field | Ignore field | No |
| Two numbers that cannot be separated | Skip field, keep cell value | Yes |
| No readable fields, or withdrawn message | Skip record | Yes |
| Unresolved entity ownership | Skip record, mark manual review | Yes, if configured |
| Missing or ambiguous business period | Skip record, mark manual review | Yes |

## Ownership precedence

| Priority | Source | Behavior on conflict |
| --- | --- | --- |
| 1 | `ownership.entity_to_group` | Overrides everything; log an ownership correction |
| 2 | Explicit group field in the record | Log a correction against priority 3 |
| 3 | Source channel inference | Used only when the record has no group field |

An entity absent from the mapping is never defaulted to the largest group. It is marked `unresolved` and excluded from aggregates and outbound summaries.

All aggregates, rankings, absence markers, policy hooks and notification content are computed after normalization and grouped by the resolved group. No outbound message combines two groups.

## Deduplication and correction

```
key = (business_period, entity, resolved_group)
```

- Within a run, sort records with the same key by source timestamp and keep the last.
- Compare the normalized value against the **current cell value**, not against a processed-keys list.
- Different value: overwrite, log `old -> new`, create a new pre-correction backup copy.
- Same value: log "no change", write nothing, make no backup.
- A correction may arrive after a period was closed. It still writes, updates that period's log and backup directory, and recomputes that period's aggregates. It never writes into a different period's row.
- A record with no period or an ambiguous period is not assigned the run's period by default.

## Surgical write strategy

The workbook is a package of parts. A full rewrite through a high-level library can discard custom parts, cached formula values and styles even when the visible cells look correct.

Required procedure:

1. Create a backup checkpoint of the whole file and verify it opens.
2. Read all package parts. Resolve the target sheet part through the workbook part and its relationships.
3. Modify only the target cells inside that sheet part, preserving cell attributes. Convert self-closing empty cells only when a value is being written.
4. Write every other part back byte-identically. Add a recalculation-on-load flag to the workbook part so formula cells recompute when opened, without editing those cells.
5. Write to a temporary file in the same directory, preserve permissions, then atomically replace the original path.
6. Verify: byte-compare every untouched part against the backup, reopen with formulas preserved, confirm the target values and confirm the backup opens.
7. On any verification failure, restore from the backup checkpoint.

Absence-marker styling is a separate operation. If it cannot be done at part level, use a library loaded with formulas preserved; never use a formula-stripping mode. Clear an existing marker before writing a late correction to that row.

## State machine

```
IDLE -> READ -> PARSE -> NORMALIZE -> RESOLVE -> DEDUPE -> BACKUP -> WRITE -> VERIFY -> LOGGED -> NOTIFIED
                                                     |          |          |
                                                     +----------+----------+--> SKIPPED / FAILED
```

Rounds add an outer loop:

```
ROUND_1 ... ROUND_N-1 : backfill and correct only
ROUND_N (final)       : full re-read -> absence markers -> aggregates -> summaries -> closed=true
```

- A run that finds the previous period unclosed finalizes it before the current round.
- The final round never reuses cached values from earlier rounds.
- `closed=true` does not block later corrections; it only prevents repeating finalization actions.
- Change logs append a section per round and are never overwritten.

## Notification tiers

| Tier | Trigger | Content | Idempotency |
| --- | --- | --- | --- |
| Run summary | Round made changes | Period, round, count of updated entities, manual-review count | One per period and round |
| Anomaly escalation | Ambiguous or unreadable record | Original field text, problem description, request for a corrected record, sender mention | One per source message identifier |
| Final aggregation | Final round | Per-group aggregates only, never merged across groups | One per period and group |
| Operational detail | Any run with changes or failures | Full detail including backup and log paths | One per period and round |

All outbound content excludes local machine paths, workbook file names and other groups' data, except the operational-detail tier. Mentions of all participants are disabled unless explicitly configured. Sender mentions use a structured mention element, not plain text.

A notification failure is logged as a degradation; it does not interrupt writes, roll back changes or trigger repeated retries.

## Policy hooks

Domain-specific rules such as rankings, thresholds, rewards, penalties, commentary or greeting text are injected here. They receive the final normalized per-group data and return optional messages. Constraints:

- A hook never changes workbook contents.
- A hook never merges groups.
- A hook never emits per-entity values unless the aggregation config allows it.
- A hook is disabled by default. No organization-specific rule is part of the blueprint.

## Failure matrix

| Stage | Failure | Behavior | Logged as |
| --- | --- | --- | --- |
| Read | Channel unavailable | Abort the run, no writes | `channel_read_failed` |
| Parse | Unknown shape | Record as unreadable, keep cells | `shape_unrecognized` |
| Normalize | Ambiguous value | Skip that field, escalate | `field_ambiguous` |
| Resolve | Entity not in mapping | Skip record, manual review | `ownership_unresolved` |
| Locate | File, sheet or row missing | Skip, never create | `target_not_found` |
| Backup | Copy or verification fails | Abort that workbook's write | `backup_failed` |
| Write | Atomic replace fails | Restore backup, abort that workbook | `write_failed` |
| Verify | Untouched part differs | Restore backup | `verify_failed` |
| Notify | Send fails | Log degradation, continue | `notification_degraded` |
| Schedule | Unexpected clock hour | Fallback round, never guess | `round_unmapped` |

## Extension points

| Interface | Must not do |
| --- | --- |
| `ChannelReader` | Read outside the allowlist |
| `MessageParser` | Silently ignore a configured shape |
| `Normalizer` | Guess an ambiguous value |
| `OwnershipResolver` | Default an unresolved entity to a majority group |
| `WorkbookLocator` | Create or rename a workbook |
| `CellWriter` | Touch formulas, subtotals, notes or other rows |
| `Aggregator` | Merge groups |
| `NotificationAdapter` | Send outside configured targets |
| `PolicyHook` | Write to the workbook |

## Testing checklist

- [ ] Both configured message shapes produce the same canonical field set.
- [ ] A glued value whose field name starts with a digit parses correctly.
- [ ] A synonym and a full-width separator normalize to the same field.
- [ ] An empty field follows the configured empty-value policy, not a hardcoded one.
- [ ] A same-value rerun writes nothing and creates no backup.
- [ ] A changed value creates a new pre-correction backup without overwriting an older one.
- [ ] A correction for an earlier period writes only that period's row, log and backup directory.
- [ ] An ownership conflict resolves to the mapping and is logged as a correction.
- [ ] An unresolved entity is never defaulted into a group.
- [ ] Every untouched package part is byte-identical after a write.
- [ ] Formula cells and cached values survive a write.
- [ ] Group A's summary never contains group B's data.
- [ ] The change log is append-only across three rounds.
- [ ] A notification failure does not roll back a successful write.
