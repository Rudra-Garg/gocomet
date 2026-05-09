import { useEffect, useMemo, useState } from "react";

import ExtractionView from "./components/ExtractionView.jsx";
import QueryPanel from "./components/QueryPanel.jsx";
import RouterDecision from "./components/RouterDecision.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import ValidationView from "./components/ValidationView.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [activeRunId, setActiveRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [runs, setRuns] = useState([]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isComplete = useMemo(
    () => Boolean(runData?.action || runData?.error),
    [runData],
  );

  useEffect(() => {
    fetchRuns();
  }, []);

  useEffect(() => {
    if (!activeRunId || isComplete) {
      return undefined;
    }

    const poll = async () => {
      try {
        const nextRun = await fetchJson(`${API_BASE}/api/pipeline/${activeRunId}`);
        setRunData(nextRun);
        if (nextRun.action || nextRun.error) {
          fetchRuns();
        }
      } catch (pollError) {
        setError(pollError.message);
      }
    };

    poll();
    const intervalId = window.setInterval(poll, 2000);
    return () => window.clearInterval(intervalId);
  }, [activeRunId, isComplete]);

  async function fetchRuns() {
    try {
      setRuns(await fetchJson(`${API_BASE}/api/runs`));
    } catch {
      setRuns([]);
    }
  }

  async function selectRun(runId) {
    setError("");
    setActiveRunId(runId);
    try {
      setRunData(await fetchJson(`${API_BASE}/api/pipeline/${runId}`));
    } catch (selectError) {
      setError(selectError.message);
    }
  }

  async function handleUpload({ file, customerId }) {
    setError("");
    setIsSubmitting(true);
    const body = new FormData();
    body.append("customer_id", customerId);
    body.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/api/pipeline/run`, {
        method: "POST",
        body,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = await response.json();
      setActiveRunId(payload.run_id);
      if (payload.error) {
        setRunData({ run_id: payload.run_id, error: payload.error });
        return;
      }
      setRunData(await fetchJson(`${API_BASE}/api/pipeline/${payload.run_id}`));
      fetchRuns();
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="sidebar">
          <h1>Trade Document Validation</h1>
          <UploadPanel onUpload={handleUpload} isSubmitting={isSubmitting} />
          <div className="run-list">
            <h2>Recent runs</h2>
            {runs.length === 0 ? (
              <p className="muted">No runs yet.</p>
            ) : (
              runs.map((run) => (
                <button
                  className={run.run_id === activeRunId ? "run active" : "run"}
                  key={run.run_id}
                  onClick={() => void selectRun(run.run_id)}
                >
                  <span>{run.customer_id}</span>
                  <strong>{run.action || run.error || "processing"}</strong>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="content">
          {error && <div className="error-banner">{error}</div>}
          <RouterDecision decision={runData?.decision} error={runData?.error} />
          <ExtractionView fields={runData?.extraction || []} />
          <ValidationView results={runData?.validation || []} />
          <QueryPanel apiBase={API_BASE} activeRunId={activeRunId} onRunSelect={selectRun} />
        </section>
      </section>
    </main>
  );
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
