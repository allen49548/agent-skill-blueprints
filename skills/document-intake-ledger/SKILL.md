---
name: document-intake-ledger
description: Specification for extracting structured records from documents and images posted in allowlisted channels, attributing each record to an entity by sender identity, deduplicating through a layered ledger, appending rows to an existing workbook, driving a status state machine and issuing confirmation tasks with tiered notifications. Use when the same document may be submitted more than once and double-counting is the primary risk. Defines accepted document classes, attribution resolution, four-layer deduplication, record-without-write behavior, append-only surgical writes with backup and rollback, status states, task permission separation, two-tier notification and period aggregation. Do not use for updating fixed-layout cells, for computed results requiring an approval gate, or when every document arrives once through a trusted structured API.
agent_created: true
---

# Document Intake Ledger

## Purpose

Accept documents posted in channels, turn them into structured records, and guarantee that each underlying real-world item is accounted for exactly once. The ledger is the authority: a record is not "counted" until the ledger says it is new and the write has been verified.

The same pipeline supports periodic aggregation, a status state machine and confirmation tasks. This is a specification, not an implementation.

## When to use

- Documents or screenshots are submitted by multiple people in one or more channels.
- The same item can be submitted twice, on the same day or days later.
- A durable audit trail must explain why a duplicate added nothing.
- A record may exist even when its target workbook does not.
- Downstream confirmation is a task with permission separation between an editor and a viewer.

## When not to use

- Updating existing cells in a fixed-layout workbook: use the `message-to-workbook-sync` blueprint.
- Computed results that need an approver before delivery: use the `verified-batch-calculation` blueprint.
- Every document arrives exactly once through a trusted structured API; a ledger would be overhead.
- Documents must be modified in place. This blueprint is append-only.

## Core concepts

`entity`, `channel`, `workbook`, `recipient`, `run`, `ledger`, `record without write`, `idempotency key`, `backup checkpoint`, `policy hook`. Definitions are in `docs/vocabulary.md`.

## Quick start (runnable)

This package is self-contained. From this directory:

```bash
python3 run.py demo      # zero configuration, bundled sample data
python3 run.py setup     # interactive wizard -> config.json
python3 run.py doctor    # validate
python3 run.py run       # dry-run by default
```

Standard library only. All deployment differences live in `config.json`; no code changes are needed for a new user or project. `profile.json` declares this package's defaults and which wizard steps apply.

## Onboarding wizard

Before any read, write, send or scheduled run, walk the user through the shared wizard described in `docs/onboarding-contract.md` at the repository root, and record every choice in the `wizard` section of the config. Never infer a platform, group identifier, message source, output target, notification template or run time, and never reuse a choice from an earlier session.

If the user is unsure, offer the quick-start preset. Creating a new report requires explicit authorization, all choices must be echoed for review, dry-run stays on, and the first run produces a change log only. Steps that do not apply to this package are skipped with a brief explanation, never silently.

## Required configuration

Read the local config before every run. Never infer a channel identifier, workbook path, entity mapping, document class or threshold from memory. See `config.example.json` and `config.schema.md`.

## Input and output are configurable

The mechanism used to obtain records and to deliver results is declared in `adapters.input` and `adapters.output`, not fixed in this document. Top-level config groups remain the single source of truth for parameters; every `*_ref` field points at one of them instead of duplicating its value.

`adapters.input` covers the message source family, the read client and identity, accepted document shapes, and the pull window. `adapters.output` covers the write target, notification channels, the task backend, and per-tier renderers with field visibility. See `DESIGN.md` and `config.schema.md`.

`adapters.resolution` is `declarative` until a dispatcher is implemented: the built-in default adapters keep running, and changing a `type` to an unimplemented alternative is a startup error. Switching an adapter must never weaken the invariants in this document.

## Accepted document classes

Document classes and their extraction requirements are config-driven. A typical split:

| Class | Treatment |
| --- | --- |
| Machine-readable evidence with amount-equivalent fields, a timestamp and a business key | Extract, attribute, deduplicate, register |
| Handwritten or unstructured material | Do not extract values; record a resubmission request with only a file reference and timestamp |
| Text-only messages claiming a value | Ignore entirely; record as a skipped item |
| Non-document images | Ignore; not an anomaly |
| Low-confidence, undated or altered documents | Route to manual review; do not register |

A one-off exception granted by an operator for a specific document is recorded as a run-level note. It never changes the class rules themselves.

## Attribution

Each record's entity is resolved from the message sender, not from the channel name.

1. Resolve the sender identifier against the configured entity mapping.
2. If the sender is not mapped but has a valid identity from the channel, create an entity from that objective identity. A newly seen entity without a workbook is handled as `record_without_write`.
3. Cross-check names appearing in the document or message text. A conflict with the sender identity is not resolved in favor of either side; it goes to manual review.
4. A sender that cannot be resolved to an entity, an automated identity, or an ambiguous name form goes to manual review. Never guess an owner and never assign a default.
5. The registry is elastic: only entities that actually submitted documents in the period appear in reports. Do not pad with zero-value entities and do not treat missing participants as an anomaly or a follow-up task.

## Deduplication

Four independent layers, checked in order:

| Layer | Key | Notes |
| --- | --- | --- |
| L1 | Source message identifier | Exact replay of the same message |
| L2 | Content hash of the document | Exact same bytes |
| L3 | Perceptual hash | Near-identical rendering of the same document |
| L4 | Business key | Business identifier plus timestamp; when no business identifier exists, a composite of entity, period, value, class and content hash |

Rules:

- A duplicate is defined by the business key, **not by an equal value**. Two distinct items with the same value are not duplicates.
- A perceptual-hash hit with a different business key is a false positive, not a duplicate.
- Two different entities with otherwise identical fields are never duplicates; the composite key includes the entity.
- A duplicate hit must be transparent: report the original registration time, the current status of the original record and the associated task link. Silent skipping is forbidden.
- The original message identifier is retained in the ledger. Entries are marked, never physically deleted.

## Write model

- One canonical detail sheet per target workbook, created only inside an **existing** workbook when the config explicitly authorizes it.
- Append-only: new rows only. Never modify existing cells, never insert rows into other sheets, never delete rows, never overwrite formulas.
- Use a package-part-level insertion: add the sheet part and update only the minimum required package parts; write every other part byte-identically.
- Back up before writing, verify after writing (untouched parts byte-identical, workbook opens, row count and values match), and roll back on failure.
- Idempotency key is the source message identifier; a rerun never appends the row twice.
- If the target workbook does not exist, register the record in the ledger with `record_without_write=true`, create the confirmation task, and report that a target must be assigned. **Never create a new workbook file.**
- Register the ledger entry only after the write verification succeeds.

## Status state machine

| State | Ledger condition | Counts as outstanding | Meaning |
| --- | --- | --- | --- |
| `confirmed` | Completion flag set by the editor | No | Downstream action is finished |
| `registered` | Registered, not completed, not voided | **Yes, the only one** | Awaiting downstream action |
| `needs_material` | Low confidence, undated, unresolved entity, unsupported class | No | Requires manual review |
| `duplicate` | Any dedup layer hit | No | Already accounted for; adds nothing |
| `voided` | Explicitly voided | No | Excluded from all totals |

Only `registered` contributes to outstanding totals. This single rule prevents both duplicate double-counting and unsupported material leaking into totals. Historical entries from retired channels remain in the ledger and remain in period statistics, because statistics are grouped by entity, not by channel.

## Confirmation tasks

- One task per entity per run, grouping that entity's newly registered records.
- Editor role: may edit and mark the task complete. Viewer role: may view and comment only, never change a value or complete the task.
- If a viewer identifier is missing, skip the viewer assignment silently and record it in the run log; it is not an anomaly or a follow-up task.
- Completion is polled. When a task becomes complete, mark the corresponding ledger entries `confirmed` and emit a short acknowledgement to the submitter, idempotent per task identifier.
- Task content carries a time boundary: the statistic window and the downstream action deadline. It contains no local machine paths.

## Notifications

Two tiers, both sent every run regardless of whether anything changed:

| Tier | Audience | Content |
| --- | --- | --- |
| Channel overview | The configured channel | One line per entity that submitted a document in this run, plus a total; a viewer mention and the task link; no ledger states, no outstanding balances, no period comparisons, no order identifiers, no file names, no local paths |
| Operator detail | A configured private channel | Per-entity values and destinations, duplicate hits with original registration time and current status, anomalies, task links and deadlines, ledger state counts, change log and backup paths |

A completely unchanged run still sends a compact no-change line. Silence is not acceptable because transparency is what prevents double action downstream.

Tone, greeting text and domain-specific wording are **policy hooks** disabled by default. They never carry operational fields.

## Period aggregation

A separate periodic run groups by entity using the ledger's entity field, not the channel allowlist.

- Only entities that submitted documents in the period appear; no zero-value padding.
- Period membership is derived from the document timestamp, falling back to the registration timestamp; never from the run date.
- Split totals into `confirmed` and `registered`; only `registered` is outstanding.
- A comparison with the previous period appears only in the operator tier.
- Include the list of document dates per entity for the channel overview.
- Produce no per-entity private reports unless explicitly configured.

## Invariants

1. One real-world item is accounted for exactly once, keyed by business key, never by equal value.
2. Every duplicate hit is transparent, with original registration time and current status.
3. A record is registered only after a verified write, or explicitly as `record_without_write`.
4. No new workbook file is ever created.
5. Writes are append-only to one detail sheet; every other part is byte-identical.
6. Every write has a backup checkpoint, verification and rollback.
7. Attribution is never guessed; conflicts go to manual review.
8. Only `registered` counts as outstanding.
9. Registry size is elastic; missing participants are never anomalies.
10. Both notification tiers are sent every run.
11. Change logs are append-only and never overwrite previous runs.

## Boundaries

- Only allowlisted channels are read; only exactly matched allowlisted channel identifiers receive messages.
- Retired channels are neither read nor notified; their historical ledger entries remain.
- No viewer private messages unless explicitly enabled; the send layer must hard-block an accidental per-entity private delivery flag.
- No changes to channel membership, settings or permissions.
- No value extraction from unsupported document classes.
- No operator exception becomes a permanent rule change.

## Extension points

- `ChannelReader.read(channel_id, window) -> messages` with document attachments.
- `DocumentClassifier.classify(document) -> class, confidence`.
- `Extractor.extract(document) -> structured fields`.
- `AttributionResolver.resolve(sender, text, document) -> entity or conflict`.
- `Deduper.check(record) -> verdict, original_entry`.
- `Ledger.add / check / mark / balance(...) -> state`.
- `DetailSheetWriter.append(target, rows, backup_checkpoint) -> verification`.
- `TaskAdapter.create / check(...) -> task, completion`.
- `NotificationAdapter.send(channel_id, message, idempotency_key) -> receipt`.
- `PolicyHook.render_tone(...) -> optional text`.

## Resource index

| File | Purpose |
| --- | --- |
| `README.md` | Use cases, quick start and adaptation guide |
| `DESIGN.md` | Dedup layers, ledger schema, state machine, write strategy, failure matrix |
| `config.example.json` | Placeholder-only example configuration |
| `config.schema.md` | Field-by-field configuration contract and environment overrides |
