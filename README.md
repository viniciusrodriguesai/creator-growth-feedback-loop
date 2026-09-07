# Creator Growth Feedback Loop

Creator Growth Feedback Loop is a local content-intelligence dashboard. It
stores published-content performance, compares patterns across user-classified
hooks and formats, and proposes an explainable next experiment from the current
dataset.

## Architecture

- A React and TypeScript frontend built with Vite.
- A FastAPI backend that exposes posts, analytics, recommendations, and YouTube
  import endpoints.
- A local SQLite database for posts and imported YouTube identities.
- The YouTube Data API v3 for public video metadata and metrics.

During development, the frontend calls relative `/api` paths. Vite removes that
prefix and proxies requests to FastAPI at `http://127.0.0.1:8000`.

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

## Backend setup

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

The safe [`.env.example`](.env.example) documents the variable name. `.env`
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

## Frontend setup

In a second terminal:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:5173` while the backend is running.

## API overview

- `GET /health` checks backend availability.
- `POST /posts` stores a manually entered content record.
- `GET /posts` lists persisted posts in ascending ID order.
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
- This project is not affiliated with or endorsed by YouTube.
- This project is not affiliated with Osynth and makes no claim of access to
  Osynth systems, source code, data, or internal processes.
