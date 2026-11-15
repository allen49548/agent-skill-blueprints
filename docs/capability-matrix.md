# Capability matrix

This document states what actually runs today versus what is a target design. It exists because a beautiful `DESIGN.md` that describes unwritten code is worse than no design document: people make safety decisions based on it.

Read this before relying on any invariant.

## Status values

| Value | Meaning |
| --- | --- |
| Implemented | Code exists in `skillkit/engine.py`, is exercised by `tests/` on every commit, and works in `python3 run.py demo` |
| Partial | Some of the described behaviour runs; the rest is configuration or a placeholder |
| Contract only | The config field, wizard step or interface exists, but no working implementation is bundled |
| Target design | Described in `DESIGN.md` as the intended capability; not implemented |

## Shared runtime

| Capability | Status | Notes |
| --- | --- | --- |
| `demo` / `setup` / `doctor` / `run` / `info` / `install` | Implemented | Standard library only |
| `build.py` standalone packages | Implemented | Four self-contained packages into gitignored `dist/` |
| Input: `local_folder`, `json_file`, `webhook` | Implemented | webhook uses `urllib` |
| Output: CSV, JSON | Implemented | |
| Output: XLSX new workbook, add/replace named sheet, surgical cell update | Implemented | zip-level part replacement; other parts stay byte-identical |
| Notifications: `minimal`, `compact_professional`, `alert_only`, `full_audit` | Implemented | stdout and webhook notifiers |
| Business-key deduplication and JSON ledger | Implemented | Equal values are never duplicates; group is part of the key |
| Dry-run, backup, byte-identical verification, rollback path | Implemented | Covered by tests |
| Wizard steps 0, 3-8 (preset, sources, output, templates, schedule config, review, trial run) | Implemented | Schedule is written to config; no scheduler is installed |
| Structured JSON-lines run log | Implemented | `run.log` |
| Adapter registry validation in `doctor` | Implemented | Rejects unregistered adapter names |
| CI on Python 3.9-3.13 | Implemented | Tests, four demos, build verification, hygiene gate |

## Platform and scheduling

| Capability | Status | Notes |
| --- | --- | --- |
| `feishu` / `wecom` as config option values | Contract only | No vendor SDK is bundled |
| List all groups for multi-select | Contract only | The built-in discovery lists local inbox folders; a real platform needs a project-supplied adapter |
| Reading messages from a real platform | Target design | Adapter slot defined in `docs/onboarding-contract.md` |
| Sending to a real platform channel | Target design | Only stdout / generic webhook run today |
| Installing a scheduled job | Target design | `setup` writes cron and timezone into config; nothing schedules the run |

## Per-skill capability-specific mechanisms

The four packages share one generic pipeline. Their distinctive mechanisms are **target designs**, not code. `profile.json` currently changes defaults (output adapter, templates, schedule, message sources) only.

| Package | Described capability | Status |
| --- | --- | --- |
| `verified-batch-calculation` | Independent recomputation, 8 verification classes, `BLOCK`/`REVIEW`/`PASS`, fingerprint-bound approval gate | **Target design. Not implemented.** The runtime contains no verification stage |
| `scheduled-digest-publisher` | Multi-source feed/API fetching, ranking, focus-entity spotlight, timezone normalization | **Target design. Not implemented.** |
| `message-to-workbook-sync` | Semantic field normalization, alias maps, glued field/value splitting, ownership precedence, multi-round polling | **Target design. Not implemented.** Only raw JSON/JSONL records are read |
| `document-intake-ledger` | Image/document extraction, four-layer deduplication (L1-L3), status state machine, confirmation tasks | **Partial.** Only the L4 business-key dedup and append-only sheet writes are implemented; no OCR and no task backend |

## Consequences

- Do not treat any `DESIGN.md` invariant as enforced runtime behaviour unless the capability matrix says "Implemented".
- A project adopting a package must implement the missing mechanisms behind the declared adapter interfaces. The bundled runtime is a working skeleton, not the finished capability.
- Every row that moves from "Target design" to "Implemented" must come with tests in `tests/`.

## Keeping this honest

`tools/check_repo.py` verifies structure, encoding and privacy. It cannot verify prose. When implementation status changes, update this file in the same pull request as the code; the pull request checklist in `CONTRIBUTING.md` requires it.
