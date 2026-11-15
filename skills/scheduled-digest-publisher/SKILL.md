---
name: scheduled-digest-publisher
description: Specification for a periodic digest pipeline that aggregates items from multiple configured sources, filters and ranks them, spotlights one configured focus entity, normalizes timestamps into a single display timezone, renders a template, and delivers exactly one message per business period to an allowlisted channel with idempotency and graceful degradation. Use when a project needs a scheduled briefing, recurring status digest, release-notes roundup, monitoring summary or event schedule sent to a channel. Defines the source window, selection and verification policy, focus-entity section, timezone conversion, message template, delivery allowlist, idempotency key and failure chain. Do not use for real-time event push, interactive querying, or one-off reports with no delivery step.
agent_created: true
---


> **Implementation status: mixed.** The generic runtime (ingest, dedupe, write, notify) is implemented; most capability-specific mechanisms below are target design. See [docs/capability-matrix.md](../../docs/capability-matrix.md) before relying on any invariant here.
# Scheduled Digest Publisher

## Purpose

Produce exactly one digest message per business period. The digest combines a curated set of items from configured sources with a dedicated section for one configured focus entity, converts every timestamp into a single display timezone, and delivers the rendered message to an allowlisted channel.

This is a specification, not an implementation. All sources, channels, schedule and thresholds come from configuration. No source name, product name, organization name or real identifier belongs in this document.

## When to use

- A recurring briefing must be produced on a schedule and delivered to a channel.
- Items from several heterogeneous sources must be filtered, deduplicated and ranked into a fixed-size set.
- One entity must always be highlighted, whether or not it has an item in the current period.
- All times must be shown in one timezone regardless of the source timezone.
- A repeated run for the same period must not produce a duplicate message.

## When not to use

- Real-time push on every incoming event. This pipeline is period-based.
- An interactive assistant that answers arbitrary follow-up questions.
- A one-off export with no delivery step and no idempotency requirement.
- A workflow that requires the recipient to approve content before delivery. Use an approval gate from the verified calculation blueprint instead.

## Core concepts

`source`, `channel`, `entity`, `run`, `business period`, `idempotency key`, `degradation`. Definitions are in `docs/vocabulary.md` at the repository root. Keep the vocabulary consistent when implementing adapters.

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

Read the local config before every run. Never infer a source endpoint, channel identifier, timezone or threshold from memory. See `config.example.json` and `config.schema.md`.

Minimum required fields: `schedule`, `display_timezone`, `sources`, `selection`, `focus.entity_id`, `delivery.allowlist`, `output.root`.

## Fixed pipeline

The order is mandatory. No stage may be skipped.

1. **Resolve the period.** Obtain the current time from the system clock, convert it into `display_timezone`, and derive the business period identifier. Never compute a date or weekday from memory.
2. **Collect.** For each enabled source, fetch items inside the configured lookback window. Write a structured `material` artifact and a human-readable `draft` artifact under `output.root/<period>/`. A single source failure is recorded in `material.errors` and does not abort the run.
3. **Read.** Load the draft. Consult the structured artifact only when an exact field such as a timestamp, link or numeric value is required.
4. **Verify.** Perform at least `verification.min_cross_checks` independent cross-checks for statements involving numbers, named parties, statuses or times. When a check conflicts with collected material, prefer the traceable authoritative source and record a one-line difference in the run log. If a fact cannot be confirmed, omit it. Never fill gaps with unverified content.
5. **Select.** Apply the selection policy: window filter, title and fact deduplication, category assignment, and a one-sentence justification per item. Produce between `selection.min_items` and `selection.max_items` items.
6. **Render.** Build the final message from the message template. The message must contain the focus-entity section first, followed by selected items grouped by category, followed by a source list. It must not contain local machine paths, script paths, debug output or internal identifiers.
7. **Deliver.** Send to every allowlisted channel with `enabled=true`, using the configured idempotency key. Rich rendering falls back to plain text automatically. Append the outcome to the send log.
8. **Record and report.** Append a run log entry containing item count, source distribution, focus-entity status, delivery outcome and every degradation. Report the same summary back to the caller in a short structured form.

## Focus-entity section

The focus entity is a config value, not a hardcoded constant.

- The section is always present and always first, with a stable marker in its heading.
- If the entity has an occurrence in the period: show the normalized local start time, the counterpart, the location or venue if available, the current status, and any verified context. Numeric values must come from the structured artifact.
- If it has no occurrence: state that explicitly and give the next occurrence with its normalized time and counterpart.
- Fields the configured sources do not provide must be omitted, not invented. Absence of data is not a zero score or a default status.

## Source and selection policy

- Only items inside the lookback window are eligible.
- Deduplicate by a normalized title plus the underlying fact, not by exact string equality.
- Assign each item to one configured category.
- Every item carries a clickable source link.
- Exclude promotional text, sensational headlines, stale items and sources that have failed a freshness check.
- Do not reproduce large excerpts of source content; summarize with a link.
- Adding a source requires a live validation that it returns current-period items. A blocked or stale source stays in the denylist until revalidated.

## Timezone handling

- Source timestamps may be expressed in a different timezone than `display_timezone`. A single source day is not equivalent to a display day.
- Collect across a window that spans at least the preceding and following source day relative to the display period, then filter by the converted timestamp. Querying a single day is incorrect.
- All displayed times carry an explicit timezone label. Do not assume daylight saving rules; use the configured timezone database.

## Invariants

1. One message per business period per channel. The idempotency key includes the period and the channel identifier.
2. The focus-entity section is never omitted, including periods with no occurrence.
3. No unverified number, name, status or time appears in the final message.
4. Delivery is restricted to the allowlist. Changing the target set requires an explicit config change.
5. A manual test run uses a distinct idempotency key suffix so it cannot suppress the scheduled run.
6. All artifacts are written only under `output.root/<period>/`.
7. A failure is always recorded. A silent failure is a defect.

## Failure and degradation

| Failure | Behavior |
| --- | --- |
| One source fails | Continue with remaining sources; record the failed source; omit it from the source list |
| All sources fail | Still deliver the structural sections with an explicit "sources unavailable" note; never backfill with stale or invented items |
| Schedule source fails | Deliver without the event section and state that it is unavailable |
| Rich rendering fails | Fall back to plain text automatically |
| Delivery fails after fallback | Record the reason in the send log and report "not delivered" explicitly; do not retry in a loop |
| Focus data missing | Keep the section, state that data is unavailable, omit unverifiable fields |

## Boundaries

- No writes outside `output.root/<period>/`.
- No changes to channel membership, channel settings or permissions.
- No mentions of arbitrary participants and no unsolicited messages to channels outside the allowlist.
- No modification of the verified source denylist without a live revalidation.
- No bulk reproduction of source content.

## Extension points

Implement these against your own services; they are intentionally absent from this specification.

- `SourceAdapter.fetch(period, window) -> items` with a freshness declaration.
- `ScheduleAdapter.fetch(period_range) -> occurrences` with timezone-aware timestamps.
- `Verifier.cross_check(claim) -> verdict` backed by a traceable authority.
- `ChannelAdapter.send(channel_id, message, idempotency_key) -> receipt` with rich/plain fallback.
- `TemplateRenderer.render(model) -> string` with no machine-local values.
- `Clock.now() -> datetime` always backed by the system clock.

## Resource index

| File | Purpose |
| --- | --- |
| `README.md` | Use cases, quick start and adaptation guide |
| `DESIGN.md` | Architecture, data contracts, state machine, failure matrix |
| `config.example.json` | Placeholder-only example configuration |
| `config.schema.md` | Field-by-field configuration contract and environment overrides |
