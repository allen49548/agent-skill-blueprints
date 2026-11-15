# Scheduled Digest Publisher

Aggregate multiple sources into one period-keyed digest, always highlight one configured entity, normalize every time into a single timezone, and deliver exactly once to an allowlisted channel.

Onboarding is guided by `docs/onboarding-contract.md` at the repository root; use its quick-start preset if you are unsure.

`build.py` at the repository root produces a standalone copy of this package into `dist/`. Read [docs/capability-matrix.md](../../docs/capability-matrix.md) to see which parts are implemented.

## Use when

- A recurring briefing, release-notes roundup, incident summary or event schedule must be sent on a schedule.
- Items from heterogeneous sources need window filtering, deduplication and a fixed-size ranked set.
- One configured entity must be highlighted even in periods with no occurrence for it.
- Runs must be safe to repeat and safe to send unattended.

## Do not use when

Real-time event push, conversational follow-up, one-off exports, or content that requires human approval before delivery (see `verified-batch-calculation`).

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

`DESIGN.md` covers the collection window across timezone boundaries, the idempotency key, the state machine and the failure matrix. Read it before choosing a scheduler: a key without the channel identifier silently suppresses valid sends. Field-by-field configuration is in `config.schema.md`.

## Files

`SKILL.md` (contract), `README.md`, `DESIGN.md`, `config.example.json`, `config.schema.md`.
