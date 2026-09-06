import type { AnalyticsGroup } from "../api/types";
import { formatInteger, formatLift, formatPercentage } from "../lib/format";

interface BreakdownTableProps {
  caption: string;
  groups: AnalyticsGroup[];
}

export function BreakdownTable({ caption, groups }: BreakdownTableProps) {
  return (
    <article className="breakdown-card">
      <h3>{caption}</h3>
      {groups.length === 0 ? (
        <p className="section-status">No groups available yet.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <caption>Engagement performance grouped by {caption.toLowerCase()}</caption>
            <thead>
              <tr>
                <th scope="col">Value</th>
                <th scope="col" className="numeric-cell">Eligible</th>
                <th scope="col" className="numeric-cell">Views</th>
                <th scope="col" className="numeric-cell">Engagement</th>
                <th scope="col" className="numeric-cell">Lift</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.value}>
                  <th scope="row">{group.value}</th>
                  <td className="numeric-cell">
                    {formatInteger(group.eligible_post_count)}
                  </td>
                  <td className="numeric-cell">{formatInteger(group.total_views)}</td>
                  <td className="numeric-cell">
                    {formatPercentage(group.engagement_rate)}
                  </td>
                  <td className="numeric-cell">{formatLift(group.lift_vs_overall)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}
