import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ready_when_database_is_available(
    client: TestClient,
) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_does_not_query_the_database(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_connection() -> None:
        raise AssertionError("The liveness endpoint queried the database")

    monkeypatch.setattr(
        client.app.state.database_engine,
        "connect",
        unavailable_connection,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_safe_failure_when_database_is_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_url = "postgresql://demo:secret-password@private-db.example/app"

    def unavailable_connection() -> None:
        raise OperationalError(secret_url, {}, ConnectionError(secret_url))

    monkeypatch.setattr(
        client.app.state.database_engine,
        "connect",
        unavailable_connection,
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "database_unavailable",
            "message": "The database is unavailable.",
        }
    }
    assert "secret-password" not in response.text
    assert "private-db.example" not in response.text
    assert "OperationalError" not in response.text
