import type { AnalyticsResponse } from "../api/types";
import type { ResourceState } from "../hooks/useDashboardData";
import { BreakdownTable } from "./BreakdownTable";

interface PerformanceBreakdownProps {
  resource: ResourceState<AnalyticsResponse>;
}

export function PerformanceBreakdown({ resource }: PerformanceBreakdownProps) {
  if (!resource.data) {
    return null;
  }

  return (
    <section className="panel breakdown-section" aria-labelledby="breakdown-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Observed patterns</p>
          <h2 id="breakdown-title">Performance breakdown</h2>
        </div>
        <p>Aggregated engagement rates, weighted by views.</p>
      </div>

      <div className="breakdown-grid">
        <BreakdownTable caption="Hook type" groups={resource.data.by_hook_type} />
        <BreakdownTable caption="Format" groups={resource.data.by_format} />
        <BreakdownTable caption="Creator" groups={resource.data.by_creator} />
      </div>

      <div className="metric-note">
        <strong>Metric note</strong>
        <span>{resource.data.limitations.engagement_rate_definition}</span>
        <span>{resource.data.limitations.share_data_handling}</span>
      </div>
    </section>
  );
}
