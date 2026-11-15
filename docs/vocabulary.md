# Canonical Vocabulary

All four packages use this vocabulary. Terms are role-free and vendor-free. When a new concept is introduced, add it here before using it in a package.

## Core terms

| Term | Meaning | Replaces | Notes |
| --- | --- | --- | --- |
| `entity` | The subject a record or result belongs to | Any industry-specific human role, agent name, member name | Always resolved from an explicit identifier or a configured mapping. Never guessed. |
| `channel` | A message source or message destination | Named group, room, chat, DM, team channel | Identified by a config-level channel identifier. Reading and writing are separate permissions. |
| `workbook` | A spreadsheet file with an existing layout that must be preserved | Named spreadsheet product, a named report file | Treated as read-mostly. Structural changes require an explicit policy hook. |
| `approver` | The human who authorizes an irreversible action | Manager, owner, team lead, initiator | The only actor allowed to cross an approval gate. An agent must never stand in for the approver. |
| `recipient` | The target of a one-to-one delivery | A named individual receiving a private result | Delivery is one recipient per message; group delivery is a different action with different rules. |
| `source` | A configured origin of records or items | A named feed, API, website, directory or inbox | Each source declares its own freshness window and failure behavior. |
| `run` | One execution instance of a pipeline | A round, poll, batch, job, trigger | Keyed by business period plus a content fingerprint. Re-running a run must be safe. |
| `ledger` | The durable idempotency store that decides whether a record has already been accounted for | A named database table, state file, dedup log | Append-oriented. Never physically deletes entries; superseded entries are marked. |
| `business period` | The logical date or period a record belongs to | A specific calendar convention or shift boundary | Derived from the record, not from the wall-clock time of the run. |
| `policy hook` | A configurable decision point where domain-specific rules are injected | Hardcoded reward, penalty, ranking or wording rules | Keeps the blueprint free of any one organization's business logic. |
| `adapter` | A project-specific implementation of an interface declared in `DESIGN.md` | A named vendor client or SDK call | Adapters are outside this repository. |

## Invariant glossary

| Term | Definition |
| --- | --- |
| `idempotency key` | A stable string derived from business period, entity and a content fingerprint. A successful delivery or write with the same key is never repeated. |
| `fingerprint` | A hash over the exact inputs, rules and results used by a run. Any change to those inputs invalidates an approval tied to the previous fingerprint. |
| `approval gate` | An explicit step between a verified result and an external irreversible action. Dry-run is on until the approver crosses it. |
| `BLOCK` | Verification outcome that forbids approval and delivery. Requires fixing inputs or rules. |
| `REVIEW` | Verification outcome that allows approval only when the approver explicitly accepts the flagged items. |
| `PASS` | Verification outcome that permits the approval gate to open. |
| `surgical write` | A write that changes only the specified cells or parts of an existing workbook, leaving every other part byte-identical. |
| `backup checkpoint` | A copy of the exact pre-write file state, verified before any write and retained for rollback. |
| `degradation` | Continuing with reduced function when one source or delivery path fails, while recording the loss explicitly. Silence is not a valid degradation. |
| `record without write` | Registering a record in the ledger when its target workbook does not exist, without creating a new workbook. |
| `ownership precedence` | The fixed order used to resolve which group an entity belongs to: configured mapping, then explicit record field, then source-channel inference. |

## Naming conventions

- Package slugs are lowercase `kebab-case` and describe a mechanism, never a domain.
- Config keys use `snake_case` and never contain a product, brand or role name.
- Placeholders use upper snake case in angle brackets, for example `<CHANNEL_ID>`, `<WORKBOOK_DIR>`.
- Environment variables are prefixed with the package name in upper snake case, for example `DIGEST_DISPLAY_TIMEZONE`.
- No config key, file name, concept or comment may be written in a language other than English.

## Anti-patterns

- Naming a package after the original business domain.
- Embedding a fixed clock time, weekday or calendar day in a procedure instead of a config field.
- Adding a domain-specific reward, penalty or greeting rule directly to a specification.
- Using a vendor product name as a synonym for a generic capability.
- Allowing an agent to self-approve, self-issue a token, or infer an entity identity from ambiguous text.
