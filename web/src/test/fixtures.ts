import type {
  AnalyticsResponse,
  Post,
  RecommendationResponse,
} from "../api/types";

export const posts: Post[] = [
  {
    id: 1,
    platform: "youtube",
    title: "Pain point opening",
    hook_type: "pain_point",
    format: "short",
    creator: "Alex",
    views: 1200,
    likes: 180,
    comments: 20,
    shares: null,
    duration_seconds: 35,
    published_at: "2026-09-05T12:00:00Z",
  },
  {
    id: 2,
    platform: "instagram",
    title: "Product opening",
    hook_type: "product_led",
    format: "long",
    creator: "Bea",
    views: 800,
    likes: 70,
    comments: 10,
    shares: 4,
    duration_seconds: 60,
    published_at: "2026-09-04T12:00:00Z",
  },
];

export const analytics: AnalyticsResponse = {
  overall: {
    post_count: 2,
    eligible_post_count: 2,
    total_views: 2000,
    known_core_engagements: 280,
    known_shares: 4,
    eligible_posts_with_share_data: 1,
    eligible_posts_without_share_data: 1,
    engagement_rate: 0.14,
  },
  by_hook_type: [
    {
      value: "pain_point",
      post_count: 1,
      eligible_post_count: 1,
      total_views: 1200,
      known_core_engagements: 200,
      known_shares: null,
      eligible_posts_with_share_data: 0,
      eligible_posts_without_share_data: 1,
      engagement_rate: 1 / 6,
      lift_vs_overall: (1 / 6) / 0.14,
    },
    {
      value: "product_led",
      post_count: 1,
      eligible_post_count: 1,
      total_views: 800,
      known_core_engagements: 80,
      known_shares: 4,
      eligible_posts_with_share_data: 1,
      eligible_posts_without_share_data: 0,
      engagement_rate: 0.1,
      lift_vs_overall: 0.1 / 0.14,
    },
  ],
  by_format: [],
  by_creator: [],
  limitations: {
    zero_view_posts_excluded_from_rates: 0,
    eligible_posts_without_share_data: 1,
    engagement_rate_definition:
      "Engagement rate uses likes plus comments divided by views for posts with views greater than zero.",
    share_data_handling:
      "Shares are excluded from engagement rate and lift; missing shares are not treated as zero.",
  },
};

export const recommendation: RecommendationResponse = {
  status: "recommendation_available",
  dimension: "hook_type",
  value: "pain_point",
  candidate_engagement_rate: 0.185,
  comparison_engagement_rate: 0.0825,
  contrast_vs_rest: 2.2424242424,
  rate_difference: 0.1025,
  eligible_post_count: 4,
  total_views: 4000,
  evidence: {
    summary:
      "The 'pain_point' hook_type was associated with higher observed core engagement than the rest of eligible posts.",
    minimum_eligible_post_count: 2,
    overall_eligible_post_count: 8,
    actionable_candidates_evaluated: 4,
    creator_candidates_evaluated: 2,
    candidate_known_core_engagements: 740,
    comparison_eligible_post_count: 4,
    comparison_total_views: 4000,
    comparison_known_core_engagements: 330,
    ranking_basis:
      "Candidates are ranked by rate_difference, then eligible sample, views, dimension priority, and lexical value.",
    strongest_creator: null,
  },
  action:
    "Test new hook variations within the 'pain_point' hook_type while keeping format as consistent as possible.",
  limitations: [
    "The minimum eligible-post count is a product heuristic, not statistical significance.",
    "The result is observational and shows association, not causation.",
    "Shares are excluded from the primary comparison because share data may be unavailable.",
  ],
};

export const insufficientRecommendation: RecommendationResponse = {
  status: "insufficient_data",
  dimension: null,
  value: null,
  candidate_engagement_rate: null,
  comparison_engagement_rate: null,
  contrast_vs_rest: null,
  rate_difference: null,
  eligible_post_count: null,
  total_views: null,
  evidence: {
    summary:
      "No actionable group met the minimum eligible-post count with a valid comparison population.",
    minimum_eligible_post_count: 2,
    overall_eligible_post_count: 1,
    actionable_candidates_evaluated: 0,
    creator_candidates_evaluated: 0,
    candidate_known_core_engagements: null,
    comparison_eligible_post_count: null,
    comparison_total_views: null,
    comparison_known_core_engagements: null,
    ranking_basis:
      "Candidates are ranked by rate_difference, then eligible sample, views, dimension priority, and lexical value.",
    strongest_creator: null,
  },
  action:
    "Collect more eligible posts across at least two hook types or formats before selecting an experiment.",
  limitations: [
    "The result is observational and shows association, not causation.",
  ],
};
