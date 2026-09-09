# Creator Growth Feedback Loop

Creator Growth Feedback Loop turns scattered content-performance data into one
explainable next experiment. A creator can import a public YouTube video or add
a performance record, compare observed hook and format patterns, and decide
what to test next without treating correlation as causation.

- **Live Demo:** _URL coming soon_
- **Short demo video:** _URL coming soon_

## Product workflow

1. Import public YouTube metadata and metrics, or record a post manually.
2. Classify the hook type and format so comparable creative patterns emerge.
3. Review view-weighted engagement across hooks, formats, and creators.
4. Use the evidence-backed Next Experiment card to choose a controlled test.

**Core stack:** React, TypeScript, Vite, FastAPI, SQLAlchemy, SQLite for local
development, PostgreSQL for hosted persistence, and YouTube Data API v3.

## Architecture

- A React and TypeScript frontend built with Vite.
- A FastAPI backend that exposes posts, analytics, recommendations, and YouTube
  import endpoints.
- SQLAlchemy with local SQLite by default and PostgreSQL for hosted persistence.
- The YouTube Data API v3 for public video metadata and metrics.

During development, the frontend calls relative `/api` paths. Vite removes that
prefix and proxies requests to FastAPI at `http://127.0.0.1:8000`. A production
build uses `VITE_API_BASE_URL` to call the separately hosted API. The backend
allows only the exact origins configured in `FRONTEND_ORIGINS`.

The recommended demo deployment uses a Render Static Site for the frontend, a
Render Web Service for the API, and Neon PostgreSQL for persistent data. The
repository-level [`render.yaml`](render.yaml) defines both Render services.

## YouTube import workflow

In the dashboard, paste a public YouTube video URL, select its hook type and
format, and choose **Import video**. The backend then:

1. extracts and validates the YouTube video ID;
2. rejects a video ID that was already imported;
3. retrieves its public title, channel, publication time, duration, views,
   likes, and comments;
4. stores the post and YouTube identity in one transaction; and
5. returns the imported post.

After success, the frontend refreshes posts, summary analytics, performance
breakdowns, and the Next Experiment recommendation without reloading the page.
The URL field is cleared, while the selected hook type and format remain ready
for another import.

Supported HTTPS URL forms include:

```text
https://www.youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://www.youtube.com/shorts/VIDEO_ID
https://www.youtube.com/embed/VIDEO_ID
https://www.youtube.com/live/VIDEO_ID
```

The standard `youtube.com`, `www.youtube.com`, and `m.youtube.com` hosts are
supported where applicable. Playlist, channel, non-HTTPS, credential-bearing,
custom-port, and non-YouTube URLs are rejected.

## Requirements

- Python 3.11 or later
- Node.js and npm
- A YouTube Data API v3 key only when using real YouTube import

## Local development

### Backend

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[test]"
```

Set the API key in the shell that will start the backend. Do not commit or paste
the real value into project files:

```powershell
$env:YOUTUBE_API_KEY = "your-local-api-key"
```

The safe [`.env.example`](.env.example) documents configuration names. `.env`
and other environment files are ignored by Git, but the application reads the
process environment directly and does not automatically load `.env` files.

Start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend
```

The API is available at `http://127.0.0.1:8000`. The local database is stored
at `backend/creator_growth.db` and is ignored by Git.

Without `YOUTUBE_API_KEY`, the rest of the product remains usable and YouTube
imports return a safe configuration error.

### Frontend

In a second terminal:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:5173` while the backend is running.

Local development needs no CORS or API-base configuration because the Vite
proxy keeps browser requests same-origin. The demo write limit is also disabled
when `DEMO_WRITE_RATE_LIMIT` is unset.

## Deployment

### Recommended architecture

- **Frontend:** Render Static Site, built from `web/` and served over managed
  HTTPS.
- **Backend:** one Render Python Web Service, started with
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Render checks `/ready`,
  which verifies database connectivity; `/health` remains a lightweight
  liveness endpoint.
- **Database:** Neon PostgreSQL, using its persistent pooled connection string.

This keeps the React build on a CDN, keeps every credential on the backend, and
avoids storing SQLite on Render's ephemeral free-service filesystem. Render's
free web service can sleep when idle, so warm `/health` shortly before a live
demo. A paid Render service with a persistent disk could keep SQLite, but the
PostgreSQL option is more durable for a no-cost portfolio demo.

### Environment variables

| Variable | Service | Secret | Purpose |
| --- | --- | --- | --- |
| `APP_ENV` | Backend | No | Set to `production` on Render; the Blueprint supplies this value. |
| `DATABASE_URL` | Backend | Yes | Neon pooled PostgreSQL connection string. Local default remains SQLite when unset. |
| `FRONTEND_ORIGINS` | Backend | No | Comma-separated exact frontend origins, such as `https://creator-growth-feedback-loop.onrender.com`. Wildcards are rejected. |
| `YOUTUBE_API_KEY` | Backend | Yes | YouTube Data API v3 key used only by the server. |
| `DEMO_WRITE_RATE_LIMIT` | Backend | No | Maximum shared demo writes per process and window. Render sets `10`. |
| `DEMO_WRITE_RATE_WINDOW_SECONDS` | Backend | No | Demo limit window in seconds. Render sets `3600`. |
| `VITE_API_BASE_URL` | Frontend build | No | Public HTTPS origin of the backend, without an endpoint path. |

`PORT` is supplied by Render and is not a manual setting. Vite exposes every
`VITE_*` value to browser code, so no API key, database URL, or server credential
may use that prefix. `YOUTUBE_API_KEY` is read only by the Python integration.
When `APP_ENV=production`, startup fails safely unless `DATABASE_URL`,
`FRONTEND_ORIGINS`, and `YOUTUBE_API_KEY` are all configured. In development,
these values remain optional and the local SQLite fallback is unchanged.

### Manual deployment steps

1. Create a Neon project and copy its pooled PostgreSQL connection string.
2. In Render, choose **New > Blueprint**, connect this repository, select
   `main`, and use the root `render.yaml`.
3. Set the backend's `DATABASE_URL` to the Neon connection string and set
   `YOUTUBE_API_KEY` as a secret.
4. Set the backend's `FRONTEND_ORIGINS` to the exact HTTPS URL Render assigns to
   the static site. Do not add a trailing path and do not use `*`.
5. Set the static site's `VITE_API_BASE_URL` to the exact HTTPS URL Render
   assigns to the API service. If either generated hostname differs from the
   planned service name, update both variables and redeploy the affected
   service.
6. In Google Cloud, restrict the key to YouTube Data API v3 and configure quota
   monitoring or alerts. Never put the key in Render's frontend variables.
7. Verify the API `/health` and `/ready`, load the static-site URL, and perform
   one controlled import before sharing the demo.

No account or paid resource is created by this repository configuration.

### Demo write protection

When configured, one in-memory limiter is shared by `POST /posts`,
`POST /imports/youtube`, and `DELETE /posts/{post_id}`. Read-only health, list,
analytics, and recommendation requests are not limited. Render enables 10
writes per 3,600-second window and the API returns `429` with `Retry-After` when
the allowance is exhausted.

This is lightweight demo abuse mitigation only. It resets when the process
restarts, is per-process, is not distributed, is not authentication, and is not
production-grade protection against sophisticated or distributed abuse. A real
multi-user product requires authentication, authorization, and a stronger
shared rate limiter. Keep the demo URL controlled and monitor the YouTube quota.

## API overview

- `GET /health` checks process liveness without querying the database.
- `GET /ready` checks database connectivity and returns `503` with a generic
  response when the database is unavailable.
- `POST /posts` stores a manually entered content record.
- `GET /posts` lists persisted posts in ascending ID order.
- `DELETE /posts/{post_id}` removes a post and its YouTube import mapping, when
  present; it returns `204` on success and `404` for an unknown post.
- `POST /imports/youtube` imports public YouTube metadata and metrics.
- `GET /analytics` returns the overall summary and groups by `hook_type`,
  `format`, and `creator`.
- `GET /recommendations` returns either an explainable next experiment or an
  insufficient-data result.

The primary engagement metric is:

```text
known_core_engagements = likes + comments
engagement_rate = sum(known_core_engagements) / sum(views)
```

Only posts with views greater than zero participate in rates. Recommendations
compare eligible hook-type and format groups against the remaining eligible
posts. A candidate needs at least two eligible posts; otherwise the endpoint
returns `insufficient_data`.

## Testing

Backend tests never use a real YouTube request; transports and video metadata
are controlled in the test suite.

GitHub Actions runs the full backend tests plus `pip check`, and the full
frontend tests plus production build, on every push and pull request to `main`.

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
.\.venv\Scripts\python.exe -m pip check
```

Run frontend tests and the production build from `web`:

```powershell
npm test
npm run build
```

The build command runs TypeScript project compilation before Vite creates the
production bundle. There is currently no lint script.

## Limitations

- Analytics are observational; they identify associations, not causes.
- Recommendations use explicit product heuristics and are not statistical
  proof.
- Shares are unavailable through this YouTube integration and are stored as
  unknown rather than zero.
- Hook type and format are classified by the user, not inferred from the video.
- Only public metadata and metrics exposed by the YouTube Data API are used.
- Private, unavailable, restricted, or incomplete videos may not be importable.
- API quota, credentials, network availability, and upstream responses can
  temporarily prevent imports.
- Public demo writes are intentionally unauthenticated; the in-memory limit is
  only a lightweight guard for a controlled demonstration.
- This project is not affiliated with or endorsed by YouTube.
- This project is not affiliated with Osynth and makes no claim of access to
  Osynth systems, source code, data, or internal processes.
