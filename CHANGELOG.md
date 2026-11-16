# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog and the project uses semantic versioning.

Version numbers refer to the shared runtime and the repository as a whole. `config.example.json` carries its own `schema_version` and `wizard.schema_version`; a change to either requires a migration note here.

## [0.2.2] - 2026-11-16

### Changed

- The five `README.md` files were tightened into a shorter, scannable structure (one-line pitch, status banner, use / avoid, quick start, next steps); the root README dropped from ~145 to ~85 lines.

### Performance

- `_update_cells` now rewrites targeted cells in a single compiled-regex pass over the sheet XML instead of recompiling a pattern and rebuilding the whole string for every cell (quadratic -> linear).
- `_col_letters` is memoized with `lru_cache`; sheet/cell/value regexes are compiled once at import time.
- `io.BytesIO` uses a top-level `import io` instead of a runtime `__import__`.
- `dedupe` stamps the whole batch with one timestamp and skips rewriting the ledger when nothing new was kept.
- Backup filenames now include microseconds so two writes in the same second no longer collide.

No public API change. All 22 tests and the repository gate pass.

## [0.2.1] - 2026-11-15

### Changed

- All five `README.md` files are now Chinese (repository root plus the four skills). Commands, identifiers, config keys and file paths remain in English.
- `SKILL.md`, `DESIGN.md`, `docs/`, code comments and config keys remain English, so concepts and naming stay language-neutral.
- `tools/check_repo.py` exempts READMEs from the ASCII gate, allows platform names in user-facing docs, and now asserts that all five READMEs actually contain Chinese. Business-specific vocabulary remains forbidden.
- `PUBLISHING.md` ASCII pre-flight and `CONTRIBUTING.md` language rule updated to match.

No runtime behaviour changed. Tests, CI matrix and capability statuses are unchanged.

## [0.2.0] - 2026-11-15

Refactor release. The public API (the six `run.py` commands) is unchanged; the internal layout and the guarantee behind it changed.

### Added

- Single runtime source: `skillkit/engine.py`. The four skills now use thin `run.py` shims; no duplicated engine is committed.
- `build.py` generates four standalone, individually distributable packages into gitignored `dist/`, with `BUILD_INFO.json` carrying the engine digest.
- `tests/`: 22 standard-library unit tests covering business-key deduplication, group isolation, idempotent reruns, backup and byte-identical untouched parts, dry-run, XLSX writes, template field leakage, repository structure, all four demos, setup/doctor and standalone builds.
- `.github/workflows/ci.yml`: Python 3.9-3.13 matrix running tests, four demos and build verification, plus a hygiene job.
- `tools/check_repo.py`: encoding, privacy, JSON, structure and tracked-artifact gate.
- `docs/capability-matrix.md`: explicit implemented / partial / contract-only / target-design status for every capability.
- `VERSION`, `CHANGELOG.md`, `SECURITY.md`, issue templates.
- Structured JSON-lines `run.log` and an adapter registry validated by `doctor`.
- `skillkit.__version__` exposed programmatically.

### Fixed

- `_append_sheet` was not idempotent: every rerun created a new worksheet part, relationship and content-type override. It now replaces the named sheet in place. Covered by a test that reruns four times.
- `doctor` previously printed adapter names without verifying them; it now rejects unregistered adapters.
- `install --apply` now installs a self-contained copy rather than referencing a duplicated engine file.
- LICENSE copyright placeholder resolved.

### Changed

- `CONTRIBUTING.md` no longer needs a rule to keep four engine copies byte-identical.
- `DESIGN.md` files in all four packages now carry an implementation-status banner pointing at the capability matrix.
- Documentation no longer implies that platform connectors, scheduled execution or per-skill verification logic are implemented.

## [0.1.0] - 2026-11-15

Initial public release.

- Four capability blueprints with English-only, project-independent naming and design documents.
- Shared nine-step onboarding contract and `wizard` config section.
- Zero-dependency runnable runtime with demo, setup, doctor, run, info and install commands.
- Built-in local-folder/JSON/webhook inputs, CSV/JSON/XLSX outputs, stdout/webhook notifiers and four notification templates.
- Published as a public repository with a verified fresh-clone workflow.
