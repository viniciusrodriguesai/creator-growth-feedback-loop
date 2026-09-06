from typing import Any

import pytest
from fastapi.testclient import TestClient


def post_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "platform": "youtube",
        "title": "Three ways to improve your opening",
        "hook_type": "pain_point",
        "format": "short",
        "creator": "Alex",
        "views": 1200,
        "likes": 140,
        "comments": 18,
        "shares": 24,
        "duration_seconds": 42,
        "published_at": "2026-09-05T09:30:00-03:00",
    }
    payload.update(overrides)
    return payload


def test_create_and_list_posts_in_id_order(client: TestClient) -> None:
    first_response = client.post("/posts", json=post_payload(title="First post"))
    second_response = client.post(
        "/posts",
        json=post_payload(platform="instagram", title="Second post"),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] == 1
    assert second_response.json()["id"] == 2
    assert first_response.json()["published_at"] == "2026-09-05T12:30:00Z"

    list_response = client.get("/posts")

    assert list_response.status_code == 200
    assert list_response.json() == [first_response.json(), second_response.json()]


@pytest.mark.parametrize(
    "field",
    ["views", "likes", "comments", "shares", "duration_seconds"],
)
def test_negative_numeric_values_are_rejected(
    client: TestClient,
    field: str,
) -> None:
    response = client.post("/posts", json=post_payload(**{field: -1}))

    assert response.status_code == 422


def test_zero_views_and_more_interactions_than_views_are_accepted(
    client: TestClient,
) -> None:
    response = client.post(
        "/posts",
        json=post_payload(views=0, likes=10, comments=2, shares=1),
    )

    assert response.status_code == 201
    assert response.json()["views"] == 0
    assert response.json()["likes"] == 10


def test_timezone_naive_published_at_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/posts",
        json=post_payload(published_at="2026-09-05T09:30:00"),
    )

    assert response.status_code == 422


def test_unknown_platform_is_rejected(client: TestClient) -> None:
    response = client.post("/posts", json=post_payload(platform="other"))

    assert response.status_code == 422
