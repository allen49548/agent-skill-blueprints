# Document Intake Ledger

Extract structured records from documents posted in channels, attribute them to the sender, and guarantee through a layered ledger that each real-world item is counted exactly once.

Onboarding is guided by `docs/onboarding-contract.md` at the repository root; use its quick-start preset if you are unsure.

## Use when

- Documents or screenshots arrive from multiple senders and duplicate submission is common.
- A duplicate must be explained with its original registration time and current status, never skipped silently.
- A record must still exist when its target workbook is missing.
- Downstream confirmation is a task with an editor and a viewer who cannot change values.
- Every run must report what happened, including runs with no changes.

## Do not use when

Fixed-layout cell updates (`message-to-workbook-sync`), results needing an approval gate (`verified-batch-calculation`), a trusted exactly-once API, or any workflow that modifies a document in place.

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

`DESIGN.md` defines the four dedup layers, the ledger schema, the state machine, the append-only write and the failure matrix. Read the dedup section first: a perceptual hash hit with a different business key is a false positive, or legitimate distinct items will be dropped. Field-by-field configuration is in `config.schema.md`.

## Files

`SKILL.md` (contract), `README.md`, `DESIGN.md`, `config.example.json`, `config.schema.md`.
