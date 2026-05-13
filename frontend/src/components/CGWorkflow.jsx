import { ArrowLeft, MailCheck, Play, Send } from "lucide-react";
import { useEffect, useState } from "react";

import ExtractionView from "./ExtractionView.jsx";
import ValidationView from "./ValidationView.jsx";

const STAGES = ["incoming", "verification", "discrepancy", "draft_reply"];

export default function CGWorkflow({ apiBase, onRunSelect }) {
  const [stage, setStage] = useState("incoming");
  const [inbox, setInbox] = useState([]);
  const [customerId, setCustomerId] = useState("acme");
  const [filenames, setFilenames] = useState("");
  const [runId, setRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [emailMeta, setEmailMeta] = useState(null);
  const [selectedConflict, setSelectedConflict] = useState(null);
  const [draft, setDraft] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const originalDraft = runData?.decision?.amendment_email || "";
  const extractionFields = runData?.extraction || [];
  const validationResults = (runData?.validation || []).filter(
    (item) => item.rule_ref !== "cross_doc_conflict",
  );
  const discrepancyItems = [
    ...validationResults.filter((item) => item.status === "mismatch"),
    ...(runData?.cross_validation || []).filter((item) => item.status === "conflict"),
  ].map((item) => ({
    ...item,
    source_snippet: getSnippetForField(item.field_name, extractionFields),
  }));
  const hasDiscrepancies = discrepancyItems.length > 0;

  useEffect(() => {
    void fetchInbox();
  }, [apiBase]);

  useEffect(() => {
    if (!runId || runData?.action || runData?.error) {
      return undefined;
    }

    const poll = async () => {
      try {
        const nextRun = await fetchJson(`${apiBase}/api/pipeline/${runId}`);
        setRunData(nextRun);
        if (nextRun.action || nextRun.error) {
          setStage("verification");
          void loadEmail(runId);
        }
      } catch (pollError) {
        setError(pollError.message);
      }
    };

    void poll();
    const intervalId = window.setInterval(poll, 2000);
    return () => window.clearInterval(intervalId);
  }, [apiBase, runId, runData?.action, runData?.error]);

  useEffect(() => {
    setDraft(originalDraft);
    setSent(false);
  }, [originalDraft]);

  async function loadEmail(nextRunId) {
    try {
      setEmailMeta(await fetchJson(`${apiBase}/api/shipments/${nextRunId}/email`));
    } catch {
      setEmailMeta(null);
    }
  }

  async function fetchInbox() {
    try {
      setInbox(await fetchJson(`${apiBase}/api/inbox`));
    } catch {
      setInbox([]);
    }
  }

  async function openInboxRun(nextRunId) {
    setError("");
    setRunId(nextRunId);
    setSelectedConflict(null);
    setStage("verification");
    onRunSelect?.(nextRunId);
    try {
      setRunData(await fetchJson(`${apiBase}/api/pipeline/${nextRunId}`));
      void loadEmail(nextRunId);
    } catch (openError) {
      setRunData(null);
      setError(openError.message);
    }
  }

  async function simulateIncomingEmail(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    setRunData(null);
    setSelectedConflict(null);
    try {
      const payload = await postJson(`${apiBase}/api/trigger/simulate`, {
        customer_id: customerId,
        filenames: filenames
          .split(",")
          .map((name) => name.trim())
          .filter(Boolean),
      });
      setRunId(payload.run_id);
      setStage("verification");
      onRunSelect?.(payload.run_id);
      void fetchInbox();
    } catch (simulateError) {
      setError(simulateError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function sendReply() {
    setError("");
    setIsSubmitting(true);
    try {
      const payload = await postJson(`${apiBase}/api/shipments/${runId}/send-reply`, {
        body: draft,
      });
      setSent(payload.sent);
    } catch (sendError) {
      setError(sendError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function openConflict(conflict) {
    setSelectedConflict({
      ...conflict,
      source_snippet: getSnippetForField(conflict.field_name, extractionFields),
    });
    setStage("discrepancy");
  }

  function openDiscrepancyStage() {
    setStage("discrepancy");
  }

  function navigateStage(nextStage) {
    if (nextStage === "discrepancy") {
      openDiscrepancyStage();
      return;
    }
    setStage(nextStage);
  }

  return (
    <section className="content">
      {error && <div className="error-banner">{error}</div>}
      <section className="panel">
        <header style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <h2>CG Workflow</h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {STAGES.map((item) => (
              <button
                className={item === stage ? "badge clear" : "badge uncertain"}
                disabled={item === "discrepancy" && !hasDiscrepancies}
                key={item}
                onClick={() => navigateStage(item)}
                type="button"
              >
                {item.replace("_", " ")}
              </button>
            ))}
          </div>
        </header>

        {stage === "incoming" && (
          <div className="upload-panel">
            <form className="upload-panel" onSubmit={simulateIncomingEmail}>
              <label>
                Customer
                <select
                  value={customerId}
                  onChange={(event) => setCustomerId(event.target.value)}
                >
                  <option value="acme">acme</option>
                  <option value="abc">abc</option>
                </select>
              </label>
              <label>
                Sample document filenames
                <input
                  value={filenames}
                  onChange={(event) => setFilenames(event.target.value)}
                  placeholder="invoice.pdf, packing-list.pdf"
                />
              </label>
              <button disabled={isSubmitting || !filenames.trim()} type="submit">
                <Play size={18} />
                Simulate incoming email
              </button>
            </form>

            <section>
              <header>
                <h2>Inbox Queue</h2>
              </header>
              {inbox.length === 0 ? (
                <p className="muted">No shipment emails in the queue.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Received</th>
                      <th>Sender</th>
                      <th>Subject</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inbox.map((item) => (
                      <tr
                        className="query-run-row"
                        key={item.run_id}
                        onClick={() => void openInboxRun(item.run_id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            void openInboxRun(item.run_id);
                          }
                        }}
                        role="button"
                        tabIndex={0}
                      >
                        <td>{formatReceived(item.received_at)}</td>
                        <td>{item.sender || "Unknown"}</td>
                        <td>{item.subject || "No subject"}</td>
                        <td>{formatInboxStatus(item)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>
        )}

        {stage !== "incoming" && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            <button onClick={() => setStage("incoming")} type="button">
              <ArrowLeft size={18} />
              Incoming
            </button>
            <button onClick={() => setStage("verification")} type="button">
              Verification
            </button>
            <button
              disabled={!hasDiscrepancies}
              onClick={openDiscrepancyStage}
              type="button"
            >
              Discrepancy
            </button>
            <button
              disabled={!runData?.decision}
              onClick={() => setStage("draft_reply")}
              type="button"
            >
              Draft reply
            </button>
          </div>
        )}
      </section>

      {stage === "verification" && (
        <>
          <section className="panel">
            <header>
              <h2>Shipment documents</h2>
            </header>
            {!runData ? (
              <p className="muted">Waiting for extraction and validation.</p>
            ) : (
              <>
                <p className="muted">
                  Run {runData.run_id} · {runData.action || "processing"}
                </p>
                {(runData.documents || []).length > 0 && (
                  <table>
                    <thead>
                      <tr>
                        <th>Index</th>
                        <th>Filename</th>
                        <th>Type</th>
                        <th>Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runData.documents.map((document) => (
                        <tr key={`${document.attachment_index}-${document.filename}`}>
                          <td>{document.attachment_index + 1}</td>
                          <td>{document.filename}</td>
                          <td>{document.mime}</td>
                          <td>{document.size} bytes</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </section>
          <ExtractionView
            documentExtractions={runData?.document_extractions || []}
            fields={runData?.extraction || []}
          />
          <ValidationView results={validationResults} onConflict={openConflict} />
          <CrossValidationTable results={runData?.cross_validation || []} onConflict={openConflict} />
        </>
      )}

      {stage === "discrepancy" && (
        <section className="panel">
          <header>
            <h2>Discrepancy detail</h2>
          </header>
          {discrepancyItems.length > 0 ? (
            <>
              <DiscrepancyList
                items={prioritizeSelectedDiscrepancy(discrepancyItems, selectedConflict)}
              />
              <button onClick={() => setStage("draft_reply")} type="button">
                <MailCheck size={18} />
                Review draft reply
              </button>
            </>
          ) : (
            <p className="muted">Select a conflict from verification.</p>
          )}
        </section>
      )}

      {stage === "draft_reply" && (
        <section className="panel">
          <header>
            <h2>Draft reply</h2>
          </header>
          {!originalDraft ? (
            <>
              <p className="muted">No amendment required.</p>
              <button onClick={() => setStage("verification")} type="button">
                Back to verification
              </button>
            </>
          ) : (
            <>
              <p className="muted">
                To {emailMeta?.reply_to || "stored shipment contact"} ·{" "}
                {emailMeta?.subject || "shipment email"}
              </p>
              <label className="email-review">
                Reply body
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  rows={10}
                />
              </label>
              <button
                disabled={isSubmitting || draft === originalDraft || sent}
                onClick={sendReply}
                type="button"
              >
                <Send size={18} />
                {sent ? "Sent" : "Send reply"}
              </button>
              {sent && <p className="muted">Reply sent and recorded.</p>}
            </>
          )}
        </section>
      )}
    </section>
  );
}

function CrossValidationTable({ results, onConflict }) {
  return (
    <section className="panel">
      <header>
        <h2>Cross-document validation</h2>
      </header>
      {results.length === 0 ? (
        <p className="muted">Cross-document checks appear after shipment ingestion.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Field</th>
              <th>Verdict</th>
              <th>Actual values</th>
            </tr>
          </thead>
          <tbody>
            {results.map((item) => (
              <tr key={item.field_name}>
                <td>{item.field_name}</td>
                <td>
                  {item.status === "conflict" ? (
                    <button
                      className="query-run-link"
                      onClick={() => onConflict(item)}
                      type="button"
                    >
                      <span className="badge uncertain">Conflict</span>
                    </button>
                  ) : (
                    <span className="badge clear">Consistent</span>
                  )}
                </td>
                <td>
                  <ValueList values={item.values} emptyLabel="No confident values" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function DiscrepancyList({ items }) {
  return (
    <div className="discrepancy-list">
      {items.map((item, index) => (
        <article
          className="discrepancy-item"
          key={`${item.field_name}-${item.rule_ref || item.status}-${index}`}
        >
          <header>
            <h3>{item.field_name}</h3>
            <span className="badge uncertain">
              {item.status === "conflict" ? "Cross-document conflict" : "Rule mismatch"}
            </span>
          </header>
          <p className="muted">
            {item.message || "The extracted value does not match the configured customer rule."}
          </p>
          {item.values ? (
            <ValueTable values={item.values} />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Found in Document</th>
                  <th>Expected per Customer Rule</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{formatCellValue(item.found, "None")}</td>
                  <td>{formatCellValue(item.expected, "None")}</td>
                </tr>
              </tbody>
            </table>
          )}
          {item.source_snippet && (
            <blockquote className="source-snippet">{item.source_snippet}</blockquote>
          )}
        </article>
      ))}
    </div>
  );
}

function ValueTable({ values }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Document</th>
          <th>Actual Value</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(values || {}).map(([document, value]) => (
          <tr key={document}>
            <td>{document}</td>
            <td>{formatCellValue(value, "None")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ValueList({ values, emptyLabel }) {
  const entries = Object.entries(values || {});
  if (entries.length === 0) {
    return emptyLabel;
  }
  return (
    <div className="value-list">
      {entries.map(([document, value]) => (
        <div key={document}>
          <strong>{document}:</strong> {formatCellValue(value, "None")}
        </div>
      ))}
    </div>
  );
}

function prioritizeSelectedDiscrepancy(items, selectedConflict) {
  if (!selectedConflict) {
    return items;
  }
  const selectedIndex = items.findIndex((item) =>
    isSameDiscrepancy(item, selectedConflict),
  );
  if (selectedIndex < 1) {
    return items;
  }
  return [
    items[selectedIndex],
    ...items.slice(0, selectedIndex),
    ...items.slice(selectedIndex + 1),
  ];
}

function getSnippetForField(fieldName, extractionFields) {
  return (
    extractionFields.find((field) => field.field_name === fieldName)?.source_snippet ||
    null
  );
}

function isSameDiscrepancy(item, selectedConflict) {
  return (
    item.field_name === selectedConflict.field_name &&
    (item.rule_ref || "") === (selectedConflict.rule_ref || "") &&
    item.status === selectedConflict.status
  );
}

function formatCellValue(value, fallback) {
  return value === undefined || value === null || value === "" ? fallback : String(value);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function formatInboxStatus(item) {
  if (!item.action) {
    return "processing";
  }
  if (item.has_uncertain) {
    return `${item.action} · uncertain`;
  }
  if (item.has_mismatches) {
    return `${item.action} · mismatches`;
  }
  return item.action;
}

function formatReceived(value) {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
