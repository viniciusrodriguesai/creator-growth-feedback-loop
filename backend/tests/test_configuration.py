from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import DEFAULT_DATABASE_URL, database_url_from_environment
from app.main import create_app, frontend_origins_from_environment


def test_database_url_defaults_to_local_sqlite() -> None:
    assert database_url_from_environment({}) == DEFAULT_DATABASE_URL


def test_database_url_uses_psycopg_for_postgres() -> None:
    database_url = "postgresql://user:password@example.com/database?sslmode=require"

    assert database_url_from_environment({"DATABASE_URL": database_url}) == (
        "postgresql+psycopg://user:password@example.com/database?sslmode=require"
    )


def test_frontend_origins_are_normalized_and_deduplicated() -> None:
    assert frontend_origins_from_environment(
        {
            "FRONTEND_ORIGINS": (
                "https://demo.example/, http://localhost:5173, "
                "https://demo.example"
            )
        }
    ) == ("https://demo.example", "http://localhost:5173")


@pytest.mark.parametrize(
    "origin",
    ["*", "demo.example", "https://demo.example/path"],
)
def test_frontend_origins_reject_unsafe_values(origin: str) -> None:
    with pytest.raises(ValueError, match="exact HTTP\\(S\\) origins"):
        frontend_origins_from_environment({"FRONTEND_ORIGINS": origin})


def test_cors_allows_only_the_configured_frontend_origin(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'cors.db').as_posix()}"

    with TestClient(
        create_app(
            database_url,
            frontend_origins=("https://demo.example",),
        )
    ) as client:
        allowed_response = client.options(
            "/posts",
            headers={
                "Origin": "https://demo.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        rejected_response = client.options(
            "/posts",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed_response.status_code == 200
    assert allowed_response.headers["access-control-allow-origin"] == (
        "https://demo.example"
    )
    assert "access-control-allow-origin" not in rejected_response.headers
