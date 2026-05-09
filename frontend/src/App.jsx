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
    () => Boolean(runData?.action || runData?.decision?.action || runData?.error),
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
        if (nextRun.action || nextRun.decision?.action || nextRun.error) {
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
      setRunData(payload.state);
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
                  onClick={() => {
                    setActiveRunId(run.run_id);
                    fetchJson(`${API_BASE}/api/pipeline/${run.run_id}`).then(setRunData);
                  }}
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
          <RouterDecision decision={runData?.decision || runData} error={runData?.error} />
          <ExtractionView extraction={runData?.extraction} />
          <ValidationView validation={runData?.validation} />
          <QueryPanel apiBase={API_BASE} />
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

