import type { RecommendationResponse } from "../api/types";
import type { ResourceState } from "../hooks/useDashboardData";
import {
  formatDisplayText,
  formatDisplayValue,
  formatInteger,
  formatLift,
  formatPercentage,
} from "../lib/format";

interface NextExperimentCardProps {
  resource: ResourceState<RecommendationResponse>;
}

function formatDimension(value: "hook_type" | "format"): string {
  return value === "hook_type" ? "Hook type" : "Format";
}

function formatRecommendationTitle(
  dimension: "hook_type" | "format",
  value: string,
): string {
  const naturalValue = value.replaceAll("_", "-");
  return dimension === "hook_type"
    ? `Test ${naturalValue} hooks next`
    : `Test ${naturalValue} format next`;
}

function hasCompleteRecommendation(
  recommendation: RecommendationResponse,
): recommendation is RecommendationResponse & {
  dimension: "hook_type" | "format";
  value: string;
  candidate_engagement_rate: number;
  comparison_engagement_rate: number;
  rate_difference: number;
  eligible_post_count: number;
  total_views: number;
} {
  return (
    recommendation.status === "recommendation_available" &&
    recommendation.dimension !== null &&
    recommendation.value !== null &&
    recommendation.candidate_engagement_rate !== null &&
    recommendation.comparison_engagement_rate !== null &&
    recommendation.rate_difference !== null &&
    recommendation.eligible_post_count !== null &&
    recommendation.total_views !== null
  );
}

export function NextExperimentCard({ resource }: NextExperimentCardProps) {
  const recommendation = resource.data;
  const recommendationAvailable =
    recommendation !== null && hasCompleteRecommendation(recommendation);

  return (
    <section
      className={`next-experiment-card panel${
        recommendation?.status === "insufficient_data" ? " insufficient" : ""
      }`}
      aria-labelledby="next-experiment-title"
    >
      <div className="recommendation-heading">
        <div>
          <p className="eyebrow">Next experiment</p>
          <h2 id="next-experiment-title">
            {recommendationAvailable
              ? formatRecommendationTitle(
                  recommendation.dimension,
                  recommendation.value,
                )
              : recommendation?.status === "insufficient_data"
                ? "More comparable posts needed"
                : "Finding the clearest next test"}
          </h2>
        </div>
        <span className="observational-badge">Observational evidence</span>
      </div>

      {resource.error ? (
        <p className="inline-error" role="alert">
          The recommendation could not be refreshed. {resource.error}
        </p>
      ) : null}

      {resource.loading && !recommendation ? (
        <p className="recommendation-status" role="status">
          Comparing actionable patterns...
        </p>
      ) : null}

      {recommendation?.status === "insufficient_data" ? (
        <div className="insufficient-state">
          <p>{formatDisplayText(recommendation.evidence.summary)}</p>
          <strong>{formatDisplayText(recommendation.action)}</strong>
          <span>
            Current evidence: {recommendation.evidence.overall_eligible_post_count}{" "}
            eligible posts. Candidate minimum:{" "}
            {recommendation.evidence.minimum_eligible_post_count}.
          </span>
        </div>
      ) : null}

      {recommendationAvailable ? (
        <>
          <div className="recommendation-lead">
            <div className="recommendation-target">
              <span>{formatDimension(recommendation.dimension)}</span>
              <strong>{formatDisplayValue(recommendation.value)}</strong>
            </div>
            <div className="recommendation-action">
              <span>Controlled next action</span>
              <p>{formatDisplayText(recommendation.action)}</p>
            </div>
          </div>

          <dl className="recommendation-metrics">
            <div>
              <dt>Candidate engagement</dt>
              <dd>{formatPercentage(recommendation.candidate_engagement_rate)}</dd>
            </div>
            <div>
              <dt>Other eligible posts</dt>
              <dd>{formatPercentage(recommendation.comparison_engagement_rate)}</dd>
            </div>
            <div>
              <dt>Rate difference</dt>
              <dd>+{formatPercentage(recommendation.rate_difference)}</dd>
            </div>
            <div>
              <dt>Contrast</dt>
              <dd>
                {formatLift(recommendation.contrast_vs_rest)}
                <span>engagement vs other eligible posts</span>
              </dd>
            </div>
            <div>
              <dt>Eligible posts</dt>
              <dd>{formatInteger(recommendation.eligible_post_count)}</dd>
            </div>
            <div>
              <dt>Total views</dt>
              <dd>{formatInteger(recommendation.total_views)}</dd>
            </div>
          </dl>

          <div className="recommendation-evidence">
            <div>
              <h3>Why this experiment</h3>
              <p>{formatDisplayText(recommendation.evidence.summary)}</p>
            </div>
            <div>
              <h3>Interpret with care</h3>
              <ul>
                {recommendation.limitations.map((limitation) => (
                  <li key={limitation}>{formatDisplayText(limitation)}</li>
                ))}
              </ul>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
