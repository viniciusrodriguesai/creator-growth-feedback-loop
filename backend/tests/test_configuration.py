from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import DEFAULT_DATABASE_URL, database_url_from_environment
from app.main import (
    app_environment_from_environment,
    create_app,
    create_runtime_app,
    frontend_origins_from_environment,
)


def test_database_url_defaults_to_local_sqlite() -> None:
    assert database_url_from_environment({}) == DEFAULT_DATABASE_URL


def test_database_url_uses_psycopg_for_postgres() -> None:
    database_url = "postgresql://user:password@example.com/database?sslmode=require"

    assert database_url_from_environment({"DATABASE_URL": database_url}) == (
        "postgresql+psycopg://user:password@example.com/database?sslmode=require"
    )


def test_invalid_database_url_returns_safe_configuration_error() -> None:
    secret_value = "secret-password"

    with pytest.raises(ValueError) as error:
        database_url_from_environment(
            {"DATABASE_URL": f"not a database URL {secret_value}"}
        )

    assert str(error.value) == "DATABASE_URL must be a valid database URL"
    assert secret_value not in str(error.value)


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


def test_app_environment_defaults_to_development() -> None:
    assert app_environment_from_environment({}) == "development"
    assert app_environment_from_environment({"APP_ENV": ""}) == "development"


def test_unknown_app_environment_is_rejected() -> None:
    with pytest.raises(ValueError, match="APP_ENV must be"):
        app_environment_from_environment({"APP_ENV": "staging"})


def test_development_runtime_allows_optional_configuration_to_be_absent() -> None:
    application = create_runtime_app({})

    try:
        assert str(application.state.database_engine.url) == DEFAULT_DATABASE_URL
        assert application.state.demo_write_rate_limiter is None
    finally:
        application.state.database_engine.dispose()


@pytest.mark.parametrize(
    "missing_variable",
    ["DATABASE_URL", "FRONTEND_ORIGINS", "YOUTUBE_API_KEY"],
)
def test_production_requires_core_configuration(missing_variable: str) -> None:
    secret_database_url = "sqlite:///:memory:"
    secret_youtube_key = "private-youtube-key"
    environment = {
        "APP_ENV": "production",
        "DATABASE_URL": secret_database_url,
        "FRONTEND_ORIGINS": "https://demo.example",
        "YOUTUBE_API_KEY": secret_youtube_key,
    }
    del environment[missing_variable]

    with pytest.raises(ValueError) as error:
        create_runtime_app(environment)

    assert missing_variable in str(error.value)
    assert secret_database_url not in str(error.value)
    assert secret_youtube_key not in str(error.value)


def test_complete_production_configuration_creates_application() -> None:
    application = create_runtime_app(
        {
            "APP_ENV": "production",
            "DATABASE_URL": "sqlite:///:memory:",
            "FRONTEND_ORIGINS": "https://demo.example",
            "YOUTUBE_API_KEY": "private-youtube-key",
        }
    )

    try:
        assert str(application.state.database_engine.url) == "sqlite:///:memory:"
        assert len(application.user_middleware) == 1
    finally:
        application.state.database_engine.dispose()
