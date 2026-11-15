---
name: message-to-workbook-sync
description: Specification for parsing semi-structured channel messages in multiple formats, normalizing fields by meaning, resolving entity-to-group ownership, and writing normalized values idempotently into existing workbooks at cell level without changing their structure. Use when records arrive as free-form or card-style messages and a fixed-layout workbook must be updated across several scheduled rounds with corrections, backups, absence marking, anomaly escalation and tiered summaries. Defines ownership precedence, semantic normalization, deduplication keys, surgical write rules, cross-period corrections, business-period rules, idempotent cell comparison and notification tiers. Do not use for append-only record collection, for creating new workbooks, or when a structured form can replace message parsing.
agent_created: true
---

# Message to Workbook Sync

## Purpose

Turn semi-structured messages published in allowlisted channels into precise cell-level updates in existing workbooks, without ever changing the workbook's structure, formulas or other content.

The pipeline handles multiple message formats, field-name variation, corrections that arrive later or belong to an earlier business period, and several scheduled rounds that culminate in a final aggregation. This is a specification, not an implementation.

## When to use

- Records arrive as human-written messages or rendered card-style messages, not as structured API payloads.
- The target workbook has a fixed layout with pre-existing period rows and formulas that must be preserved byte-for-byte outside the written cells.
- Corrections must overwrite earlier values, including corrections to a previous business period.
- The same run may execute several times a day and must be safe to repeat.
- Per-entity ownership of a group must be resolved from an explicit mapping rather than inferred from the channel the message appeared in.

## When not to use

- A structured form or API can provide the records directly.
- Records must be appended as new rows behind a deduplication ledger; use the `document-intake-ledger` blueprint.
- New workbooks need to be created. This blueprint never creates a target file.
- High-stakes computed results need an approval gate before delivery; use the `verified-batch-calculation` blueprint.

## Core concepts

`entity`, `channel`, `workbook`, `run`, `business period`, `ownership precedence`, `surgical write`, `backup checkpoint`, `idempotency key`, `policy hook`. Definitions are in `docs/vocabulary.md`.

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

Read the local config before every run. Never infer a channel identifier, workbook path, entity mapping, column mapping or business-period rule from memory. See `config.example.json` and `config.schema.md`.

## Source formats

The parser must support at least two message shapes and normalize them into one field set.

| Shape | Detection | Notes |
| --- | --- | --- |
| Labeled text | Lines of `field: value`, possibly with full-width punctuation, extra whitespace or several records in one message | Split multi-record messages on a configured boundary field |
| Rendered card | Structured message whose content contains bolded or labeled fields | Decorative lines, links and image markers are ignored; missing fields are handled by policy |

Both shapes flow into the same normalization, deduplication, ownership resolution and write path. Ignoring one shape causes entities to be falsely classified as absent.

## Semantic normalization

Field names vary. Normalize by meaning, not by exact string equality.

1. Strip leading and trailing whitespace, remove whitespace inside field names, and unify full-width and half-width separators.
2. Apply the configured alias map so synonyms resolve to one canonical field.
3. Handle a value glued to the field name by longest-prefix matching against the canonical field-name set. Digits that are part of a field name must not be consumed as the value. Only write when the remainder parses uniquely as one numeric value.
4. Strip units and thousands separators before numeric conversion.
5. A present field with an empty value is handled by `normalization.empty_value_policy`. The original implementation used zero; a different project may prefer "leave unchanged". The policy is config, not a hardcoded rule.
6. Fields with no target column are recorded as ignored fields, not failures.

Only genuinely ambiguous or unreadable content is skipped. That includes two numbers that cannot be separated, a message with no readable fields, a non-numeric dirty string and a withdrawn message. A skipped item keeps the existing cell value, is recorded in the change log, and may trigger anomaly escalation depending on configuration.

## Ownership precedence

Resolve the group an entity belongs to in this fixed order:

1. Configured entity-to-group mapping (highest priority).
2. An explicit group field in the record.
3. Inference from the source channel (lowest priority, used only for card-shaped messages that omit the field).

A conflict is resolved by the higher-priority source, recorded as an ownership correction, and is not treated as a field anomaly. An entity absent from the mapping is not defaulted to a majority group; it is marked as unresolved and routed to manual review. All statistics, rankings, summaries and notifications are computed per group after normalization. Groups are never merged in any outbound message.

## Deduplication and corrections

- Deduplication key: `(business_period, entity, normalized_group)`.
- Multiple records with the same key in one run: take the most recent by source timestamp and record that it was a correction.
- **The decision to write is based on the current cell value, not on a processed-state flag.** A previously processed key is not a reason to skip.
- If the new value differs from the current cell value, overwrite it and record `old -> new`. If equal, record "no change" without writing or making a redundant backup.
- Corrections may arrive across runs, across days, or after a period has been closed. Each correction is attributed to the business period stated in the record, never to the wall-clock date of the run.
- A correction to an earlier period updates that period's row and that period's log and backup directory. It never writes into the current period's row or log.
- A record with a missing or ambiguous period is not guessed; it is skipped and routed to manual review.

## Surgical write rules

1. Never append rows, insert columns, delete rows or change the period grid. Locate the row by the configured period key.
2. Modify only the configured target cells on that row. Absence-marker styling is a separate, explicitly enabled operation.
3. Never modify formulas, subtotal rows, summary regions, notes columns or any cell containing a formula.
4. Prefer a part-level replacement of the workbook package: modify only the relevant sheet part, keep every other part byte-identical, and set a recalculation flag on load instead of rewriting formula cells.
5. Write through a temporary file and an atomic replace at the same path, preserving permissions.
6. Verify after writing by comparing every untouched part against the backup byte-for-byte, reopening the workbook, and confirming the target values. Roll back on verification failure.
7. Styling changes that cannot be done at part level require a full-document library loaded with formulas preserved; never load a formula-stripping mode.

## Backup rule

Every write, including corrections and absence-marker changes, is preceded by a backup checkpoint. A correction creates an additional pre-correction copy rather than overwriting an existing backup, so any historical version can be restored. A backup failure aborts the write for that workbook.

## Scheduled rounds and business period

Rounds, their clock times and their business-period mapping are entirely config-driven. The general rules are:

- Derive the current time from the system clock, then map it to a round and a business period using the configured table. An unexpected hour is a fallback case, never a guessed round.
- All logs, backups, state and notifications are attributed to the business period, which may be the preceding calendar day for a run just after midnight.
- Each round re-reads the full period window. Never reuse a previous round's cached values for the final aggregation.
- The final round performs a full re-read, applies absence markers, computes per-group aggregates, and records the period as closed. Earlier rounds only backfill and correct.
- If a previous period is found unclosed at the start of a run, complete its finalization before processing the current round.
- Absence markers are a policy hook: a configurable visual marker applied to entities with no successfully written record in the period. No numeric value is written for an absent entity. A later successful write clears the marker first.

## Notifications and summaries

Notification tiers are config-driven. The general contract:

| Tier | Audience | Content rule |
| --- | --- | --- |
| Run summary | A configured channel | Only when the run made changes; no sensitive per-entity values |
| Anomaly escalation | The source channel | Show the original field text of an unreadable record and mention the sender; never include other entities' data or local paths |
| Final aggregation | Each group's own channel | Per-group aggregates only, never merged across groups, never with per-entity values unless explicitly configured |
| Operational detail | A configured private channel | Full detail, backup paths, change log paths and skipped items |

Domain-specific reward, penalty, ranking and commentary rules are **policy hooks**, not part of this blueprint. If enabled, they receive the final normalized per-group data and must never add cross-group or per-entity values that the config forbids.

## Invariants

1. Inputs are read-only; only configured target cells in existing workbooks are modified.
2. No workbook is created, deleted, moved or renamed.
3. Every write has a verified backup checkpoint.
4. Cell-value comparison, not a processed flag, decides whether a write occurs.
5. A correction belongs to the business period stated in the record.
6. Ownership is resolved by precedence; unresolved entities are never defaulted.
7. Groups are never merged in statistics or outbound messages.
8. Change logs are append-only across rounds.
9. Ambiguous data is skipped, never guessed.
10. Every failure and every skip is recorded; silent failure is a defect.

## Boundaries

- Only allowlisted channels are read; only configured channels receive notifications.
- No changes to channel membership, settings or permissions.
- No automatic addition of service identities to channels.
- No mention of all participants unless explicitly configured.
- A request to produce a change log without writing must be honored by skipping the write stage entirely.

## Extension points

- `ChannelReader.read(channel_id, window) -> messages` preserving sender identity and timestamps.
- `MessageParser.parse(message) -> records`, one parser per configured shape.
- `Normalizer.normalize(record) -> canonical fields` using the alias map and empty-value policy.
- `OwnershipResolver.resolve(entity, record, channel_id) -> group`.
- `WorkbookLocator.locate(entity, business_period) -> file, sheet, row`.
- `CellWriter.write(targets, backup_checkpoint) -> verification`.
- `Aggregator.summarize(final_records) -> per_group_summaries`.
- `NotificationAdapter.send(channel_id, message, idempotency_key) -> receipt`.
- `PolicyHook.evaluate(final_records) -> optional messages`.

## Resource index

| File | Purpose |
| --- | --- |
| `README.md` | Use cases, quick start and adaptation guide |
| `DESIGN.md` | Parsing, ownership, surgical writes, state machine, failure matrix |
| `config.example.json` | Placeholder-only example configuration |
| `config.schema.md` | Field-by-field configuration contract and environment overrides |
