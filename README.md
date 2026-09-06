# Creator Growth Feedback Loop

This repository currently contains a FastAPI backend that stores content-performance
posts in a local SQLite database.

## Requirements

- Python 3.11 or later

## Install the backend

Run these commands from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[test]"
```

## Run the backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend
```

The API is available at `http://127.0.0.1:8000`.

The local database is stored at `backend/creator_growth.db` and is ignored by Git.

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

## Current endpoints

### Health

`GET /health` returns HTTP `200` with:

```json
{"status": "ok"}
```

### Create a post

`POST /posts` accepts:

```json
{
  "platform": "youtube",
  "title": "Manual check",
  "hook_type": "question",
  "format": "short",
  "creator": "Creator",
  "views": 0,
  "likes": 1,
  "comments": 2,
  "shares": 3,
  "duration_seconds": 30,
  "published_at": "2026-09-05T12:00:00-03:00"
}
```

The supported platform values are `youtube`, `instagram`, and `tiktok`.
`shares` and `duration_seconds` may be omitted or set to `null`. Numeric values,
when present, must be non-negative, and `published_at` must include a timezone.

A successful request returns HTTP `201` with the stored post. Datetimes are
normalized to UTC:

```json
{
  "platform": "youtube",
  "title": "Manual check",
  "hook_type": "question",
  "format": "short",
  "creator": "Creator",
  "views": 0,
  "likes": 1,
  "comments": 2,
  "shares": 3,
  "duration_seconds": 30,
  "published_at": "2026-09-05T15:00:00Z",
  "id": 1
}
```

### List posts

`GET /posts` returns HTTP `200` with all stored posts ordered by ascending `id`:

```json
[
  {
    "platform": "youtube",
    "title": "Manual check",
    "hook_type": "question",
    "format": "short",
    "creator": "Creator",
    "views": 0,
    "likes": 1,
    "comments": 2,
    "shares": 3,
    "duration_seconds": 30,
    "published_at": "2026-09-05T15:00:00Z",
    "id": 1
  }
]
```

### Analyze posts

`GET /analytics` returns HTTP `200` with an overall summary and results grouped
by `hook_type`, `format`, and `creator`.

The primary metric uses only fields that are consistently available:

```text
known_core_engagements = likes + comments
engagement_rate = sum(known_core_engagements) / sum(views)
```

Only posts with `views > 0` participate in engagement rates. Zero-view posts
remain stored and are reported in `zero_view_posts_excluded_from_rates`.

Shares do not affect `engagement_rate` or `lift_vs_overall`. `known_shares`
contains the sum of available shares from eligible posts and is `null` when no
eligible share value is available. A known share total of zero remains `0`.
The `eligible_posts_with_share_data` and
`eligible_posts_without_share_data` counters show the coverage. Missing shares
are never interpreted as zero.

Each group contains:

- `value`
- `post_count`
- `eligible_post_count`
- `total_views`
- `known_core_engagements`
- `known_shares`
- `eligible_posts_with_share_data`
- `eligible_posts_without_share_data`
- `engagement_rate`
- `lift_vs_overall`

`lift_vs_overall` divides the group engagement rate by the overall engagement
rate. It is `null` when either rate is unavailable or when the overall rate is
zero.

Grouped results are ordered by `value` alphabetically without case sensitivity,
with the original value used as a deterministic tie-breaker. Rates are returned
as normal JSON numbers without application-level rounding. Undefined values are
returned as `null`; the API never returns `NaN` or infinity.

### Get the next experiment

`GET /recommendations` returns HTTP `200` with either
`recommendation_available` or `insufficient_data`.

The engine evaluates `hook_type`, `format`, and `creator` groups using the same
core engagement metric as analytics. Each candidate needs at least two eligible
posts. This threshold is an explicit product heuristic, not a claim of
statistical significance.

For every eligible candidate, the engine compares its aggregated rate with all
other eligible posts in the same dimension:

```text
candidate_rate = candidate_core_engagements / candidate_views
comparison_rate = remaining_core_engagements / remaining_views
contrast_vs_rest = candidate_rate / comparison_rate
rate_difference = candidate_rate - comparison_rate
```

`rate_difference` is the primary ranking measure because it remains defined when
the comparison rate is zero. In that case, `contrast_vs_rest` is `null` rather
than infinity. Candidates are then ordered by larger eligible sample, larger
view count, dimension priority (`hook_type` before `format`), and stable lexical
value.

Only `hook_type` and `format` can become the recommended dimension. Creator
performance is included as supporting evidence but cannot override an actionable
creative attribute. The action changes one dimension and asks that the other be
kept as consistent as possible.

A successful result includes the selected value, candidate and comparison rates,
absolute difference, optional contrast, sample and view totals, evidence,
action, and limitations. The limitations state that the evidence is
observational, excludes shares from the primary metric, and may be confounded
when the selected pattern appears with only one creator or control attribute.

The endpoint returns `insufficient_data` instead of forcing an experiment when
there are no eligible posts, no actionable group reaches the threshold, no valid
comparison population exists, or no actionable candidate outperforms its
comparison population.
