from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.analytics import PostAnalyticsInput, calculate_analytics
from app.recommendations import evaluate_candidates, recommend_next_experiment


def recommendation_post(**overrides: Any) -> PostAnalyticsInput:
    values = {
        "hook_type": "pain_point",
        "format": "short",
        "creator": "Alex",
        "views": 100,
        "likes": 10,
        "comments": 0,
        "shares": None,
    }
    values.update(overrides)
    return PostAnalyticsInput(**values)


def api_post_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "platform": "youtube",
        "title": "Recommendation test post",
        "hook_type": "pain_point",
        "format": "short",
        "creator": "Alex",
        "views": 1000,
        "likes": 100,
        "comments": 10,
        "shares": None,
        "duration_seconds": 30,
        "published_at": "2026-09-05T12:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_no_posts_returns_insufficient_data() -> None:
    result = recommend_next_experiment([])

    assert result.status == "insufficient_data"
    assert result.dimension is None
    assert result.evidence.overall_eligible_post_count == 0


def test_only_zero_view_posts_return_insufficient_data() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(views=0, likes=1000),
            recommendation_post(views=0, comments=1000),
        ]
    )

    assert result.status == "insufficient_data"
    assert result.evidence.overall_eligible_post_count == 0


def test_one_eligible_post_returns_insufficient_data() -> None:
    result = recommend_next_experiment([recommendation_post()])

    assert result.status == "insufficient_data"
    assert result.evidence.actionable_candidates_evaluated == 0


def test_single_post_candidate_is_ignored() -> None:
    posts = [
        recommendation_post(hook_type="viral", likes=80),
        recommendation_post(hook_type="baseline", likes=10),
        recommendation_post(hook_type="baseline", likes=10),
    ]

    candidates = evaluate_candidates(calculate_analytics(posts))
    result = recommend_next_experiment(posts)

    assert not any(
        candidate.dimension == "hook_type" and candidate.value == "viral"
        for candidate in candidates
    )
    assert result.status == "insufficient_data"


def test_candidate_with_multiple_posts_can_be_recommended() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(hook_type="pain", likes=20),
            recommendation_post(hook_type="pain", likes=20),
            recommendation_post(hook_type="product", likes=10),
            recommendation_post(hook_type="product", likes=10),
        ]
    )

    assert result.status == "recommendation_available"
    assert result.dimension == "hook_type"
    assert result.value == "pain"
    assert result.eligible_post_count == 2
    assert result.candidate_engagement_rate == pytest.approx(0.2)
    assert result.comparison_engagement_rate == pytest.approx(0.1)
    assert result.contrast_vs_rest == pytest.approx(2.0)
    assert result.rate_difference == pytest.approx(0.1)


def test_underperforming_eligible_candidate_is_not_recommended() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(hook_type="low", likes=5),
            recommendation_post(hook_type="low", likes=5),
            recommendation_post(hook_type="high_single", likes=50),
        ]
    )

    assert result.status == "insufficient_data"
    assert result.dimension is None


def test_no_valid_comparison_population_returns_insufficient_data() -> None:
    result = recommend_next_experiment(
        [recommendation_post(), recommendation_post()]
    )

    assert result.status == "insufficient_data"
    assert result.evidence.actionable_candidates_evaluated == 0


def test_zero_rest_rate_keeps_ratio_null_and_absolute_difference() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(hook_type="pain", likes=20),
            recommendation_post(hook_type="pain", likes=20),
            recommendation_post(hook_type="product", likes=0),
            recommendation_post(hook_type="product", likes=0),
        ]
    )

    assert result.status == "recommendation_available"
    assert result.value == "pain"
    assert result.comparison_engagement_rate == pytest.approx(0.0)
    assert result.contrast_vs_rest is None
    assert result.rate_difference == pytest.approx(0.2)


def test_tied_values_use_stable_lexical_order_regardless_of_input_order() -> None:
    posts = [
        recommendation_post(hook_type="beta", likes=20),
        recommendation_post(hook_type="alpha", likes=20),
        recommendation_post(hook_type="gamma", likes=0),
        recommendation_post(hook_type="beta", likes=20),
        recommendation_post(hook_type="alpha", likes=20),
        recommendation_post(hook_type="gamma", likes=0),
    ]

    forward = recommend_next_experiment(posts)
    reverse = recommend_next_experiment(reversed(posts))

    assert forward.dimension == "hook_type"
    assert forward.value == "alpha"
    assert reverse.dimension == "hook_type"
    assert reverse.value == "alpha"


def test_tied_dimensions_prefer_hook_type_over_format() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(hook_type="pain", format="short", likes=20),
            recommendation_post(hook_type="pain", format="short", likes=20),
            recommendation_post(hook_type="product", format="long", likes=10),
            recommendation_post(hook_type="product", format="long", likes=10),
        ]
    )

    assert result.dimension == "hook_type"
    assert result.value == "pain"
    assert any("format may be confounded" in item for item in result.limitations)


def test_winning_hook_exposes_creator_confounding() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(
                hook_type="pain", format="short", creator="Alex", likes=20
            ),
            recommendation_post(
                hook_type="pain", format="long", creator="Alex", likes=20
            ),
            recommendation_post(
                hook_type="product", format="short", creator="Bea", likes=10
            ),
            recommendation_post(
                hook_type="product", format="long", creator="Bea", likes=10
            ),
        ]
    )

    assert result.dimension == "hook_type"
    assert result.value == "pain"
    assert any("creator may be confounded" in item for item in result.limitations)
    assert not any("format may be confounded" in item for item in result.limitations)


def test_winning_format_exposes_hook_type_confounding() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(
                hook_type="pain", format="short", creator="Alex", likes=20
            ),
            recommendation_post(
                hook_type="pain", format="short", creator="Bea", likes=20
            ),
            recommendation_post(
                hook_type="pain", format="long", creator="Alex", likes=0
            ),
            recommendation_post(
                hook_type="product", format="long", creator="Alex", likes=10
            ),
            recommendation_post(
                hook_type="product", format="long", creator="Bea", likes=10
            ),
        ]
    )

    assert result.dimension == "format"
    assert result.value == "short"
    assert any("hook_type may be confounded" in item for item in result.limitations)
    assert not any("creator may be confounded" in item for item in result.limitations)


def test_creator_evidence_does_not_override_actionable_candidate() -> None:
    posts = [
        recommendation_post(hook_type="good", creator="Alex", likes=30),
        recommendation_post(hook_type="good", creator="Alex", likes=30),
        recommendation_post(hook_type="bad", creator="Alex", likes=20),
        recommendation_post(hook_type="bad", creator="Alex", likes=20),
        recommendation_post(hook_type="good", creator="Bea", likes=10),
        recommendation_post(hook_type="good", creator="Bea", likes=10),
        recommendation_post(hook_type="bad", creator="Bea", likes=5),
        recommendation_post(hook_type="bad", creator="Bea", likes=5),
    ]

    result = recommend_next_experiment(posts)

    assert result.dimension == "hook_type"
    assert result.value == "good"
    assert result.evidence.strongest_creator is not None
    assert result.evidence.strongest_creator.value == "Alex"
    assert result.evidence.strongest_creator.rate_difference > result.rate_difference


def test_interactions_greater_than_views_are_preserved() -> None:
    result = recommend_next_experiment(
        [
            recommendation_post(hook_type="high", views=10, likes=15),
            recommendation_post(hook_type="high", views=10, likes=15),
            recommendation_post(hook_type="low", views=10, likes=1),
            recommendation_post(hook_type="low", views=10, likes=1),
        ]
    )

    assert result.status == "recommendation_available"
    assert result.candidate_engagement_rate == pytest.approx(1.5)


def test_share_availability_does_not_change_primary_recommendation() -> None:
    base_posts = [
        recommendation_post(hook_type="pain", likes=20),
        recommendation_post(hook_type="pain", likes=20),
        recommendation_post(hook_type="product", likes=10),
        recommendation_post(hook_type="product", likes=10),
    ]
    mixed_shares = [
        recommendation_post(hook_type="pain", likes=20, shares=1000),
        recommendation_post(hook_type="pain", likes=20, shares=None),
        recommendation_post(hook_type="product", likes=10, shares=0),
        recommendation_post(hook_type="product", likes=10, shares=None),
    ]

    assert recommend_next_experiment(base_posts) == recommend_next_experiment(
        mixed_shares
    )


def test_recommendations_endpoint_uses_persisted_posts(client: TestClient) -> None:
    posts = [
        api_post_payload(title="Pain 1", likes=180, comments=20),
        api_post_payload(
            title="Pain 2", format="long", creator="Bea", likes=160, comments=20,
            shares=10,
        ),
        api_post_payload(
            title="Pain 3", creator="Bea", likes=170, comments=20
        ),
        api_post_payload(
            title="Pain 4", format="long", likes=150, comments=20, shares=8
        ),
        api_post_payload(
            title="Product 1", hook_type="product_led", likes=80, comments=10
        ),
        api_post_payload(
            title="Product 2", hook_type="product_led", format="long",
            creator="Bea", likes=70, comments=10, shares=5,
        ),
        api_post_payload(
            title="Product 3", hook_type="product_led", creator="Bea", likes=75,
            comments=10,
        ),
        api_post_payload(
            title="Product 4", hook_type="product_led", format="long", likes=65,
            comments=10, shares=4,
        ),
    ]
    responses = [client.post("/posts", json=post) for post in posts]
    assert [response.status_code for response in responses] == [201] * 8

    response = client.get("/recommendations")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "recommendation_available"
    assert body["dimension"] == "hook_type"
    assert body["value"] == "pain_point"
    assert body["candidate_engagement_rate"] == pytest.approx(740 / 4000)
    assert body["comparison_engagement_rate"] == pytest.approx(330 / 4000)
    assert body["contrast_vs_rest"] == pytest.approx((740 / 4000) / (330 / 4000))
    assert body["rate_difference"] == pytest.approx((740 - 330) / 4000)
    assert body["eligible_post_count"] == 4
    assert body["total_views"] == 4000
    assert body["evidence"]["candidate_known_core_engagements"] == 740
    assert body["evidence"]["comparison_known_core_engagements"] == 330
    assert body["evidence"]["strongest_creator"]["rate_difference"] == pytest.approx(
        0.0
    )
    assert "keeping format as consistent as possible" in body["action"]
