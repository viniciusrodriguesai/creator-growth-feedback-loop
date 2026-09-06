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
`duration_seconds` may be omitted or set to `null`. All numeric values must be
non-negative, and `published_at` must include a timezone.

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
