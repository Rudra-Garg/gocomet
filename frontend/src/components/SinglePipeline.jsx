import { useEffect, useMemo, useState } from "react";

import ExtractionView from "./ExtractionView.jsx";
import RouterDecision from "./RouterDecision.jsx";
import UploadPanel from "./UploadPanel.jsx";
import ValidationView from "./ValidationView.jsx";

export default function SinglePipeline({ apiBase, initialRunId }) {
  const [activeRunId, setActiveRunId] = useState(initialRunId || null);
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

  // If navigated from Query panel
  useEffect(() => {
    if (initialRunId && initialRunId !== activeRunId) {
      selectRun(initialRunId);
    }
  }, [initialRunId]);

  useEffect(() => {
    if (!activeRunId || isComplete) {
      return undefined;
    }

    const poll = async () => {
      try {
        const nextRun = await fetchJson(`${apiBase}/api/pipeline/${activeRunId}`);
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
  }, [activeRunId, isComplete, apiBase]);

  async function fetchRuns() {
    try {
      setRuns(await fetchJson(`${apiBase}/api/runs`));
    } catch {
      setRuns([]);
    }
  }

  async function selectRun(runId) {
    setError("");
    setActiveRunId(runId);
    try {
      setRunData(await fetchJson(`${apiBase}/api/pipeline/${runId}`));
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
      const response = await fetch(`${apiBase}/api/pipeline/run`, {
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
      setRunData(await fetchJson(`${apiBase}/api/pipeline/${payload.run_id}`));
      fetchRuns();
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h2>Single Document Pipeline</h2>
        <p className="muted">Upload and validate a single trade document manually.</p>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="pipeline-controls-grid">
        <section className="panel">
          <header><h3>Upload Document</h3></header>
          <UploadPanel onUpload={handleUpload} isSubmitting={isSubmitting} />
        </section>

        <section className="panel">
          <header><h3>Recent Runs</h3></header>
          <div className="recent-runs-flex">
            {runs.length === 0 ? (
              <p className="muted">No runs yet.</p>
            ) : (
              runs.map((run) => (
                <button
                  className={`run-chip ${run.run_id === activeRunId ? "active" : ""}`}
                  key={run.run_id}
                  onClick={() => void selectRun(run.run_id)}
                >
                  <span className="chip-customer">{run.customer_id}</span>
                  <span className="chip-status">{run.action || run.error || "processing"}</span>
                </button>
              ))
            )}
          </div>
        </section>
      </div>

      {activeRunId && (
        <div className="pipeline-results">
          <RouterDecision decision={runData?.decision} error={runData?.error} />
          <ExtractionView
            documentExtractions={runData?.document_extractions || []}
            fields={runData?.extraction || []}
          />
          <ValidationView results={runData?.validation || []} />
        </div>
      )}
    </div>
  );
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
