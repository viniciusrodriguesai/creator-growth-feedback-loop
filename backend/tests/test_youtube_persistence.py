import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, event, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import create_database_engine
from app.integrations.youtube import YouTubeVideoData
from app.models import Base, Post, YouTubeImport
from app.youtube_imports import (
    YouTubeVideoAlreadyImportedError,
    is_youtube_video_imported,
    persist_youtube_import,
)

VIDEO_ID = "dQw4w9WgXcQ"
OTHER_VIDEO_ID = "abcdefghijk"


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    database_path = tmp_path / "youtube-imports.db"
    database_engine = create_database_engine(
        f"sqlite:///{database_path.as_posix()}"
    )
    Base.metadata.create_all(database_engine)
    yield database_engine
    database_engine.dispose()


def video_data(
    video_id: str = VIDEO_ID,
    *,
    published_at: datetime | None = None,
) -> YouTubeVideoData:
    return YouTubeVideoData(
        video_id=video_id,
        platform="youtube",
        title="A public video",
        creator="Creator Channel",
        views=12_000,
        likes=850,
        comments=42,
        shares=None,
        duration_seconds=73,
        published_at=published_at
        or datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc),
    )


def test_youtube_import_table_has_required_identity_constraints(
    engine: Engine,
) -> None:
    inspector = inspect(engine)
    primary_key = inspector.get_pk_constraint("youtube_imports")
    unique_constraints = inspector.get_unique_constraints("youtube_imports")
    foreign_keys = inspector.get_foreign_keys("youtube_imports")
    columns = {
        column["name"]: column
        for column in inspector.get_columns("youtube_imports")
    }

    assert primary_key["constrained_columns"] == ["video_id"]
    assert columns["video_id"]["type"].length == 11
    assert any(
        constraint["column_names"] == ["post_id"]
        for constraint in unique_constraints
    )
    assert any(
        foreign_key["constrained_columns"] == ["post_id"]
        and foreign_key["referred_table"] == "posts"
        and foreign_key["referred_columns"] == ["id"]
        for foreign_key in foreign_keys
    )
    assert columns["post_id"]["nullable"] is False


def test_persist_youtube_import_maps_post_and_identity_atomically(
    engine: Engine,
) -> None:
    source_timezone = timezone(timedelta(hours=-3))
    published_at = datetime(2026, 8, 20, 11, 30, tzinfo=source_timezone)

    with Session(engine) as session:
        post = persist_youtube_import(
            session,
            video_data(published_at=published_at),
            hook_type="pain_point",
            format="short",
        )
        post_id = post.id

    with Session(engine) as session:
        stored_post = session.get(Post, post_id)
        identity = session.get(YouTubeImport, VIDEO_ID)

        assert stored_post is not None
        assert stored_post.platform == "youtube"
        assert stored_post.title == "A public video"
        assert stored_post.creator == "Creator Channel"
        assert stored_post.views == 12_000
        assert stored_post.likes == 850
        assert stored_post.comments == 42
        assert stored_post.shares is None
        assert stored_post.duration_seconds == 73
        assert stored_post.published_at == datetime(
            2026,
            8,
            20,
            14,
            30,
            tzinfo=timezone.utc,
        )
        assert stored_post.hook_type == "pain_point"
        assert stored_post.format == "short"
        assert identity is not None
        assert identity.post_id == post_id


def test_youtube_import_pre_check_reports_existing_video(engine: Engine) -> None:
    with Session(engine) as session:
        assert not is_youtube_video_imported(session, VIDEO_ID)
        persist_youtube_import(
            session,
            video_data(),
            hook_type="question",
            format="long",
        )
        assert is_youtube_video_imported(session, VIDEO_ID)


def test_duplicate_video_id_is_rejected_without_orphan_post(
    engine: Engine,
) -> None:
    with Session(engine) as session:
        first_post = persist_youtube_import(
            session,
            video_data(),
            hook_type="question",
            format="long",
        )

        with pytest.raises(YouTubeVideoAlreadyImportedError) as error:
            persist_youtube_import(
                session,
                video_data(),
                hook_type="story",
                format="short",
            )

        posts = session.scalars(select(Post)).all()
        identities = session.scalars(select(YouTubeImport)).all()

    assert error.value.code == "youtube_video_already_imported"
    assert str(error.value) == "This YouTube video has already been imported."
    assert [post.id for post in posts] == [first_post.id]
    assert len(identities) == 1


def test_different_video_ids_can_be_imported(engine: Engine) -> None:
    with Session(engine) as session:
        first_post = persist_youtube_import(
            session,
            video_data(),
            hook_type="question",
            format="long",
        )
        second_post = persist_youtube_import(
            session,
            video_data(OTHER_VIDEO_ID),
            hook_type="story",
            format="short",
        )

        assert first_post.id != second_post.id
        assert session.scalar(select(func.count()).select_from(Post)) == 2


def test_database_uniqueness_is_authoritative_when_pre_check_is_bypassed(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with Session(engine) as session:
        first_post = persist_youtube_import(
            session,
            video_data(),
            hook_type="question",
            format="long",
        )

        monkeypatch.setattr(
            "app.youtube_imports.is_youtube_video_imported",
            lambda session, video_id: False,
        )

        with pytest.raises(YouTubeVideoAlreadyImportedError) as error:
            persist_youtube_import(
                session,
                video_data(),
                hook_type="story",
                format="short",
            )

        posts = session.scalars(select(Post).order_by(Post.id)).all()

    assert error.value.code == "youtube_video_already_imported"
    assert str(error.value) == "This YouTube video has already been imported."
    assert [post.id for post in posts] == [first_post.id]


def test_failed_identity_insert_rolls_back_post(engine: Engine) -> None:
    def reject_identity_insert(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if statement.startswith("INSERT INTO youtube_imports"):
            raise IntegrityError(
                statement,
                parameters,
                sqlite3.IntegrityError("simulated identity failure"),
            )

    event.listen(engine, "before_cursor_execute", reject_identity_insert)
    try:
        with Session(engine) as session:
            with pytest.raises(IntegrityError):
                persist_youtube_import(
                    session,
                    video_data(),
                    hook_type="question",
                    format="long",
                )

            assert session.scalars(select(Post)).all() == []
            assert session.scalars(select(YouTubeImport)).all() == []
    finally:
        event.remove(engine, "before_cursor_execute", reject_identity_insert)


def test_youtube_import_reuses_post_validation(engine: Engine) -> None:
    invalid_video = video_data()
    object.__setattr__(invalid_video, "views", -1)

    with Session(engine) as session:
        with pytest.raises(ValidationError):
            persist_youtube_import(
                session,
                invalid_video,
                hook_type="question",
                format="long",
            )

        assert session.scalars(select(Post)).all() == []
