# Configuration Schema: Verified Batch Calculation

Copy `config.example.json` to a local `config.json` (gitignored) or override individual fields with environment variables. Environment variables use the `CALC_` prefix; nested fields use double underscores, for example `CALC_DELIVERY__DRY_RUN`.

Placeholders in `<ANGLE_BRACKETS>` must be replaced before use. Startup must reject any config value that still contains placeholder markers.

## Top level and `period`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `schema_version` | integer | yes | `1` | Config shape version. Reject unknown major versions. |
| `period.id_format` | string | yes | `YYYY-MM` | Business period identifier format. |
| `period.derivation` | string | yes | `system_clock` | Must be `system_clock`; never derive dates from memory. |
| `period.schedule_cron` | string | no | - | Trigger expression. A specific calendar day is a deployment choice, not a blueprint constant. |
| `period.schedule_timezone` | string | no | - | IANA timezone for the trigger. |
| `period.scheduled_run_stops_at` | string | yes | `preview` | Must remain `preview`. A scheduled run never confirms or dispatches. |

## `registry`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `adapter` | string | yes | Registered `RegistryAdapter` identifier. |
| `source` | string | yes | Registry endpoint, injected at deployment time. |
| `cache_path` | string | yes | Local cache. Gitignored. Sync is read-only against the source. |
| `alias_map` | object | no | Alternative labels mapped to canonical entity identifiers. |
| `elastic` | boolean | no | When true, only entities with records in the period are computed; no zero-value padding, no missing-entity alerts. |
| `exclude_identities` | array | no | Non-entity identities such as service accounts or owners. |

## `record_sources[]`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | yes | Stable source identifier used in the fingerprint. |
| `type` | string | yes | Adapter type (`table`, `api`, or a custom registered adapter). |
| `location` | string | yes | Input location. Inputs are strictly read-only. |
| `field_map` | string | yes | Field mapping file. An ambiguous mapping is a stopping error, never a guess. |
| `enabled` | boolean | no | Disabled sources are excluded from the fingerprint. |

## `transcription`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `enabled` | boolean | no | Whether document transcription is part of input preparation. |
| `adapter` | string | conditional | `Transcriber` identifier. |
| `low_confidence_action` | string | no | Must be `manual_review`; never `guess`. |
| `confidence_threshold` | number | no | Below this value, a row goes to manual review. |

## `rules`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `path` | string | yes | - | Confirmed declarative rule set. |
| `candidates_path` | string | no | - | Inferred rules; always `confirmed=false`. |
| `require_human_confirmation` | boolean | yes | `true` | Must remain true. Unconfirmed rules produce `BLOCK`. |
| `allow_arbitrary_expressions` | boolean | yes | `false` | Must remain false. No dynamic code evaluation. |
| `allowed_operators` | array | yes | - | Closed operator allowlist for the rule DSL. |

## `precision` and `verification`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `precision.scale` | integer | no | `2` | Decimal scale. |
| `precision.rounding` | string | no | `half_up` | Rounding mode. |
| `precision.round_per_row_before_sum` | boolean | no | `true` | Prevents floating-point drift from creating false verification failures. |
| `verification.independent_recompute` | boolean | yes | `true` | Must remain true. The verify path must not reuse the compute evaluator. |
| `verification.classes.*` | string | yes | - | One of `blocking`, `advisory`, `disabled`. Eight classes are defined in `DESIGN.md`. |
| `verification.anomaly_threshold_percent` | number | no | `30` | Deviation that produces `REVIEW`. |
| `verification.external_reference_source` | string | no | - | Optional reference set for class 6. |

## `approval`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `token_source` | string | yes | `approver_supplied` | Must remain `approver_supplied`. |
| `bind_to_fingerprint` | boolean | yes | `true` | Must remain true. Any input, rule or result change invalidates confirmation. |
| `expiry_hours` | integer | no | `24` | Confirmation lifetime. |
| `require_explicit_review_acceptance` | boolean | yes | `true` | `REVIEW` requires separate explicit acceptance. |
| `agent_may_confirm` | boolean | yes | `false` | Must remain false. |

## `delivery`

| Field | Type | Required | Environment override | Description |
| --- | --- | --- | --- | --- |
| `adapter` | string | yes | `CALC_DELIVERY__ADAPTER` | Registered `DeliveryAdapter` identifier. |
| `channel` | string | no | `CALC_DELIVERY__CHANNEL` | Abstract channel type, not a product name. |
| `dry_run` | boolean | yes | `CALC_DELIVERY__DRY_RUN` | Must default to `true`. Real delivery requires explicit opt-out. |
| `allowlist[].entity_id` | string | yes | - | Canonical entity identifier. |
| `allowlist[].recipient_id` | string | yes | - | Delivery identifier; must be valid for one-to-one delivery. |
| `allowlist[].enabled` | boolean | yes | - | Only enabled entries are eligible. Start with `false`. |
| `one_message_per_recipient` | boolean | yes | - | Must remain `true`. |
| `group_fallback` | boolean | yes | `false` | Must remain false. |
| `idempotency_key_template` | string | yes | - | Must contain `{period}`, `{entity_id}` and `{fingerprint}`. |

## `output` and `style`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `output.root` | string | yes | Relative output root. Every artifact is written here; no input file is ever modified. |
| `output.artifacts` | array | no | Allowlisted artifact names. |
| `style.template` | string | no | Optional layout template for the unified result table. |

## Validation rules

1. `require_human_confirmation`, `independent_recompute`, `bind_to_fingerprint`, `one_message_per_recipient` must be `true`; `allow_arbitrary_expressions`, `group_fallback`, `agent_may_confirm` must be `false`.
2. `period.scheduled_run_stops_at` must be `preview`.
3. `delivery.dry_run` must be `true` unless an explicit runtime flag disables it.
4. `idempotency_key_template` must contain all three placeholders.
5. Every `location`, `endpoint`, `entity_id` and `recipient_id` must be a non-placeholder value at runtime.
6. `state/`, `out/`, local config and any runtime artifacts must be gitignored. A pre-publish privacy check must find no real names, identifiers or amounts in committed files.

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
