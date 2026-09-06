export type Platform = "youtube" | "instagram" | "tiktok";

export interface PostCreate {
  platform: Platform;
  title: string;
  hook_type: string;
  format: string;
  creator: string;
  views: number;
  likes: number;
  comments: number;
  shares: number | null;
  duration_seconds: number | null;
  published_at: string;
}

export interface Post extends PostCreate {
  id: number;
}

export interface AnalyticsSummary {
  post_count: number;
  eligible_post_count: number;
  total_views: number;
  known_core_engagements: number;
  known_shares: number | null;
  eligible_posts_with_share_data: number;
  eligible_posts_without_share_data: number;
  engagement_rate: number | null;
}

export interface AnalyticsGroup extends AnalyticsSummary {
  value: string;
  lift_vs_overall: number | null;
}

export interface AnalyticsLimitations {
  zero_view_posts_excluded_from_rates: number;
  eligible_posts_without_share_data: number;
  engagement_rate_definition: string;
  share_data_handling: string;
}

export interface AnalyticsResponse {
  overall: AnalyticsSummary;
  by_hook_type: AnalyticsGroup[];
  by_format: AnalyticsGroup[];
  by_creator: AnalyticsGroup[];
  limitations: AnalyticsLimitations;
}

export interface CreatorEvidence {
  value: string;
  eligible_post_count: number;
  total_views: number;
  engagement_rate: number;
  comparison_engagement_rate: number;
  contrast_vs_rest: number | null;
  rate_difference: number;
}

export interface RecommendationEvidence {
  summary: string;
  minimum_eligible_post_count: number;
  overall_eligible_post_count: number;
  actionable_candidates_evaluated: number;
  creator_candidates_evaluated: number;
  candidate_known_core_engagements: number | null;
  comparison_eligible_post_count: number | null;
  comparison_total_views: number | null;
  comparison_known_core_engagements: number | null;
  ranking_basis: string;
  strongest_creator: CreatorEvidence | null;
}

export type RecommendationStatus =
  | "recommendation_available"
  | "insufficient_data";

export type RecommendationDimension = "hook_type" | "format";

export interface RecommendationResponse {
  status: RecommendationStatus;
  dimension: RecommendationDimension | null;
  value: string | null;
  candidate_engagement_rate: number | null;
  comparison_engagement_rate: number | null;
  contrast_vs_rest: number | null;
  rate_difference: number | null;
  eligible_post_count: number | null;
  total_views: number | null;
  evidence: RecommendationEvidence;
  action: string;
  limitations: string[];
}

export interface ValidationIssue {
  type: string;
  loc: Array<string | number>;
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

export interface ValidationErrorResponse {
  detail: ValidationIssue[];
}
