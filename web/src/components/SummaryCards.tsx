import type { AnalyticsResponse } from "../api/types";
import type { ResourceState } from "../hooks/useDashboardData";
import { formatInteger, formatPercentage } from "../lib/format";

interface SummaryCardsProps {
  resource: ResourceState<AnalyticsResponse>;
}

export function SummaryCards({ resource }: SummaryCardsProps) {
  return (
    <section className="summary-section" aria-labelledby="summary-title">
      <div className="compact-heading">
        <div>
          <p className="eyebrow">Current baseline</p>
          <h2 id="summary-title">Performance snapshot</h2>
        </div>
        {resource.loading && resource.data ? (
          <span className="refresh-status" role="status">Refreshing…</span>
        ) : null}
      </div>

      {resource.error ? (
        <p className="inline-error" role="alert">
          Analytics could not be refreshed. {resource.error}
        </p>
      ) : null}

      {resource.loading && !resource.data ? (
        <p className="section-status" role="status">Loading analytics…</p>
      ) : null}

      {resource.data ? (
        <div className="summary-grid">
          <article className="summary-card">
            <span>Total posts</span>
            <strong>{formatInteger(resource.data.overall.post_count)}</strong>
          </article>
          <article className="summary-card">
            <span>Eligible posts</span>
            <strong>{formatInteger(resource.data.overall.eligible_post_count)}</strong>
          </article>
          <article className="summary-card">
            <span>Total views</span>
            <strong>{formatInteger(resource.data.overall.total_views)}</strong>
          </article>
          <article className="summary-card">
            <span>Engagement rate</span>
            <strong>{formatPercentage(resource.data.overall.engagement_rate)}</strong>
          </article>
        </div>
      ) : null}
    </section>
  );
}
