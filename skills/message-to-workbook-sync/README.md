# Message to Workbook Sync

Parse semi-structured channel messages in multiple formats and write normalized values into existing fixed-layout workbooks at cell level, idempotently and without changing their structure.

Onboarding is guided by `docs/onboarding-contract.md` at the repository root; use its quick-start preset if you are unsure.

## Use when

- Records arrive as text templates or rendered cards and must land in an existing workbook.
- The workbook layout is owned by someone else and formulas, cached values and other sheets must survive byte-identically.
- Corrections must overwrite earlier values, including corrections to a closed earlier period.
- Several scheduled rounds per period end in per-group aggregates.
- Entity-to-group ownership must be authoritative and must never leak across groups.

## Do not use when

Append-only record collection (`document-intake-ledger`), workflows that can use a structured form instead of parsing, cases requiring new workbooks, or results needing an approval gate (`verified-batch-calculation`).

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

`DESIGN.md` covers ownership precedence, glued field/value splitting, the part-level surgical write, cross-period corrections and the failure matrix. Read the write strategy before choosing a spreadsheet library: a full save in the wrong mode can drop formulas and custom parts. Field-by-field configuration is in `config.schema.md`.

## Files

`SKILL.md` (contract), `README.md`, `DESIGN.md`, `config.example.json`, `config.schema.md`.
