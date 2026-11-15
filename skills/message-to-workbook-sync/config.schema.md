# Configuration Schema: Message to Workbook Sync

Copy `config.example.json` to a local `config.json` (gitignored) or override individual fields with environment variables. Environment variables use the `SYNC_` prefix; nested fields use double underscores, for example `SYNC_SAFETY__WRITE_ENABLED`.

Placeholders in `<ANGLE_BRACKETS>` must be replaced before use. Startup must reject any config value that still contains placeholder markers.

## `channels`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `reader_adapter` | string | yes | Registered `ChannelReader` identifier. |
| `read_allowlist[].channel_id` | string | yes | Source channel identifier. Never guess it. |
| `read_allowlist[].group` | string | yes | Group used only as a fallback inference source. |
| `read_identity` | string | no | Identity used when reading; reading and sending permissions are separate. |
| `window_lookback_periods` | integer | no | Extra periods read to capture late corrections. |

## `workbooks`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `root` | string | yes | Directory containing existing workbook files. |
| `file_pattern` | string | yes | Resolves an entity to an existing file. Use `{entity}`. |
| `sheet_pattern` | string | yes | Resolves a business period to a sheet name. Use `{business_period}`. |
| `row_key` | string | yes | How the period row is located inside the sheet. |
| `target_cells` | object | yes | Canonical field to column mapping. Only these cells may be written. |
| `protected_regions` | array | yes | Regions a write must never touch. |
| `create_if_missing` | boolean | yes | Must remain `false`. This blueprint never creates a workbook. |

## `formats`, `field_map` and `alias_map`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `formats[].id` | string | yes | Shape identifier used in the change log. |
| `formats[].parser` | string | yes | Registered `MessageParser`. All enabled shapes must be parsed. |
| `formats[].multi_record_boundary_field` | string | no | Field that splits a message containing several records. |
| `formats[].enabled` | boolean | yes | Disabling a shape risks false absence markers; avoid it. |
| `field_map.<field>.target_cell` | string | yes | Target column. Fields without a target are ignored fields. |
| `alias_map.<synonym>` | string | no | Canonical field name that the synonym resolves to. |
| `canonical_field_names` | array | yes | Used for longest-prefix glued-value splitting. Order is by descending length at runtime. |
| `ignored_fields` | array | no | Fields recorded but not written, never treated as anomalies. |

## `normalization`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `unify_punctuation` | boolean | no | `true` | Unify full-width and half-width separators and strip internal whitespace. |
| `strip_units` | boolean | no | `true` | Remove units and separators before numeric parsing. |
| `glued_value_split` | string | no | `longest_prefix` | Must remain longest-prefix matching so digits inside field names are preserved. |
| `empty_value_policy` | string | yes | `zero` | One of `zero`, `leave_unchanged`, `manual_review`. The original production rule was `zero`; it is a deployment choice, not a universal rule. |
| `ambiguous_value_action` | string | yes | `skip_and_escalate` | Ambiguous values are never guessed. |
| `date_formats` | array | yes | - | Accepted business-period formats. A missing or ambiguous period is never defaulted to the run date. |

## `ownership` and `deduplication`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `ownership.entity_to_group` | object | yes | Authoritative mapping, highest precedence. |
| `ownership.precedence` | array | yes | Must be `[entity_to_group, record_field, source_channel]`. |
| `ownership.unresolved_action` | string | yes | `manual_review` for entities not in the mapping. |
| `ownership.allow_default_group` | boolean | yes | Must remain `false`. |
| `deduplication.key_fields` | array | yes | Must be `[business_period, entity, group]`. |
| `deduplication.same_key_strategy` | string | yes | `latest_by_source_timestamp`. |
| `deduplication.write_decision` | string | yes | Must be `compare_current_cell_value`; never a processed-keys flag. |

## `rounds`, `absence_marker` and `aggregation`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `rounds[].id` | integer | yes | Stable round identifier. |
| `rounds[].hour` | integer | yes | Clock hour that maps to this round. |
| `rounds[].business_period_offset_days` | integer | yes | Offset from the run date. A run just after midnight typically uses `-1`. |
| `rounds[].role` | string | yes | `backfill` or `finalize`. Exactly one finalize round is expected. |
| `absence_marker.enabled` | boolean | no | Whether entities with no record are visually marked in the finalize round. |
| `absence_marker.style` | string | conditional | Style identifier. A color or format is a deployment value, not a blueprint constant. |
| `absence_marker.clear_before_late_write` | boolean | no | Must be `true` so a late correction removes an absence marker. |
| `aggregation.scope` | string | yes | Must be `per_group`. |
| `aggregation.allow_cross_group_merge` | boolean | yes | Must remain `false`. |
| `aggregation.expose_entity_values` | boolean | yes | Controls whether per-entity values may appear in outbound summaries. |

## `policy_hooks` and `notifications`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `policy_hooks[].enabled` | boolean | yes | Disabled by default. Domain rules are injected here, never in the core. |
| `notifications.adapter` | string | yes | Registered `NotificationAdapter`. |
| `notifications.delivery_enabled` | boolean | yes | Start with `false` during onboarding. |
| `notifications.tiers.*` | object | no | Four tiers: run summary, anomaly escalation, final aggregation, operational detail. |
| `notifications.idempotency_key_template` | string | yes | Must contain `{period}`, `{round}`, `{tier}` and `{channel_id}`. |

## `output` and `safety`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `output.root` | string | yes | All logs, state and backups are written here. |
| `output.backup_dir` | string | yes | Per-period backup directory. Corrections create additional copies. |
| `output.change_log` | string | yes | Append-only across rounds. |
| `safety.write_enabled` | boolean | yes | Start with `false` to produce a change log only. |
| `safety.backup_required` | boolean | yes | Must remain `true`. |
| `safety.verify_untouched_parts` | boolean | yes | Must remain `true`. |
| `safety.rollback_on_verify_failure` | boolean | yes | Must remain `true`. |

## Validation rules

1. `create_if_missing`, `allow_default_group`, `allow_cross_group_merge` must be `false`.
2. `backup_required`, `verify_untouched_parts`, `rollback_on_verify_failure`, `clear_before_late_write` must be `true`.
3. Every enabled `formats[].parser` must be registered; an unregistered parser is a startup error.
4. `notifications.idempotency_key_template` must contain all four placeholders.
5. All `channel_id`, `root` and identifier values must be non-placeholder at runtime.
6. No real entity names, channel identifiers or absolute home-directory paths may appear in committed config examples, docs or logs. Runtime state and backups must be gitignored.

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
