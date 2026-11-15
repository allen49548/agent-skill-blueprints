# Design: Verified Batch Calculation

## Architecture

```
  [RegistryAdapter] ----> entity registry (cached, read-only)
  [RecordSource] -------> normalized records
  [Transcriber] --------> structured rows + confidence
            |
            v
     [RuleEngine] compute --------> per-row detail, per-entity summary, fingerprint
            |                                   |
            |                                   v
     [Verifier] recompute (independent path) ---> outcome BLOCK / REVIEW / PASS
            |
            v
     [ResultRenderer] preview (no delivery)
            |
     [ApprovalGate] <--- approver token
            |
     [DeliveryAdapter] dispatch (dry-run default) ---> [Ledger] receipts
```

The verify path must not call the compute path. If they share an evaluator, a bug in that evaluator produces agreement and the entire safety property disappears.

## Two-capability boundary

Business capabilities: `compute`, `verify`. Everything else is input preparation or delivery orchestration. A new capability is added only by creating a new blueprint, never by extending this one. This constraint keeps the verification surface finite and reviewable.

## Rule DSL

Rules are declarative data, never executable code.

| Property | Requirement |
| --- | --- |
| Format | Structured JSON: conditions, operands, operators, rounding, output field |
| Allowed operators | A closed allowlist of arithmetic and comparison operators |
| Prohibited | Arbitrary expression evaluation, dynamic imports, user-supplied code strings |
| Provenance | Each rule records its origin and `confirmed` status |
| Inference | Historical results may produce `candidates` only; `confirmed=false` until a human approves |
| Evaluation | Deterministic; same inputs and rules always produce the same fingerprint |

A rule whose `confirmed` flag is false is a blocking condition in class 3 of verification. Never infer an algorithm from numeric patterns without presenting it for confirmation.

## Fingerprint

```
fingerprint = hash(
    sorted(record_ids_and_content_hashes),
    canonical_rule_set_with_confirmation_flags,
    precision_settings,
    registry_version,
    period_id
)
```

Properties:

- Changing any input, rule, confirmation flag, precision setting or registry version changes the fingerprint.
- A confirmation stores the fingerprint it authorizes.
- Before dispatch, the current fingerprint is recomputed and compared; a mismatch invalidates the confirmation.
- Confirmations have a configured expiry, independent of the fingerprint.

## State machine

```
INIT -> PREPARED -> COMPUTED -> VERIFIED -> PREVIEWED -> CONFIRMED -> DISPATCHED
                        |            |           |            |
                        |            |           |            +--> EXPIRED
                        |            +-----------+--------------> BLOCKED
                        +----------------------------------------> FAILED
```

| Transition | Guard |
| --- | --- |
| `PREPARED -> COMPUTED` | All required inputs present and mapped |
| `COMPUTED -> VERIFIED` | Independent recomputation completed |
| `VERIFIED -> PREVIEWED` | Outcome is `PASS`, or `REVIEW` with explicit acceptance |
| `PREVIEWED -> CONFIRMED` | Approver-supplied token, matching fingerprint, not expired |
| `CONFIRMED -> DISPATCHED` | Dry-run explicitly disabled and all recipients eligible |
| any -> `BLOCKED` | Any blocking verification class failed |
| any -> `FAILED` | Unrecoverable stage error; stop and report |

A `BLOCKED` or `FAILED` state never reaches `DISPATCHED`. A delivery failure does not roll back earlier artifacts.

## Verification classes

| # | Class | Typical failure | Default severity |
| --- | --- | --- | --- |
| 1 | Input completeness and provenance | Missing or untraceable records | blocking |
| 2 | Reconciliation | Row detail does not sum to entity totals | blocking |
| 3 | Rule compliance | Unconfirmed or unsupported rule | blocking |
| 4 | Inclusion and exclusion | Records outside configured filters were used | blocking |
| 5 | Period-over-period anomaly | Unexplained large deviation | advisory (`REVIEW`) |
| 6 | External reference agreement | Reference set disagrees | configurable |
| 7 | Arithmetic precision | Rounding drift | blocking |
| 8 | Delivery eligibility | Recipient missing from allowlist or identifier invalid | blocking |

Severity is configuration, not code. `BLOCK` wins over `REVIEW` when both are present.

## Approval gate

- The token is supplied by the approver. An agent must not generate, guess or reuse one.
- The gate records: token reference (never the token value), approver identifier, fingerprint, timestamp, accepted `REVIEW` items and expiry.
- A scheduled run may create a preview and notify the approver, but must never cross the gate.
- `REVIEW` acceptance is a separate explicit field, not an implication of confirming.

## Dispatch contract

- Dry-run is the default and produces a receipt plan without sending.
- Eligibility: entity in the period's computed results, recipient in the allowlist, delivery identifier valid, notification enabled.
- One message per recipient, containing only that recipient's result.
- Idempotency key: `result:{period}:{entity_id}:{fingerprint}`. A successful receipt is recorded in the ledger; a repeat is skipped.
- No group fallback. An ineligible recipient is recorded as informational, never as an alert or a follow-up task.
- Delivery failures are reported; earlier artifacts are not rolled back.

## Elasticity principle

Compute only for entities with records in the period. Do not pad with zero-value rows to reach a roster size, do not require all entities to be present, and do not treat absence as an error. An entity that cannot be resolved to a registry entry is marked `unresolved` and becomes a blocking condition in class 1, because that is a real correctness risk.

## Failure matrix

| Stage | Failure | Behavior | Logged as |
| --- | --- | --- | --- |
| Preparation | Registry source unavailable | Use last valid cache; if empty, no delivery-eligible recipients | `registry_degraded` |
| Preparation | Ambiguous column mapping | Stop; do not guess | `column_ambiguous` |
| Preparation | Low-confidence transcription | Route to manual review; exclude from computation | `transcription_low_confidence` |
| Compute | Missing or unconfirmed rule | Stop at `BLOCKED` | `rule_not_confirmed` |
| Compute | Evaluation error | Stop; record the row | `evaluation_failed` |
| Verify | Independent path disagrees | `BLOCK` | `recompute_mismatch` |
| Verify | Anomaly beyond threshold | `REVIEW` | `period_anomaly` |
| Preview | Render failure | Stop before gate | `render_failed` |
| Confirmation | Fingerprint changed or expired | Invalidate confirmation | `confirmation_invalid` |
| Dispatch | Recipient ineligible | Skip, record informationally | `recipient_ineligible` |
| Dispatch | Send failure | Record receipt failure; no rollback, no loop retry | `delivery_failed` |

## Extension points

| Interface | Must not do |
| --- | --- |
| `RegistryAdapter` | Send messages or modify the source registry |
| `RecordSource` | Modify input files |
| `Transcriber` | Guess unreadable values |
| `RuleEngine` | Evaluate arbitrary expressions |
| `Verifier` | Reuse the compute evaluator |
| `ResultRenderer` | Deliver anything |
| `ApprovalGate` | Accept an agent-generated token |
| `DeliveryAdapter` | Send a group message or another entity's data |
| `Ledger` | Delete historical entries |

## Testing checklist

- [ ] An unconfirmed rule always produces `BLOCK`.
- [ ] A deliberate bug in the compute path is caught by the independent verify path.
- [ ] Changing one input record invalidates an existing confirmation.
- [ ] `REVIEW` cannot be confirmed without explicit acceptance.
- [ ] `preview` produces zero external messages.
- [ ] A scheduled run stops at `preview`.
- [ ] Dry-run dispatch produces a plan and zero messages.
- [ ] Each message contains only its own recipient's result.
- [ ] Repeating dispatch does not resend a successful delivery.
- [ ] An elastic roster with fewer entities than nominal produces no zero-value padding and no alerts.
- [ ] No input file is modified by any stage.
- [ ] Committed artifacts contain no real names, identifiers or amounts.
