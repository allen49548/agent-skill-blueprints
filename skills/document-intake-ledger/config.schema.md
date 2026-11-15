# Configuration Schema: Document Intake Ledger

Copy `config.example.json` to a local `config.json` (gitignored) or override individual fields with environment variables. Environment variables use the `INTAKE_` prefix; nested fields use double underscores, for example `INTAKE_SAFETY__WRITE_ENABLED`.

Placeholders in `<ANGLE_BRACKETS>` must be replaced before use. Startup must reject any config value that still contains placeholder markers.

## `period` and `channels`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `period.derivation` | string | yes | Must be `system_clock`. |
| `period.schedule_cron` | string | no | Regular run trigger. |
| `period.monthly_report_cron` | string | no | Separate aggregation run trigger. |
| `channels.reader_adapter` | string | yes | Registered `ChannelReader`. |
| `channels.primary[].channel_id` | string | yes | Exact-match identifier for reading and channel-tier sending. |
| `channels.retired[]` | array | no | Channels that are neither read nor notified; their historical ledger entries remain in scope. |
| `channels.lookback_periods` | integer | no | Window covering late resubmissions. |
| `channels.send_identity` | string | no | Sending identity. Read and send permissions are separate. |

Never match a send target by channel name. An exact identifier match with `notify=true` is required.

## `document_classes` and `attribution`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `document_classes.accepted` | array | yes | Classes whose values may be extracted and registered. |
| `document_classes.unsupported` | array | yes | Classes that produce a resubmission request and no value extraction. |
| `document_classes.ignored` | array | no | Classes skipped without an anomaly. |
| `document_classes.confidence_threshold` | number | no | Below this value, route to manual review. |
| `attribution.entity_map` | object | yes | Sender identifier to entity mapping. |
| `attribution.elastic` | boolean | no | Only submitting entities appear in reports; no zero-value padding. |
| `attribution.conflict_action` | string | yes | Must be `manual_review`. Never guess an owner. |
| `attribution.allow_default_entity` | - | - | Not supported by design. An unresolved sender is never defaulted. |

## `dedup`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `layers` | array | yes | four layers | Order: message id, content hash, perceptual hash, business key. |
| `business_key_fields` | array | yes | - | Preferred business key. Equal values are never the criterion. |
| `fallback_business_key_fields` | array | yes | - | Used when no document business identifier exists. |
| `equal_value_is_duplicate` | boolean | yes | `false` | Must remain false. |
| `perceptual_hit_with_different_key` | string | yes | `false_positive` | Must remain `false_positive`; otherwise distinct items are dropped. |
| `include_entity_in_composite_key` | boolean | yes | `true` | Two entities with identical values remain distinct. |
| `report_original_registration` | boolean | yes | `true` | A duplicate must report original time and current status. |
| `retain_original_message_id` | boolean | yes | `true` | Entries are marked, never physically deleted. |

## `workbooks` and `ledger`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `workbooks.root` | string | yes | Directory of existing workbooks. |
| `workbooks.file_pattern` | string | yes | Resolves an entity and period to an existing file. |
| `workbooks.detail_sheet` | string | yes | Canonical sheet. Exactly one per workbook. |
| `workbooks.create_sheet_in_existing_workbook` | boolean | yes | The only authorized structural change. |
| `workbooks.create_workbook_if_missing` | boolean | yes | Must remain `false`. |
| `workbooks.append_only` | boolean | yes | Must remain `true`. |
| `ledger.path` | string | yes | Local durable store. Gitignored. |
| `ledger.outstanding_states` | array | yes | Must be `["registered"]` only. |
| `ledger.physical_delete` | boolean | yes | Must remain `false`. |

## `tasks`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `adapter` | string | yes | Registered `TaskAdapter`. |
| `batching` | string | yes | `entity_per_run` produces one task per entity per run. |
| `editor_role` | string | yes | May edit and complete the task. |
| `viewer_role` | string | yes | May view and comment only. |
| `poll_completion` | boolean | no | Marks entries `confirmed` on completion. |
| `missing_viewer_action` | string | yes | Must be `skip_silently_and_log`; never an anomaly or follow-up task. |

## `notifications` and `aggregation`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `notifications.delivery_enabled` | boolean | yes | Start with `false` during onboarding. |
| `notifications.per_entity_private_delivery` | boolean | yes | Must remain `false` unless explicitly reconfigured. |
| `notifications.hard_block_private_delivery_flag` | boolean | yes | Must remain `true`; blocks an accidental legacy flag. |
| `notifications.send_on_no_change` | boolean | yes | Must remain `true`. |
| `notifications.idempotency_key_template` | string | yes | Must contain `{period}`, `{run_id}`, `{tier}` and `{channel_id}`. |
| `aggregation.group_by` | string | yes | Must be `entity`, never channel. |
| `aggregation.include_channel_allowlist` | boolean | yes | Must remain `false`; retired-channel history still counts. |
| `aggregation.active_entities_only` | boolean | yes | No zero-value padding. |
| `aggregation.comparison_visibility` | string | yes | Must be `operator_detail_only`. |
| `aggregation.period_send_guard` | boolean | yes | Prevents sending a period report twice. |

## `policy_hooks`, `output` and `safety`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `policy_hooks[].enabled` | boolean | yes | Disabled by default. Tone and wording never carry operational fields. |
| `output.root` | string | yes | All logs, backups and state are written here. |
| `safety.write_enabled` | boolean | yes | Start with `false`. |
| `safety.backup_required` | boolean | yes | Must remain `true`. |
| `safety.verify_untouched_parts` | boolean | yes | Must remain `true`. |
| `safety.rollback_on_verify_failure` | boolean | yes | Must remain `true`. |
| `safety.register_only_after_verified_write` | boolean | yes | Must remain `true`. |

## Validation rules

1. `equal_value_is_duplicate`, `create_workbook_if_missing`, `include_channel_allowlist`, `per_entity_private_delivery`, `physical_delete` must be `false`.
2. `append_only`, `report_original_registration`, `retain_original_message_id`, `hard_block_private_delivery_flag`, `send_on_no_change`, `register_only_after_verified_write` must be `true`.
3. `ledger.outstanding_states` must contain exactly one state, `registered`.
4. `notifications.idempotency_key_template` must contain all four placeholders.
5. All channel identifiers, workbook roots and sender identifiers must be non-placeholder at runtime.
6. Ledger databases, run logs, backups, downloaded images and local config must be gitignored. A pre-publish privacy check must find no real names, identifiers, values or paths in committed files.

## Adapter registry (`adapters`)

`adapters` declares **how** input is obtained and **how** output is delivered. The existing top-level groups (`channels`, `document_classes`, `workbooks`, `tasks`, `notifications`, `safety`, `output`, ...) remain the single source of truth for **parameters**. Any field ending in `_ref` is a pointer into one of those groups; it must never duplicate the referenced value.

`resolution: "declarative"` means this section is a contract. The built-in default adapters keep running, and the config records exactly which defaults those are. Changing a `type` to an entry in `alternatives` requires implementing the matching interface and a dispatcher; until then such a change is a startup error. See `DESIGN.md`.

This contract is shared with a concrete implementation. Both sides use the same eight-dimension skeleton (`input.source`, `input.client`, `input.documents`, `input.window`, `output.write`, `output.notifications`, `output.tasks`, `output.rendering`) and the same naming rules: `type` selects a mechanism, `*_ref` points at a parameter group, and `alternatives` lists candidates. Values differ (placeholders and abstract channel names here, real defaults there), and either side may add implementation-detail fields as long as the skeleton is unchanged and no referenced parameter is duplicated. A `*_ref` points at a config path only; a script or client identifier belongs in a plain `adapter` field.

### `adapters.input`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `source.type` | string | yes | Input family. Default `channel_messages`. |
| `source.adapter_ref` | string | yes | Points to the registered `ChannelReader`. |
| `source.allowlist_ref` / `retired_ref` | string | yes | Points to the read allowlist and retired channels. |
| `source.alternatives` | array | no | Other source families a project may implement. |
| `client.adapter` | string | yes | Client used to read the source. No vendor product name is assumed here. |
| `client.identity` | string | yes | Read identity. Read and send identities are separate. |
| `client.download_attachments` | boolean | no | Whether documents are materialized locally. |
| `client.attachment_dir` | string | no | Relative directory for downloaded material. Must be gitignored. |
| `client.page_all` / `order` | boolean / string | no | Pagination and ordering of reads. |
| `client.identity_fallback` | string | yes | `none` means a failed identity is an error, never a silent downgrade. |
| `documents.*_ref` | string | yes | Points to accepted, unsupported and ignored classes, confidence and manual-review triggers. |
| `documents.extractor` | string | yes | Registered `Extractor`. |
| `documents.supported_shapes` | array | yes | Shapes the extractor claims to handle. |
| `window.strategy` | string | yes | `lookback` or one of `window.alternatives`. |
| `window.lookback_ref` | string | yes | Points to the lookback window. |
| `window.clock` | string | yes | Must be `system_clock`. |
| `window.incremental` | boolean | yes | `false` means each run rescans the full window. |
| `window.full_rescan_each_run` | boolean | yes | Guards against reusing stale cached messages. |
| `window.skip` | array | no | Message kinds ignored without an anomaly. |
| `window.period_field_priority_ref` | string | yes | Points to the period attribution order. |

### `adapters.output`

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `write.type` | string | yes | `workbook_detail_sheet`, or one of `write.alternatives`. |
| `write.adapter` | string | yes | Registered `DetailSheetWriter`. |
| `write.target_ref` / `safety_ref` | string | yes | Points to workbook layout and write-safety settings. |
| `write.idempotency_key` | string | yes | Key that makes appends repeatable. |
| `notifications.adapter_ref` / `channels_ref` | string | yes | Points to the send adapter and the enabled tiers. |
| `notifications.send_on_no_change_ref` | string | yes | Points to the no-change send rule. |
| `notifications.channels[].renderer` | string | yes | Renderer responsible for that tier's text. |
| `notifications.channels[].format` | string | yes | `minimal`, `compact_professional` or a registered format. |
| `notifications.channels[].fields_visible` / `fields_hidden` | array | no | Explicit field-level visibility per tier. |
| `notifications.channels[].hard_blocked` | boolean | no | A blocked tier stays blocked regardless of legacy flags. |
| `tasks.backend_ref` | string | yes | Points to the registered `TaskAdapter`. |
| `tasks.*_ref` | string | yes | Points to batching, editor and viewer roles, and completion polling. |
| `rendering.renderer_registry` | object | yes | Maps a tier to its renderer. |
| `rendering.field_visibility_ref` | string | yes | Single source of truth for field visibility. |
| `rendering.policy_hooks_ref` | string | yes | Points to optional tone hooks. |

### Additional validation rules

7. Every `_ref` must resolve to an existing config path at startup; an unresolved reference is a startup error.
8. A value declared inside `adapters` must not duplicate the value it references.
9. `adapters.resolution` must be `declarative` until a dispatcher exists; a `type` outside the declared `alternatives` is rejected.
10. `window.clock` must be `system_clock` and `client.identity_fallback` must be `none`.
11. Any tier with `hard_blocked: true` must also have `enabled: false`.

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
