# Configuration Schema: Scheduled Digest Publisher

Copy `config.example.json` to a local `config.json` (gitignored) or override individual fields with environment variables. Every value that differs between deployments is a config field. Placeholders in the example are in `<ANGLE_BRACKETS>` and must be replaced before use.

Environment variables use the `DIGEST_` prefix and override the corresponding config value. Nested fields use double underscores, for example `DIGEST_DELIVERY__ALLOWLIST`.

## Top level

| Field | Type | Required | Default | Environment override | Description |
| --- | --- | --- | --- | --- | --- |
| `schema_version` | integer | yes | `1` | `DIGEST_SCHEMA_VERSION` | Version of this config shape. Reject unknown major versions at startup. |

## `schedule`

| Field | Type | Required | Default | Environment override | Description |
| --- | --- | --- | --- | --- | --- |
| `cron` | string | yes | `0 9 * * *` | `DIGEST_SCHEDULE__CRON` | Trigger expression. Interpreted in `schedule.timezone`, not in the display timezone. |
| `timezone` | string | yes | - | `DIGEST_SCHEDULE__TIMEZONE` | IANA timezone name for the trigger. |
| `enabled` | boolean | no | `true` | `DIGEST_SCHEDULE__ENABLED` | Allows disabling the schedule without deleting config. |

## `business_period`

| Field | Type | Required | Default | Environment override | Description |
| --- | --- | --- | --- | --- | --- |
| `display_timezone` | string | yes | - | `DIGEST_DISPLAY_TIMEZONE` | The single timezone used for every timestamp in the message. |
| `window_hours` | integer | no | `30` | `DIGEST_BUSINESS_PERIOD__WINDOW_HOURS` | Editorial freshness window. Independent of the collection query range. |
| `query_padding_days` | integer | no | `1` | `DIGEST_BUSINESS_PERIOD__QUERY_PADDING_DAYS` | Days added before and after the display period when querying sources. Must be at least 1. |
| `clock` | string | no | `system` | `DIGEST_BUSINESS_PERIOD__CLOCK` | Must be `system`. Never derive dates or weekdays from model memory. |

## `sources[]` and `schedule_source`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | yes | Stable identifier used in logs and the source list. |
| `type` | string | yes | Adapter type (`feed`, `api`, or a custom registered adapter). |
| `endpoint` | string | yes | Source endpoint, injected at deployment time. |
| `category` | string | no | Default category for items from this source. |
| `enabled` | boolean | no | When false, the source is skipped and not counted as a failure. |

`schedule_source` supplies occurrences and the next occurrence for the focus entity. It uses the same field shape.

| Field | Type | Required | Environment override | Description |
| --- | --- | --- | --- | --- |
| `source_denylist` | array of strings | no | `DIGEST_SOURCE_DENYLIST` | Source ids that failed a freshness validation. Only removable after revalidation. |

## `selection`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `min_items` | integer | no | `8` | Lower bound. A shortfall is logged, not filled with stale items. |
| `max_items` | integer | no | `12` | Hard upper bound on published items. |
| `categories` | array of strings | yes | - | Allowed categories. Values are project-defined; no domain terms are assumed here. |
| `dedupe_by` | string | no | `normalized_title_and_fact` | Deduplication strategy. Exact string equality is insufficient. |
| `require_source_link` | boolean | no | `true` | Every published item must carry a traceable link. |

## `focus`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `entity_id` | string | yes | Identifier of the entity that is always highlighted. |
| `entity_label` | string | yes | Display label for the focus section. |
| `always_first` | boolean | no | Must remain `true`; the section is never omitted. |
| `heading_marker` | string | no | Stable visual marker for the focus heading. |
| `require_next_occurrence_when_absent` | boolean | no | When true, a period without an occurrence must state the next one. |

## `verification`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `min_cross_checks` | integer | no | `2` | Minimum independent checks for claims involving numbers, names, statuses or times. |
| `require_source_links` | boolean | no | `true` | Same as the selection-level requirement; kept here for verification auditing. |
| `on_conflict` | string | no | `prefer_traceable_authority` | Conflict resolution policy. Unverifiable claims are omitted. |

## `delivery`

| Field | Type | Required | Environment override | Description |
| --- | --- | --- | --- | --- |
| `channel_adapter` | string | yes | `DIGEST_DELIVERY__CHANNEL_ADAPTER` | Registered adapter identifier. No vendor name belongs in this file. |
| `identity` | string | no | `DIGEST_DELIVERY__IDENTITY` | Sending identity, for example `service`. |
| `allowlist[].channel_id` | string | yes | `DIGEST_DELIVERY__ALLOWLIST` | Channel identifier. Never guess it. |
| `allowlist[].enabled` | boolean | yes | - | Only `true` entries receive messages. Start with `false`. |
| `idempotency_key_template` | string | yes | - | Must include `{period}` and `{channel_id}` and `{key_suffix}`. |
| `key_suffix` | string | no | `DIGEST_DELIVERY__KEY_SUFFIX` | Empty for scheduled runs. |
| `test_key_suffix` | string | no | `test` | Non-empty suffix for manual tests, so a test cannot suppress a scheduled run. |
| `render_mode` | string | no | `DIGEST_DELIVERY__RENDER_MODE` | Preferred rendering mode. |
| `render_fallback` | string | no | `plain_text` | Used automatically when the preferred mode fails. Fallback must not change the idempotency key. |

## `output`

| Field | Type | Required | Environment override | Description |
| --- | --- | --- | --- | --- |
| `root` | string | yes | `DIGEST_OUTPUT__ROOT` | Relative output root. All artifacts go under `root/<period>/`. |
| `per_period_dir` | boolean | no | - | When true, isolate each period in its own directory. |
| `artifacts` | array of strings | no | - | Names of the artifacts the run is allowed to write. |

## Validation rules

1. `display_timezone` and `schedule.timezone` must be valid IANA names.
2. `query_padding_days` must be at least 1; a value of 0 is rejected because single-day collection is incorrect across timezone boundaries.
3. `idempotency_key_template` must contain all three placeholders.
4. At least one `allowlist` entry must be enabled before delivery is allowed; otherwise the run is a dry run.
5. Every `endpoint`, `channel_id` and `entity_id` must be a non-placeholder value at runtime.
6. Startup must fail if any config value still contains `<` and `>` placeholder markers.

## Wizard (`wizard`)

All four packages carry an identically structured `wizard` section. It records the choices collected by the shared onboarding contract; see [docs/onboarding-contract.md](../../docs/onboarding-contract.md) for the nine steps, the option catalogs, the quick-start preset, the applicability matrix and the boundary conditions.

| Field | Required | Description |
| --- | --- | --- |
| `mode` / `preset` | yes | `guided` or `custom`; `daily_intake` is the quick-start preset |
| `connector.platform` | yes | `feishu`, `wecom` or a registered connector identifier. A config value only, never a blueprint concept |
| `connector.selected_group_ids` | yes | Exact identifiers after multi-select; empty until the user chooses |
| `connector.group_isolation` / `match_by` | yes | `per_group` / `exact_id`; groups are never merged or matched by name |
| `message_sources` | yes | Selected types from `message_source_options`; each needs a declared extractor |
| `output.mode` | yes | `existing_report`, `new_report`, `message_only` or `artifact_export` |
| `output.existing_report.write_mode` | yes | `existing_cells` or `new_sheet` |
| `output.new_report.*` | yes | `enabled` stays false until authorization, template, target dir, backup and no-overwrite are all set |
| `notifications.selected_templates` / `channel_binding` | yes | Chosen from `minimal`, `compact_professional`, `alert_only`, `full_audit`; bound per channel |
| `schedule.*` | yes | Preset or custom cron, IANA timezone, and `user_confirmed: true` before install |
| `confirmation.*` | yes | Full review, dry-run on, trial run with writes disabled, explicit user confirmation |

Additional validation: the `wizard` key structure must be identical across all four packages; `new_report.enabled` may be `true` only with `authorized_by` present; `full_audit` must not be bound to a public channel.
