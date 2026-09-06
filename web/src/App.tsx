import { AddContentForm } from "./components/AddContentForm";
import { ExistingPostsTable } from "./components/ExistingPostsTable";
import { NextExperimentCard } from "./components/NextExperimentCard";
import { PerformanceBreakdown } from "./components/PerformanceBreakdown";
import { SummaryCards } from "./components/SummaryCards";
import { useDashboardData } from "./hooks/useDashboardData";

function App() {
  const { posts, analytics, recommendation, refreshAll } = useDashboardData();
  const resources = [posts, analytics, recommendation];
  const initialLoading = resources.every(
    (resource) => resource.loading && resource.data === null,
  );
  const catastrophicFailure = resources.every(
    (resource) => resource.error !== null && resource.data === null,
  );

  return (
    <div className="app-shell">
      <header className="product-header">
        <p className="eyebrow">Content intelligence</p>
        <h1>Creator Growth Feedback Loop</h1>
        <p>Turn content performance into an explainable next experiment.</p>
      </header>
      <main>
        {initialLoading ? (
          <section className="panel global-state" aria-live="polite">
            <p className="eyebrow">Connecting the loop</p>
            <h2>Loading content evidence…</h2>
          </section>
        ) : catastrophicFailure ? (
          <section className="panel global-state" role="alert">
            <p className="eyebrow">Connection problem</p>
            <h2>The product data is unavailable</h2>
            <p>Check that the FastAPI backend is running, then try again.</p>
            <button type="button" onClick={() => void refreshAll()}>
              Retry connection
            </button>
          </section>
        ) : (
          <>
            <NextExperimentCard resource={recommendation} />

            <SummaryCards resource={analytics} />
            <PerformanceBreakdown resource={analytics} />

            <div className="content-workspace">
              <AddContentForm onCreated={refreshAll} />
              <ExistingPostsTable resource={posts} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
