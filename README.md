# Creator Growth Feedback Loop

This repository currently contains the Phase 0 backend foundation and a health endpoint.

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

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

## Current endpoint

`GET /health` returns HTTP `200` with:

```json
{"status": "ok"}
```
