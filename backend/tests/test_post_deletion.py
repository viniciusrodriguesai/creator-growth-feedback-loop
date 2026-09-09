import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.youtube import YouTubeVideoData
from app.main import create_app
from app.models import Post, YouTubeImport
from app.posts import delete_post

VIDEO_ID = "dQw4w9WgXcQ"


def video_data(video_id: str) -> YouTubeVideoData:
    return YouTubeVideoData(
        video_id=video_id,
        platform="youtube",
        title="Imported video",
        creator="Creator Channel",
        views=12_000,
        likes=850,
        comments=42,
        shares=None,
        duration_seconds=73,
        published_at=datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def deletion_client(tmp_path: Path) -> Iterator[TestClient]:
    database_url = f"sqlite:///{(tmp_path / 'deletion.db').as_posix()}"
    application = create_app(
        database_url,
        youtube_video_fetcher=video_data,
    )
    with TestClient(application) as client:
        yield client


def manual_post_payload() -> dict[str, object]:
    return {
        "platform": "instagram",
        "title": "Manual post",
        "hook_type": "pain_point",
        "format": "short",
        "creator": "Demo Creator",
        "views": 100,
        "likes": 10,
        "comments": 2,
        "shares": 1,
        "duration_seconds": 30,
        "published_at": "2026-09-05T12:30:00Z",
    }


def import_payload() -> dict[str, str]:
    return {
        "url": f"https://www.youtube.com/watch?v={VIDEO_ID}",
        "hook_type": "question",
        "format": "long",
    }


def test_delete_manual_post(deletion_client: TestClient) -> None:
    created = deletion_client.post("/posts", json=manual_post_payload())

    response = deletion_client.delete(f"/posts/{created.json()['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert deletion_client.get("/posts").json() == []


def test_delete_youtube_imported_post(deletion_client: TestClient) -> None:
    imported = deletion_client.post("/imports/youtube", json=import_payload())

    response = deletion_client.delete(f"/posts/{imported.json()['id']}")

    assert response.status_code == 204
    assert deletion_client.get("/posts").json() == []


def test_delete_youtube_post_removes_import_mapping(
    deletion_client: TestClient,
) -> None:
    imported = deletion_client.post("/imports/youtube", json=import_payload())

    deletion_client.delete(f"/posts/{imported.json()['id']}")

    with Session(deletion_client.app.state.database_engine) as session:
        assert session.scalars(select(YouTubeImport)).all() == []

    reimported = deletion_client.post("/imports/youtube", json=import_payload())
    assert reimported.status_code == 201


def test_delete_unknown_post_returns_404(deletion_client: TestClient) -> None:
    response = deletion_client.delete("/posts/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "post_not_found",
            "message": "The requested post was not found.",
        }
    }


def test_failed_post_delete_rolls_back_import_mapping(
    deletion_client: TestClient,
) -> None:
    imported = deletion_client.post("/imports/youtube", json=import_payload())
    post_id = imported.json()["id"]
    engine: Engine = deletion_client.app.state.database_engine

    def reject_post_delete(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if statement.startswith("DELETE FROM posts"):
            raise IntegrityError(
                statement,
                parameters,
                sqlite3.IntegrityError("simulated post deletion failure"),
            )

    event.listen(engine, "before_cursor_execute", reject_post_delete)
    try:
        with Session(engine) as session:
            with pytest.raises(IntegrityError):
                delete_post(session, post_id)

        with Session(engine) as session:
            assert session.get(Post, post_id) is not None
            mapping = session.get(YouTubeImport, VIDEO_ID)
            assert mapping is not None
            assert mapping.post_id == post_id
    finally:
        event.remove(engine, "before_cursor_execute", reject_post_delete)
