from collections.abc import Generator
from pathlib import Path

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "creator_growth.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


def create_database_engine(database_url: str = DEFAULT_DATABASE_URL) -> Engine:
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )


def get_session(request: Request) -> Generator[Session, None, None]:
    with Session(request.app.state.database_engine) as session:
        yield session
