import type { Post } from "../api/types";
import type { ResourceState } from "../hooks/useDashboardData";
import { formatDateTime, formatInteger } from "../lib/format";

interface ExistingPostsTableProps {
  resource: ResourceState<Post[]>;
}

export function ExistingPostsTable({ resource }: ExistingPostsTableProps) {
  return (
    <section className="panel posts-panel" aria-labelledby="posts-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Evidence base</p>
          <h2 id="posts-title">Existing posts</h2>
        </div>
        {resource.data ? <span className="count-badge">{resource.data.length}</span> : null}
      </div>

      {resource.error ? (
        <p className="inline-error" role="alert">
          Posts could not be refreshed. {resource.error}
        </p>
      ) : null}

      {resource.loading && !resource.data ? (
        <p className="section-status" role="status">Loading content records…</p>
      ) : null}

      {resource.data?.length === 0 ? (
        <div className="empty-state">
          <h3>No content yet</h3>
          <p>Add the first performance record to start building evidence.</p>
        </div>
      ) : null}

      {resource.data && resource.data.length > 0 ? (
        <div className="table-scroll">
          <table>
            <caption>Content records used by analytics and recommendations</caption>
            <thead>
              <tr>
                <th scope="col">Title</th>
                <th scope="col">Platform</th>
                <th scope="col">Hook</th>
                <th scope="col">Format</th>
                <th scope="col">Creator</th>
                <th scope="col" className="numeric-cell">Views</th>
                <th scope="col">Published</th>
              </tr>
            </thead>
            <tbody>
              {resource.data.map((post) => (
                <tr key={post.id}>
                  <th scope="row">{post.title}</th>
                  <td><span className="platform-tag">{post.platform}</span></td>
                  <td>{post.hook_type}</td>
                  <td>{post.format}</td>
                  <td>{post.creator}</td>
                  <td className="numeric-cell">{formatInteger(post.views)}</td>
                  <td>{formatDateTime(post.published_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
