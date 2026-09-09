import { useState } from "react";

import { ApiError, deletePost } from "../api/client";
import type { Post } from "../api/types";
import type { ResourceState } from "../hooks/useDashboardData";
import {
  formatDateTime,
  formatDisplayValue,
  formatInteger,
} from "../lib/format";

interface ExistingPostsTableProps {
  resource: ResourceState<Post[]>;
  onDeleted: () => Promise<void>;
}

function deleteErrorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Unable to delete this post. Please try again.";
}

export function ExistingPostsTable({
  resource,
  onDeleted,
}: ExistingPostsTableProps) {
  const [deletingPostId, setDeletingPostId] = useState<number | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete(post: Post) {
    if (
      deletingPostId !== null ||
      !window.confirm(`Delete "${post.title}"? This cannot be undone.`)
    ) {
      return;
    }

    setDeleteError(null);
    setDeletingPostId(post.id);
    try {
      await deletePost(post.id);
      await onDeleted();
    } catch (error) {
      setDeleteError(deleteErrorMessage(error));
    } finally {
      setDeletingPostId(null);
    }
  }

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

      {deleteError ? (
        <p className="inline-error" role="alert">
          Post could not be deleted. {deleteError}
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
                <th scope="col" className="action-cell">Action</th>
              </tr>
            </thead>
            <tbody>
              {resource.data.map((post) => (
                <tr key={post.id}>
                  <th scope="row">{post.title}</th>
                  <td><span className="platform-tag">{post.platform}</span></td>
                  <td>{formatDisplayValue(post.hook_type)}</td>
                  <td>{formatDisplayValue(post.format)}</td>
                  <td>{formatDisplayValue(post.creator)}</td>
                  <td className="numeric-cell">{formatInteger(post.views)}</td>
                  <td>{formatDateTime(post.published_at)}</td>
                  <td className="action-cell">
                    <button
                      type="button"
                      className="delete-action"
                      disabled={deletingPostId !== null}
                      aria-busy={deletingPostId === post.id}
                      onClick={() => void handleDelete(post)}
                    >
                      {deletingPostId === post.id ? "Deleting…" : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
