# Abstraction Map

This document records how the four production skills were reduced to capability-level blueprints. It is a design log, not a migration script: the original skills remain untouched in their own directories and keep serving their scheduled automations.

## Old-to-new mapping

Legacy package names are intentionally not reproduced here. They contained project names, product brands, industry roles and one non-English label; keeping them would reintroduce exactly the vocabulary this repository removes. They remain only in the private source directories, which were left untouched.

| Legacy origin (described, not named) | New package | Mechanism retained | Vocabulary removed |
| --- | --- | --- | --- |
| Legacy skill 1: a scheduled briefing combining current headlines with an event schedule | `scheduled-digest-publisher` | Periodic multi-source aggregation, window filtering, ranking, one focus entity, timezone normalization, template rendering, allowlisted delivery, per-period idempotency, per-source degradation | News site names, league and team names, a named team as the permanent focus, a specific messaging product, a named schedule provider, a hardcoded channel identifier, hardcoded source URLs |
| Legacy skill 2: a periodic calculation of per-person amounts from historical results | `verified-batch-calculation` | Two capabilities only (compute, verify), per-entity declarative rules, independent recomputation, multi-class verification, approval gate bound to a fingerprint, per-recipient private delivery, dry-run default, read-only inputs | A transport role, compensation nouns, transport-document nouns, unrelated aggregation, a named directory of people, a fixed monthly trigger day, a named messaging product, real names and amounts |
| Legacy skill 3: a periodic sync of posted performance records into fixed-layout spreadsheets | `message-to-workbook-sync` | Two message formats, semantic field normalization, alias mapping, glued field/value splitting, entity-to-group ownership precedence, cell-level surgical writes into existing workbooks, backup before write, correction and overwrite, cross-period corrections, multi-round polling, business-period rules, anomaly escalation, tiered aggregated summaries | Store names, a service-industry role, per-person names, group names and identifiers, a named spreadsheet product, absolute machine paths, a reward/penalty policy, a fixed three-round clock schedule, fixed warm-message wording, hardcoded highlight color semantics |
| Legacy skill 4: automated collection of submitted payment evidence (original directory name was non-English) | `document-intake-ledger` | Document and image extraction, sender-based attribution, four-layer deduplication, append-only detail-sheet writes with backup/verify/rollback, a status state machine, confirmation tasks with permission separation, two-tier notifications, period aggregation | A transport role, reimbursement and expense nouns, department names, group names and identifiers, a named spreadsheet product, absolute machine paths, real names and amounts, a joke library, handwritten-document policy wording, ledger database files and screenshots |

The two chat-to-workbook skills were kept as separate packages. They share a family resemblance but their invariants differ: one performs surgical **cell updates** on a fixed date grid and must never append rows, while the other performs **append-only record writes** behind a deduplication ledger. Merging them would have forced a configuration surface large enough to obscure both invariants.

## Removed categories

Every item in these categories was removed from names, concepts and design documents:

- **Project and brand names**: marketplace skill names, product names, vendor CLI names, service homepages, CDN hosts.
- **Business roles**: any human role tied to a specific industry. Replaced with `entity`, `approver`, `recipient`.
- **Organization-specific rules**: reward and penalty formulas, quota thresholds, exemption lists, mandatory phrasing, joke libraries, fixed greeting text, fixed color conventions. Replaced with configurable policy hooks, or dropped where the rule had no general meaning.
- **Real identifiers**: account and chat identifiers, sender identifiers, real personal names, real amounts, absolute home-directory paths, local database files, downloaded images.
- **Vendor bindings**: named messaging clients, named schedule APIs, named spreadsheet engines, proprietary authentication flows. Replaced with adapter interfaces.
- **Fixed schedules**: specific clock times and calendar days moved into config fields.

## Decisions confirmed before finalization

None of the following was assumed; each was confirmed individually before any file was written.

| # | Decision | Confirmed choice |
| --- | --- | --- |
| 1 | Scope | Four self-authored business skills only |
| 2 | Granularity | Keep 1:1; do not merge overlapping capabilities |
| 3 | Naming depth | Capability-level names with zero domain words |
| 4 | Repository layout | Single monorepo |
| 5 | Deliverable depth | Specifications and design documents only, no implementation code |
| 6 | Configuration policy | `config.example.json` schema plus environment-variable overrides; local config gitignored |
| 7 | Core vocabulary | Generic role/system terms (`entity`, `channel`, `workbook`, `approver`, `recipient`, `source`, `run`, `ledger`) |
| 8 | Output and remote | New copy in the workspace; originals untouched; remote owner left as a placeholder |
| 9 | Name for skill 1 | `scheduled-digest-publisher` |
| 10 | Name for skill 2 | `verified-batch-calculation` |
| 11 | Name for skill 3 | `message-to-workbook-sync` |
| 12 | Name for skill 4 | `document-intake-ledger` |
| 13 | Repository name | `agent-skill-blueprints` |
| 14 | License | MIT with a `<COPYRIGHT_HOLDER>` placeholder |
| 15 | Package file set | `SKILL.md`, `README.md`, `DESIGN.md`, `config.example.json`, `config.schema.md` |

Requirement-level constraints applied without a decision point, because they were stated explicitly in the request: all abstracted naming, concepts and design documents use English only; every uncertain naming, concept and design decision is confirmed item by item before finalization; and a complete repository-creation command sequence is delivered after the transformation.

## Language policy

English is used for every name, concept, design document, example, configuration key and inline note. Localized trigger phrases were not carried over. A downstream project that needs them adds them in its own adapter layer; adding them here would reintroduce a language-specific assumption into a reusable blueprint.

## Exclusions

| Package | Reason for exclusion |
| --- | --- |
| A third-party marketplace-installed real-estate assistant | Installed from a marketplace rather than authored here; bound to a proprietary CLI, a vendor API key and a brand. Republishing it under a personal repository would create attribution and licensing risk, and abstracting away the vendor would remove the entire capability. |
| The author-side skill repository toolkit | A maintenance tool for creating, publishing and auditing repositories, not a reusable agent capability. It contains a hardcoded account name and vendor-specific paths. Its own documentation already states it is not distributed. |

## Consequence for downstream users

Because the packages are blueprints rather than runnable integrations, adopting one requires implementing the adapter interfaces listed in its `DESIGN.md`. In exchange, nothing in the specification expires when a vendor changes an API, and no project has to rename another project's business concepts.

## Onboarding wizard decisions (confirmed later in the same session)

| # | Decision | Confirmed choice |
| --- | --- | --- |
| 16 | Scope | One shared contract for all four abstract packages; each applies only its relevant steps |
| 17 | Form | Contract document plus a `wizard` config section; no connector code, no script refactor |
| 18 | New report creation | Allowed, but only with explicit per-run authorization, a template, a target directory, backups and no-overwrite |
| 19 | Multiple selected groups | Per-group isolation: independent read, aggregation, write and notification; never merged |
| 20 | Notification templates | All four retained: `minimal`, `compact_professional`, `alert_only`, `full_audit` |
| 21 | Quick-start preset | Daily intake: single platform, one group, image plus template messages, existing report with a new sheet, two notification tiers, daily 09:00, dry-run |
| 22 | Schedule input | Preset time slots plus a user-supplied custom cron and an explicit timezone |
| 23 | Platform naming | `feishu` / `wecom` allowed as config option values and in the documentation of those values; all concepts, docs and comments remain English ASCII |

Platform capability at the time of writing: the Feishu connector is bound but disabled, and no managed WeCom connector is available, so WeCom group discovery requires a project-supplied adapter. This is an environment fact, not part of the blueprint design.

## Productization decisions (same session, final round)

The delivery standard changed from "readable specification" to "clone, interact once, run immediately, with no per-user adaptation". That supersedes the earlier docs-only decision (#5) and the no-implementation-code rule.

| # | Decision | Confirmed choice |
| --- | --- | --- |
| 24 | Product form | Four independent runnable skills, each self-contained and separately installable |
| 25 | Dependencies | Python standard library only; no pip install, no vendor SDK |
| 26 | Platform depth | Adapter interfaces only; feishu / wecom are config options, no real API calls |
| 27 | Publication | New public repository `allen49548/agent-skill-blueprints` |

Each package now ships `run.py`, an identical `engine.py`, `profile.json`, bundled `examples/demo_input.json` and an `engine` config section. Commands: `demo`, `setup`, `doctor`, `run`, `info`, `install`. `engine.py` implements local-folder / JSON / webhook inputs, CSV / JSON / XLSX outputs (including zip-level sheet insertion and surgical cell updates), stdout / webhook notifiers, all four notification templates, a business-key dedup ledger and a full run log.

## Maturity refactor decisions (same session)

A review against common open-source quality signals found that the first release optimised the first 30 seconds (clone and demo) rather than the 100th change. The following changes were made without further questions because they implement the review recommendations already agreed.

| # | Decision | Change |
| --- | --- | --- |
| 28 | Documentation honesty | Added `docs/capability-matrix.md`; every `DESIGN.md` and `SKILL.md` now carries an implementation-status banner. Capability-specific mechanisms are labelled target design |
| 29 | Single source of truth | `skillkit/engine.py` replaces four byte-identical `engine.py` copies; `run.py` files are shims; `build.py` generates standalone packages into gitignored `dist/` |
| 30 | Invariants as tests | 22 standard-library unit tests and a Python 3.9-3.13 CI matrix; fixed the non-idempotent `_append_sheet` |
| 31 | Project governance | `VERSION`, `CHANGELOG.md`, `SECURITY.md`, issue templates, `tools/check_repo.py`, structured run log, adapter registry validation, resolved LICENSE placeholder |

Version 0.2.0. The six `run.py` commands are unchanged, so the fresh-clone workflow still works.
