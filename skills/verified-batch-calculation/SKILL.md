---
name: verified-batch-calculation
description: Specification for a two-capability pipeline that computes per-entity results from independently confirmed declarative rules, then recomputes them through a separate path and verifies them before an approver can authorize one-to-one private delivery to recipients. Use when results are high-stakes, calculation rules differ per entity, and a wrong result must never be delivered. Defines the compute/verify boundary, rule confirmation requirement, verification outcomes BLOCK / REVIEW / PASS, a fingerprint-bound approval gate, dry-run default, per-recipient delivery with idempotency, and the rule that inputs are never modified. Do not use for low-stakes single-pass calculations, for aggregation of documents, or for any pipeline that needs a third business capability.
agent_created: true
---


> **Implementation status: target design, not implemented.** This package currently runs the generic shared pipeline only. Independent recomputation, the eight verification classes, the approval gate and fingerprint binding described below do not exist in the runtime. See [docs/capability-matrix.md](../../docs/capability-matrix.md) before relying on any invariant here.
# Verified Batch Calculation

## Purpose

Produce trustworthy per-entity results and deliver them safely. The mechanism has exactly two business capabilities: **compute** and **verify**. Everything else is either input preparation or delivery orchestration, and must never grow into a third capability.

This is a specification, not an implementation. All rules, sources, recipients, channels and output locations come from configuration.

## When to use

- A periodic calculation determines amounts, allocations, scores or entitlements for multiple entities.
- Rules differ per entity and are derived from historical results, so they must be confirmed by a human before use.
- A mistake is expensive or irreversible, so an independent recomputation must agree before anything is sent.
- Each recipient must receive only their own result, never a group message.

## When not to use

- Reversible, low-stakes single-pass calculations with no external delivery.
- Document collection, deduplication or aggregation. Use the `document-intake-ledger` blueprint.
- Writing results into an existing structured document as the primary goal. Use the `message-to-workbook-sync` blueprint.
- Any scenario where the delivery step can be skipped safely; the approval gate is the point of this blueprint.

## Two-capability boundary

The following are **not** new capabilities; they are input preparation or delivery orchestration and are allowed but must not expand scope:

- Input preparation: entity registry synchronization, record filtering, field mapping, document transcription, rule inference, style extraction.
- Delivery orchestration: unified result rendering, preview generation, approval gate, one-to-one delivery, scheduling.

Explicitly out of scope: aggregation of unrelated documents, settlement of third-party charges, attendance, tax handling, performance analysis, entity management, and any write into an input file.

## Core concepts

`entity`, `recipient`, `approver`, `run`, `fingerprint`, `approval gate`, `ledger`, `BLOCK` / `REVIEW` / `PASS`. Definitions are in `docs/vocabulary.md`.

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

Read the local config before every run. Never infer a path, column name, entity ownership or calculation rule from memory. See `config.example.json` and `config.schema.md`.

## Fixed pipeline

The order is mandatory. No stage may be skipped or reordered.

```
input preparation -> compute -> verify -> preview -> approver confirmation -> dispatch
                                  |                        |
                              BLOCK stops            hard gate, never automated
```

1. **Read config.** Prefer the local config directory over bundled examples. If a registry source is configured, synchronize the registry read-only into a local cache; no messages are sent during this step.
2. **Prepare inputs.** Filter and map records. Documents requiring visual transcription are transcribed with row and column positions preserved; low-confidence values go to a manual review list and are never guessed.
3. **compute.** Evaluate confirmed rules row by row with fixed-precision arithmetic. Emit per-row detail, per-entity summary and an input fingerprint. Inputs are read-only.
4. **verify.** Recompute through an independent path and run every configured verification class. Emit a machine-readable verification result and a human-readable report with one of `BLOCK`, `REVIEW` or `PASS`.
5. **preview.** Produce the unified result table, one result document per entity, and a preview for the approver. **This stage never delivers anything to any recipient.**
6. **approver confirmation.** Only the approver may confirm, using a token they supply. If the outcome is `REVIEW`, the approver must explicitly accept the flagged items. An agent must never confirm on the approver's behalf or invent a token.
7. **dispatch.** Default to dry-run. When explicitly disabled, send one private message per eligible recipient, containing only that recipient's result. Record receipts in the ledger for idempotency.

A failure at any stage stops the pipeline at that stage and is reported. Never skip verification to deliver, and never roll back written artifacts because delivery failed.

## Iron rules

1. **Rules must be human-confirmed.** Rules inferred from historical results are `confirmed=false` until a human confirms them; unconfirmed rules cause `BLOCK`. Never infer an algorithm from numeric patterns, and never evaluate arbitrary expressions from data.
2. **An unverified result is never delivered.** `BLOCK` forbids confirmation and delivery. `REVIEW` requires explicit acceptance. Only `PASS` opens the approval gate.
3. **Confirmation is bound to a fingerprint.** Any change to inputs, rules or results invalidates the confirmation and requires recomputation, reverification and reconfirmation. Confirmations expire.
4. **Registry size is elastic.** Compute only for entities that actually have records in the period. Never pad the result set with zero-value rows to match a nominal roster, and never treat a missing entity as an error or a follow-up task.
5. **One recipient, one message.** Deliver only to eligible recipients with a valid delivery identifier. Never fall back to a group message and never include another entity's data.
6. **Idempotency.** A successful delivery for a given period, entity and result fingerprint is never repeated.
7. **Fixed-precision arithmetic.** Round per row at the configured precision, then accumulate. Floating-point drift must not create false verification failures.
8. **No silent anomalies.** Missing rules, evaluation errors, ambiguous columns, unparseable dates, name collisions, write failures and delivery failures all appear in the verification report and the run log.
9. **Dry-run default.** Every external action is disabled by default. Real delivery requires verified results, a valid confirmation and an explicit opt-out from dry-run.
10. **Inputs are read-only.** All artifacts are written only to the configured output root. Historical files are never modified.

## Verification classes

Implement each class as an independent check; a class failure contributes to the outcome as configured.

1. Input completeness and provenance.
2. Reconciliation between per-row detail and per-entity totals.
3. Rule compliance and confirmation status.
4. Inclusion and exclusion of configured record categories.
5. Period-over-period anomaly detection.
6. Agreement with an external reference set, when configured.
7. Arithmetic precision and rounding consistency.
8. Delivery eligibility and recipient allowlist integrity.

## Verification outcomes

| Outcome | Meaning | Allowed next step |
| --- | --- | --- |
| `BLOCK` | A hard invariant failed or a rule is unconfirmed | Fix inputs or rules, then recompute |
| `REVIEW` | Soft anomalies require human judgement | Approver explicitly accepts the flagged items, then confirms |
| `PASS` | All classes agree | Approval gate may open |

## Boundaries

- No writes to any input file, historical result file or registry source.
- No third business capability, however convenient.
- No group delivery of individual results.
- No agent-generated confirmation tokens and no automatic confirmation by a scheduled run.
- No real identifiers, names or amounts in any committed artifact; those live only in a gitignored local config and runtime state.

## Extension points

- `RegistryAdapter.sync() -> entities`, read-only.
- `RecordSource.read(period) -> records` with field mapping.
- `Transcriber.transcribe(document) -> structured rows` with confidence scores.
- `RuleEngine.evaluate(confirmed_rules, records) -> per_row_results`.
- `Verifier.recompute_and_check(...) -> outcome`, independent of the compute path.
- `ResultRenderer.render(results, style) -> artifacts`.
- `ApprovalGate.confirm(token, approver, fingerprint) -> confirmation`.
- `DeliveryAdapter.send(recipient_id, artifact, idempotency_key) -> receipt`.
- `Ledger.check_and_record(key) -> state`.

## Resource index

| File | Purpose |
| --- | --- |
| `README.md` | Use cases, quick start and adaptation guide |
| `DESIGN.md` | State machine, rule DSL, verification design, failure matrix |
| `config.example.json` | Placeholder-only example configuration |
| `config.schema.md` | Field-by-field configuration contract and environment overrides |
