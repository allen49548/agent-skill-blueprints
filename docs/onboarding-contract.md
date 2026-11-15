# Onboarding Contract

One shared, interactive onboarding contract for all four blueprints. It defines what a user must choose before a skill is allowed to read anything, write anything, send anything or run on a schedule.

This is a **contract layer**, not an implementation. An agent walks the user through the steps, collects the choices and writes the resulting `wizard` section into the package config. No connector code lives in this repository.

## Platform capability

| Platform | Config value | Group discovery | Notes |
| --- | --- | --- | --- |
| Feishu | `feishu` | Supported through a managed connector | The connector is bound but disabled by default; enable it from the connector menu before step 2. |
| WeCom | `wecom` | Requires a project-supplied adapter | No managed connector is currently available. The adapter must implement group listing and message reading. |

Both platforms are represented by the same `connector` abstraction. `feishu` and `wecom` appear only as **config option values** and in the documentation of those values; they are never used as concept names, field names or capability names in a blueprint. A project may register another connector identifier and use the same flow.

## Runnable form

Each package implements this contract with a self-contained runtime (`run.py` + `engine.py`, Python standard library only). No install step and no credentials are needed for the built-in adapters.

| Command | Contract role |
| --- | --- |
| `demo` | Runs the full pipeline on bundled sample data; proves the runtime without touching a platform |
| `setup` | Implements steps 0-7 and writes `config.json` |
| `doctor` | Validates `*_ref` pointers, adapters, timezone, dry-run state and authorization |
| `run` | Executes the pipeline; dry-run by default |
| `install --apply` | Copies the package into the local skills directory |

`profile.json` declares which steps apply to that package and its default choices. Real platform connectors are adapter slots: the wizard can select `feishu` or `wecom`, list their groups and store exact identifiers, but the network call itself is supplied by the project. This keeps a fresh clone runnable for every user without per-user code changes.

## The nine steps

| Step | Question to the user | Config path | Boundary |
| --- | --- | --- | --- |
| 0 | Quick start (recommended preset) or custom? | `wizard.mode`, `wizard.preset` | The preset is a starting point; every choice stays editable afterwards. |
| 1 | Which platform? | `wizard.connector.platform` | Only registered identifiers are accepted. Never guess. |
| 2 | Connect, list all groups, multi-select | `wizard.connector.selected_group_ids` | Exact identifiers only; never match by group name; retired groups are neither read nor notified. |
| 3 | Which message source types? | `wizard.message_sources` | Multi-select; each type must map to a declared extractor. |
| 4 | Which output target? | `wizard.output` | New reports require explicit authorization. |
| 5 | Which notification template per channel? | `wizard.notifications` | Template and channel are bound explicitly; field visibility is enforced by template. |
| 6 | When should it run? | `wizard.schedule` | The user must confirm the time; an agent never installs a default schedule silently. |
| 7 | Review all choices, then generate config | `wizard.confirmation` | Full echo of choices before anything is written; dry-run stays on. |
| 8 | Trial run | `wizard.confirmation.trial_run_writes_disabled` | Produce a change log only; no writes, no sends. |

An agent must not skip a step, collapse two steps into one question, or infer an answer from a previous conversation. If the user is unsure, offer the quick-start preset from step 0.

## Step 2: group discovery and multi-select

1. Connect to the selected platform.
2. Call the group-listing capability and present **all** groups with their display names and exact identifiers.
3. Let the user multi-select. Do not pre-select, do not limit the list, and do not hide groups the agent considers irrelevant.
4. Store exact identifiers in `selected_group_ids`. Display names are presentation only.
5. Echo the selection back to the user before continuing.
6. Default `group_isolation` is `per_group`: each selected group is read, aggregated, written and notified independently. Groups are never merged, and statistics or notifications never cross a group boundary.
7. Groups listed in the package's retired set are excluded from both reading and notification even if the user selects them; report that exclusion explicitly.

## Step 3: message source types

`message_source_options` is the shared catalog:

| Value | Meaning | Typical extractor |
| --- | --- | --- |
| `image` | Screenshots or photos | Vision extractor with a confidence threshold |
| `text` | Free-form plain text | Text parser with semantic normalization |
| `link` | URL-only or link-with-preview messages | Link resolver plus metadata extractor |
| `template_message` | Fixed-format or rendered template messages | Template parser driven by a field map |
| `card` | Structured interactive cards | Structured-field parser |
| `file` | Attached documents | Document extractor |
| `feed` | Syndicated feed items | Feed reader |
| `api` | Records from an HTTP endpoint | API adapter |
| `structured_record` | Already-normalized records | Identity mapping |

Rules: multi-select is allowed; every selected type must have a declared extractor; an unrecognized type is a startup error, never a best-effort guess. Text-only claims and unsupported document classes follow each package's existing policy (ignore or route to manual review), never an automatic value.

## Step 4: output target

| Mode | Sub-choice | Behavior |
| --- | --- | --- |
| `existing_report` | `existing_cells` | Write into existing cells of an existing workbook; never change its structure. |
| `existing_report` | `new_sheet` | Add exactly one detail sheet inside an existing workbook; never modify other parts. |
| `new_report` | - | Create a new workbook from a template. Requires explicit authorization. |
| `message_only` | - | No workbook output; the result is a message. |
| `artifact_export` | - | Write generated artifacts to the output root only. |

### New report authorization

Selecting `new_report` is the one action that relaxes the earlier "never create a workbook" rule. It is allowed only when all of these hold:

1. The user explicitly selected `new_report` in this run; it is never inferred from a missing target file.
2. `wizard.output.new_report.enabled` is `true` and `authorized_by` records who authorized it.
3. A `template` and `target_dir` are supplied.
4. `backup_required` is `true` and `never_overwrite_existing` is `true`: an existing file at the target path aborts the write instead of being replaced.
5. The choice is echoed in step 7 and a trial run (step 8) completes before the first real write.

If any condition is missing, fall back to `existing_report` with `record_without_write` behavior, or stop. Never create a file silently.

## Step 5: notification templates

Four templates are available for multi-select. A template is bound to a channel explicitly; one template per channel is the default.

| Template | Content | Intended channel | Never includes |
| --- | --- | --- | --- |
| `minimal` | One line per entity with value and date, plus a total | Public channel | Ledger states, outstanding totals, comparisons, record counts, business keys, file names, local paths |
| `compact_professional` | Per-entity sections, anomalies, pending items, ledger states, task links; may render as a structured card with mentions or buttons | Operator channel | Nothing excluded; this is the operational channel |
| `alert_only` | Nothing on a normal or no-change run; only failures, anomalies and blocking conditions | Duty or operations channel | Routine summaries |
| `full_audit` | Per-record detail, backup paths, delivery receipts, idempotency results | Private or archive channel | N/A, but must not be bound to a public channel |

Field visibility is enforced through `fields_visible` / `fields_hidden` inherited from the `adapters` layer. A template never widens the field set of its channel. `alert_only` conflicts with any package rule that requires a notification on every run; if that rule is enabled, the wizard must surface the conflict and ask the user to choose, not resolve it silently.

`delivery_whitelist` holds exact channel identifiers. Sending outside it is blocked.

## Step 6: schedule

The user chooses the time. Presets are offered for convenience, and a custom cron is always allowed.

| Preset | Cron | Timezone |
| --- | --- | --- |
| `daily_0900` | `0 9 * * *` | User-selected |
| `weekday_0900` | `0 9 * * 1-5` | User-selected |
| `daily_three_rounds` | `0 22,23,0 * * *` | User-selected |
| `monthly_1_4` | `0 9 1-4 * *` | User-selected |
| `monthly_10` | `0 9 10 * *` | User-selected |
| `hourly` | `0 * * * *` | User-selected |
| `custom` | User-supplied cron | User-selected |

Rules: `timezone` is mandatory and must be an IANA name; `user_confirmed` must be `true` before a schedule is installed; an agent never enables a schedule on the user's behalf. A custom cron is validated before acceptance.

## Step 0: quick-start preset (`daily_intake`)

Offered whenever the user is unsure. It is a set of editable defaults, not a locked configuration.

| Choice | Default |
| --- | --- |
| Platform | `feishu` |
| Groups | One selected group, `per_group` isolation |
| Message sources | `image`, `template_message` |
| Output | `existing_report` with `new_sheet`; `new_report` disabled |
| Notifications | `minimal` on the public channel, `compact_professional` on the operator channel |
| Schedule | `daily_0900`, user-selected timezone |
| Safety | `dry_run: true`, trial run with writes disabled |

The user may switch to `custom` at any point; switching does not discard choices already made.

## Applicability matrix

All four packages share this contract, but each implements only the steps relevant to its capability.

| Step | scheduled-digest-publisher | verified-batch-calculation | message-to-workbook-sync | document-intake-ledger |
| --- | --- | --- | --- | --- |
| 0 Preset | `custom` | `custom` | `daily_intake` | `daily_intake` |
| 1 Platform | Output side only | Output side only | Full | Full |
| 2 Group multi-select | N/A | N/A | Full | Full |
| 3 Message sources | `feed`, `api`, `text`, `link` | `file`, `structured_record` | `text`, `template_message`, `card` | `image`, `file` |
| 4 Output | `message_only` | `artifact_export` | `existing_report` / `existing_cells` | `existing_report` / `new_sheet` |
| 5 Templates | `minimal` | `compact_professional`, `alert_only` | `minimal`, `compact_professional` | `minimal`, `compact_professional` |
| 6 Schedule | `daily_0900` | `monthly_10` | `daily_three_rounds` | `daily_0900` |
| 7 Review | Full | Full | Full | Full |
| 8 Trial run | Full | Full | Full | Full |

A step marked N/A is skipped with a brief explanation, not silently omitted. Steps 7 and 8 are mandatory for every package.

## Unified boundary conditions

1. No read, write, send or schedule happens before step 7 completes.
2. Platform and group identifiers are exact values supplied by the platform, never guesses or name matches.
3. Multiple selected groups stay isolated; no cross-group aggregation or notification.
4. `new_report` is the only way to create a workbook, and only under the authorization rules above.
5. Every external action is dry-run by default; the first real run requires explicit confirmation.
6. A schedule is installed only after the user confirms the time and timezone.
7. Notification templates are bound to channels; field visibility is never widened by a template.
8. Every choice is echoed back before config generation. An agent never assumes a value because it was chosen in an earlier session.
9. A trial run produces a change log only. No writes, no sends, no task creation.
10. All values land in the package config; nothing is hardcoded into a blueprint document.
11. Existing package invariants survive onboarding: deduplication, backup plus verification plus rollback, approval gates, group isolation, and the hard block on per-entity private delivery where configured.

## `wizard` config section

Every package's `config.example.json` contains an identically structured `wizard` section; values differ per the applicability matrix.

| Field | Type | Description |
| --- | --- | --- |
| `schema_version` | integer | Version of the wizard shape. |
| `mode` | string | `guided` (step by step) or `custom` (user supplies config directly). |
| `preset` / `preset_options` | string / array | `daily_intake` or `custom`. |
| `connector.platform` / `platform_options` | string / array | Registered connector identifier and its allowed values. |
| `connector.connection_status` | string | `disconnected`, `connected` or `failed`. |
| `connector.group_discovery` | string | `list_all`. Never a filtered or partial list. |
| `connector.group_selection` | string | `multi`. |
| `connector.selected_group_ids` | array | Exact identifiers chosen by the user. Empty until step 2 completes. |
| `connector.group_isolation` | string | `per_group`. |
| `connector.match_by` | string | `exact_id`. |
| `message_sources` / `message_source_options` | array | Selected types and the shared catalog. |
| `output.mode` / `mode_options` | string / array | One of the five output modes. |
| `output.existing_report.write_mode` | string | `existing_cells` or `new_sheet`. |
| `output.existing_report.sheet` | string | Target sheet name. |
| `output.existing_report.create_workbook_if_missing` | boolean | Must stay `false`. |
| `output.new_report.enabled` | boolean | `false` until explicit authorization. |
| `output.new_report.requires_explicit_authorization` | boolean | Must stay `true`. |
| `output.new_report.authorized_by` | string or null | Who authorized creation. |
| `output.new_report.template` / `target_dir` | string | Template and directory. |
| `output.new_report.backup_required` | boolean | Must stay `true`. |
| `output.new_report.never_overwrite_existing` | boolean | Must stay `true`. |
| `notifications.template_catalog` | array | The four templates. |
| `notifications.selected_templates` | array | Templates chosen for this deployment. |
| `notifications.channel_binding` | object | Template per channel. |
| `notifications.delivery_whitelist` | array | Exact channel identifiers. |
| `schedule.preset` / `preset_options` | string / array | Chosen preset and allowed presets. |
| `schedule.cron` | string | Effective cron expression. |
| `schedule.timezone` | string | IANA timezone name. |
| `schedule.user_confirmed` | boolean | Must be `true` before a schedule is installed. |
| `schedule.custom_cron_allowed` | boolean | Must stay `true`. |
| `confirmation.review_all_choices` | boolean | Must stay `true`. |
| `confirmation.dry_run` | boolean | Must start `true`. |
| `confirmation.trial_run_writes_disabled` | boolean | Must start `true`. |
| `confirmation.user_confirmed` | boolean | Must be `true` before real writes or sends. |

## Validation checklist

- [ ] All four packages have an identically structured `wizard` section.
- [ ] Every `selected_group_ids` entry is an exact identifier, not a display name.
- [ ] `group_isolation` is `per_group` and `match_by` is `exact_id`.
- [ ] Every selected message source has a declared extractor.
- [ ] `new_report.enabled` is `true` only with `authorized_by`, `template`, `target_dir`, backups and no-overwrite all set.
- [ ] `full_audit` is not bound to a public channel.
- [ ] `alert_only` conflicts are surfaced to the user rather than resolved silently.
- [ ] `schedule.user_confirmed` and a valid IANA timezone are present before install.
- [ ] `confirmation.user_confirmed` is `true` before any real write or send.
- [ ] The trial run produced a change log and zero external effects.
