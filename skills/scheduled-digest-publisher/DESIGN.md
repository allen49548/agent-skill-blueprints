# Design: Scheduled Digest Publisher

## Architecture

```
  [Clock] ---> period resolver ---> business period
                                        |
   +------------------ sources ---------+---------------+
   |  SourceAdapter A   SourceAdapter B   ScheduleAdapter|
   +------------------+-----------------+--------------+
                      |  material.json + draft.md
                      v
              [Verifier] cross-checks
                      |
              [Selector] window / dedupe / rank / categorize
                      |
              [FocusResolver] focus entity + next occurrence
                      |
              [TemplateRenderer] ---> final.md
                      |
              [ChannelAdapter] ---> allowlisted channels
                      |
              run.log + send.log
```

Every box is an interface. No box knows a vendor product, a source brand or a channel identifier beyond what config supplies.

## Business period and collection window

The display period is defined in `display_timezone`. Source systems may use a different timezone. A single source day is therefore not the same set of instants as a single display day.

Required behavior:

- Convert the display period boundaries into UTC.
- Query each source across a range that starts at least one source day before and ends at least one source day after those boundaries.
- Filter collected items by converting their timestamps into `display_timezone` and keeping only those inside the display period.
- Never rely on a source-side date parameter to mean a display-side date.

The lookback window (`business_period.window_hours`) is independent of the query range. The query range guarantees correctness at boundaries; the lookback window controls editorial freshness.

## Data contracts

### `material.json`

```json
{
  "period": "<PERIOD_ID>",
  "generated_at": "<UTC_TIMESTAMP>",
  "items": [
    {
      "id": "<STABLE_ITEM_ID>",
      "source_id": "<SOURCE_ID>",
      "title": "<TITLE>",
      "url": "<TRACEABLE_URL>",
      "published_at": "<UTC_TIMESTAMP>",
      "category": "<CATEGORY>",
      "facts": []
    }
  ],
  "focus": {
    "entity_id": "<FOCUS_ENTITY_ID>",
    "occurrence": null,
    "next_occurrence": null,
    "metadata": {}
  },
  "errors": [
    { "source_id": "<SOURCE_ID>", "reason": "<REASON>" }
  ]
}
```

### `final.md`

Rendered text only. It must not contain absolute local paths, config paths, internal identifiers, raw API responses or debug fields. Every factual claim maps back to either a verified item or a `focus` field.

### `run.log`

One append-only line or block per run: period, item count, per-source counts, focus status, verification conflicts, degradations and final delivery outcome.

### `send.log`

One append-only record per channel: channel identifier, idempotency key, render mode used, receipt or failure reason.

## State machine

```
IDLE -> COLLECTING -> VERIFYING -> SELECTING -> RENDERING -> DELIVERING -> DONE
                         |              |            |             |
                         +--------------+------------+-------------+--> DEGRADED
                                                                   |
                                                              DELIVERY_FAILED -> DONE
```

- `DEGRADED` is not a failure state; it is a flag attached to a completed run.
- `DELIVERY_FAILED` still reaches `DONE` with an explicit "not delivered" outcome. The run is never retried in a loop.
- A rerun of the same period re-enters at `COLLECTING` but must exit before `DELIVERING` if the idempotency key already has a success record.

## Idempotency

Key template: `digest:{period}:{channel_id}:{key_suffix}`.

- `key_suffix` is empty for scheduled runs and non-empty for manual tests.
- A successful delivery is recorded before the run is considered complete.
- A repeated run with an existing success record skips delivery and logs "already delivered".
- Rich-to-plain fallback must not change the key; otherwise the fallback would be treated as a new message.

## Focus entity

`focus.entity_id` resolves against the structured artifact's `focus` object. The section is built from three cases:

| Case | Content |
| --- | --- |
| Occurrence in period | Marker heading, normalized time, counterpart, status, verified context |
| No occurrence, next occurrence known | Marker heading, explicit "no occurrence" statement, next occurrence time and counterpart |
| No occurrence, no next occurrence known | Marker heading, explicit "no occurrence" statement, and "next occurrence unavailable" |

Never render a default numeric value as if it were a real score or status. Never reuse a value belonging to a different entity.

## Verification policy

- At least `verification.min_cross_checks` independent checks for claims involving numbers, named parties, statuses or times.
- Conflicts are resolved in favor of traceable authoritative results; record the difference in `run.log`.
- Unverifiable claims are omitted, not softened.
- Source links are mandatory when `verification.require_source_links` is true.
- The denylist is only changed after a live freshness validation.

## Failure matrix

| Stage | Failure | Detection | Behavior | Logged as |
| --- | --- | --- | --- | --- |
| Collect | Source timeout or error | Adapter exception / `errors` entry | Continue with other sources | `source_failed` |
| Collect | All sources fail | Empty `items` with errors | Deliver structural sections with an explicit note | `all_sources_failed` |
| Collect | Schedule source fails | Missing `focus` data | Omit event details, keep the focus section | `schedule_unavailable` |
| Verify | Conflict | Cross-check disagreement | Prefer traceable source; record difference | `verification_conflict` |
| Select | Too few items | Count below minimum | Deliver with a reduced set and state the shortfall | `underfilled` |
| Render | Rich template fails | Renderer exception | Fall back to plain text | `render_fallback` |
| Deliver | Channel rejects | Non-success receipt | Record reason; no loop retry | `delivery_failed` |
| Deliver | Idempotency hit | Existing success record | Skip send | `already_delivered` |

## Extension points

| Interface | Responsibility | Must not do |
| --- | --- | --- |
| `Clock` | Supply current time | Estimate dates or weekdays |
| `SourceAdapter` | Fetch items in a UTC range | Assume its date parameter equals the display date |
| `ScheduleAdapter` | Fetch occurrences and next occurrence | Invent missing fields |
| `Verifier` | Cross-check claims | Backfill gaps from general knowledge |
| `Selector` | Filter, deduplicate, rank, categorize | Exceed configured item bounds |
| `FocusResolver` | Build the always-present section | Omit the section when data is missing |
| `TemplateRenderer` | Produce the final message | Include machine-local paths or raw responses |
| `ChannelAdapter` | Deliver with an idempotency key | Send outside the allowlist |

## Testing checklist

- [ ] A run repeated with the same period and channel produces exactly one message.
- [ ] A manual test with a distinct key suffix does not suppress the scheduled run.
- [ ] An occurrence near a timezone boundary lands in the correct display period.
- [ ] With one source failing, the remaining sources still produce a message and the failure is logged.
- [ ] With all sources failing, no stale or invented content appears.
- [ ] With no focus occurrence, the section is still present and states the next occurrence.
- [ ] The final message contains no local paths, internal identifiers or unverified numbers.
- [ ] A delivery failure is reported explicitly rather than silently.
- [ ] No file is written outside `output.root/<period>/`.
