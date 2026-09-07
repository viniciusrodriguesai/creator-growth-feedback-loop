import os
from collections.abc import Generator
from collections.abc import Mapping
from pathlib import Path

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "creator_growth.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


def database_url_from_environment(
    environment: Mapping[str, str] | None = None,
) -> str:
    source_environment = os.environ if environment is None else environment
    database_url = source_environment.get("DATABASE_URL", "").strip()
    if not database_url:
        return DEFAULT_DATABASE_URL

    if database_url.startswith("postgres://"):
        return f"postgresql+psycopg://{database_url.removeprefix('postgres://')}"
    if database_url.startswith("postgresql://"):
        return (
            "postgresql+psycopg://"
            f"{database_url.removeprefix('postgresql://')}"
        )
    return database_url


def create_database_engine(database_url: str = DEFAULT_DATABASE_URL) -> Engine:
    connect_args = (
        {"check_same_thread": False}
        if make_url(database_url).get_backend_name() == "sqlite"
        else {}
    )
    return create_engine(database_url, connect_args=connect_args)


def get_session(request: Request) -> Generator[Session, None, None]:
    with Session(request.app.state.database_engine) as session:
        yield session
