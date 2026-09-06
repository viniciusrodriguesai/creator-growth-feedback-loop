from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.analytics import PostAnalyticsInput, calculate_analytics


def analytics_post(**overrides: Any) -> PostAnalyticsInput:
    values = {
        "hook_type": "pain_point",
        "format": "short",
        "creator": "Alex",
        "views": 100,
        "likes": 10,
        "comments": 5,
        "shares": 4,
    }
    values.update(overrides)
    return PostAnalyticsInput(**values)


def api_post_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "platform": "youtube",
        "title": "Analytics test post",
        "hook_type": "pain_point",
        "format": "short",
        "creator": "Alex",
        "views": 100,
        "likes": 10,
        "comments": 10,
        "shares": 5,
        "duration_seconds": 30,
        "published_at": "2026-09-05T12:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_no_posts_returns_empty_analytics() -> None:
    result = calculate_analytics([])

    assert result.overall.post_count == 0
    assert result.overall.eligible_post_count == 0
    assert result.overall.total_views == 0
    assert result.overall.known_core_engagements == 0
    assert result.overall.engagement_rate is None
    assert result.by_hook_type == ()
    assert result.by_format == ()
    assert result.by_creator == ()
    assert result.limitations.zero_view_posts_excluded_from_rates == 0


def test_one_post_calculates_core_engagement_and_known_shares() -> None:
    result = calculate_analytics([analytics_post()])

    assert result.overall.post_count == 1
    assert result.overall.eligible_post_count == 1
    assert result.overall.total_views == 100
    assert result.overall.known_core_engagements == 15
    assert result.overall.known_shares == 4
    assert result.overall.eligible_posts_with_share_data == 1
    assert result.overall.eligible_posts_without_share_data == 0
    assert result.overall.engagement_rate == pytest.approx(0.15)
    assert result.by_hook_type[0].lift_vs_overall == pytest.approx(1.0)


def test_all_zero_view_posts_are_excluded_from_rate_and_share_evidence() -> None:
    result = calculate_analytics(
        [
            analytics_post(views=0, shares=9),
            analytics_post(views=0, shares=None),
        ]
    )

    assert result.overall.post_count == 2
    assert result.overall.eligible_post_count == 0
    assert result.overall.total_views == 0
    assert result.overall.known_core_engagements == 0
    assert result.overall.known_shares == 0
    assert result.overall.eligible_posts_with_share_data == 0
    assert result.overall.eligible_posts_without_share_data == 0
    assert result.overall.engagement_rate is None
    assert result.by_hook_type[0].engagement_rate is None
    assert result.by_hook_type[0].lift_vs_overall is None
    assert result.limitations.zero_view_posts_excluded_from_rates == 2


def test_zero_view_post_does_not_affect_eligible_totals() -> None:
    result = calculate_analytics(
        [
            analytics_post(views=100, likes=15, comments=5, shares=3),
            analytics_post(views=0, likes=500, comments=500, shares=None),
        ]
    )

    assert result.overall.post_count == 2
    assert result.overall.eligible_post_count == 1
    assert result.overall.total_views == 100
    assert result.overall.known_core_engagements == 20
    assert result.overall.known_shares == 3
    assert result.overall.eligible_posts_with_share_data == 1
    assert result.overall.eligible_posts_without_share_data == 0
    assert result.overall.engagement_rate == pytest.approx(0.2)
    assert result.limitations.zero_view_posts_excluded_from_rates == 1


def test_zero_overall_engagement_rate_makes_all_lifts_unavailable() -> None:
    result = calculate_analytics(
        [
            analytics_post(hook_type="a", likes=0, comments=0),
            analytics_post(hook_type="b", likes=0, comments=0),
        ]
    )

    assert result.overall.engagement_rate == pytest.approx(0.0)
    assert [group.engagement_rate for group in result.by_hook_type] == pytest.approx(
        [0.0, 0.0]
    )
    assert [group.lift_vs_overall for group in result.by_hook_type] == [None, None]


def test_partial_share_data_is_separate_from_primary_engagement_rate() -> None:
    result = calculate_analytics(
        [
            analytics_post(likes=10, comments=0, shares=1000),
            analytics_post(likes=10, comments=0, shares=None),
        ]
    )

    assert result.overall.known_core_engagements == 20
    assert result.overall.known_shares == 1000
    assert result.overall.eligible_posts_with_share_data == 1
    assert result.overall.eligible_posts_without_share_data == 1
    assert result.overall.engagement_rate == pytest.approx(0.1)
    assert "missing shares are not treated as zero" in (
        result.limitations.share_data_handling
    )


def test_group_rate_uses_aggregated_totals_instead_of_mean_post_rate() -> None:
    result = calculate_analytics(
        [
            analytics_post(hook_type="a", views=10, likes=10, comments=0),
            analytics_post(hook_type="a", views=90, likes=0, comments=0),
            analytics_post(hook_type="b", views=100, likes=20, comments=0),
        ]
    )

    group_a, group_b = result.by_hook_type

    assert result.overall.engagement_rate == pytest.approx(30 / 200)
    assert group_a.post_count == 2
    assert group_a.engagement_rate == pytest.approx(10 / 100)
    assert group_a.engagement_rate != pytest.approx((1.0 + 0.0) / 2)
    assert group_a.lift_vs_overall == pytest.approx((10 / 100) / (30 / 200))
    assert group_b.post_count == 1
    assert group_b.engagement_rate == pytest.approx(20 / 100)


def test_groups_have_deterministic_case_insensitive_name_order() -> None:
    result = calculate_analytics(
        [
            analytics_post(hook_type="beta", format="z", creator="Zed"),
            analytics_post(hook_type="Alpha", format="Beta", creator="carol"),
            analytics_post(hook_type="alpha", format="alpha", creator="Bob"),
        ]
    )

    assert [group.value for group in result.by_hook_type] == [
        "Alpha",
        "alpha",
        "beta",
    ]
    assert [group.value for group in result.by_format] == ["alpha", "Beta", "z"]
    assert [group.value for group in result.by_creator] == ["Bob", "carol", "Zed"]


def test_interactions_greater_than_views_are_not_capped() -> None:
    result = calculate_analytics(
        [analytics_post(views=10, likes=12, comments=3, shares=None)]
    )

    assert result.overall.engagement_rate == pytest.approx(1.5)


def test_analytics_endpoint_uses_persisted_posts(client: TestClient) -> None:
    responses = [
        client.post("/posts", json=api_post_payload()),
        client.post(
            "/posts",
            json=api_post_payload(
                title="Second post",
                format="long",
                creator="Bea",
                views=900,
                likes=45,
                comments=45,
                shares=None,
            ),
        ),
        client.post(
            "/posts",
            json=api_post_payload(
                title="Zero-view post",
                hook_type="product_led",
                views=0,
                likes=1000,
                comments=1000,
                shares=99,
            ),
        ),
    ]
    assert [response.status_code for response in responses] == [201, 201, 201]

    response = client.get("/analytics")
    body = response.json()

    assert response.status_code == 200
    assert body["overall"]["post_count"] == 3
    assert body["overall"]["eligible_post_count"] == 2
    assert body["overall"]["total_views"] == 1000
    assert body["overall"]["known_core_engagements"] == 110
    assert body["overall"]["known_shares"] == 5
    assert body["overall"]["eligible_posts_with_share_data"] == 1
    assert body["overall"]["eligible_posts_without_share_data"] == 1
    assert body["overall"]["engagement_rate"] == pytest.approx(0.11)
    assert [group["value"] for group in body["by_hook_type"]] == [
        "pain_point",
        "product_led",
    ]
    assert body["by_hook_type"][0]["lift_vs_overall"] == pytest.approx(1.0)
    assert body["by_hook_type"][1]["engagement_rate"] is None
    assert body["by_hook_type"][1]["lift_vs_overall"] is None
    assert body["limitations"]["zero_view_posts_excluded_from_rates"] == 1
    assert body["limitations"]["eligible_posts_without_share_data"] == 1
