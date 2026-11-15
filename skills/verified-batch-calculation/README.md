# Verified Batch Calculation

Compute per-entity results from human-confirmed rules, prove them through an independent recomputation, and deliver one private result per recipient only after a fingerprint-bound approval gate. Exactly two business capabilities: `compute` and `verify`.

Onboarding is guided by `docs/onboarding-contract.md` at the repository root; use its quick-start preset if you are unsure.

`build.py` at the repository root produces a standalone copy of this package into `dist/`. Read [docs/capability-matrix.md](../../docs/capability-matrix.md) to see which parts are implemented.

## Use when

- A periodic allocation, quota, score or entitlement is high-stakes and rules differ per entity.
- Rules are inferred from historical results and must be confirmed by a human before use.
- A wrong result must never be delivered, and a bug must not agree with its own check.
- A scheduled job must stop at a preview and wait for an approver.

## Do not use when

Low-stakes single-pass calculations, document collection and deduplication (`document-intake-ledger`), fixed-layout workbook updates (`message-to-workbook-sync`), or any pipeline needing a third business capability.

## Quick start

Self-contained. Python 3.9+ standard library only, no install and no credentials.

```bash
python3 run.py demo      # bundled sample data, full pipeline, artifacts in demo-out/
python3 run.py setup     # 9-step wizard -> config.json
python3 run.py doctor    # validate config and adapters
python3 run.py run       # dry-run by default; --no-dry-run for real writes
```

`setup --yes` accepts the recommended preset. `python3 run.py install --apply` installs this skill into the local skills directory. See `docs/onboarding-contract.md` at the repository root for the wizard contract and `config.schema.md` for every field.

## Read next

`DESIGN.md` defines the rule DSL safety constraints, the fingerprint, the state machine and the failure matrix. Read the fingerprint section first: a confirmation not bound to inputs, rules and results can be replayed against a changed result. Field-by-field configuration is in `config.schema.md`.

## Files

`SKILL.md` (contract), `README.md`, `DESIGN.md`, `config.example.json`, `config.schema.md`.
