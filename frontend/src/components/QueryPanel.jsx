import { Search } from "lucide-react";
import { useState } from "react";

export default function QueryPanel({ activeRunId, apiBase, onRunSelect }) {
  const [question, setQuestion] = useState("Show runs with mismatched fields");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const response = await fetch(`${apiBase}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setResult(await response.json());
    } catch (queryError) {
      setError(queryError.message);
    } finally {
      setIsLoading(false);
    }
  }

  const runIdColumnIndex = result?.columns.indexOf("run_id") ?? -1;

  return (
    <section className="panel">
      <header>
        <h2>Natural language query</h2>
      </header>
      <form className="query-form" onSubmit={submit}>
        <input value={question} onChange={(event) => setQuestion(event.target.value)} />
        <button type="submit" disabled={isLoading}>
          <Search size={16} />
          Query
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
      {result && (
        <div className="query-result">
          <pre>{result.sql}</pre>
          <table>
            <thead>
              <tr>
                {result.columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, index) => {
                const runId = runIdColumnIndex >= 0 ? row[runIdColumnIndex] : null;
                const isClickableRun = typeof runId === "string" && runId.length > 0;

                return (
                  <tr
                    className={[
                      isClickableRun ? "query-run-row" : "",
                      runId === activeRunId ? "active" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={index}
                    onClick={isClickableRun ? () => void onRunSelect(runId) : undefined}
                    tabIndex={isClickableRun ? 0 : undefined}
                    onKeyDown={
                      isClickableRun
                        ? (event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              void onRunSelect(runId);
                            }
                          }
                        : undefined
                    }
                  >
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex}>
                        {cellIndex === runIdColumnIndex && isClickableRun ? (
                          <button
                            className="query-run-link"
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void onRunSelect(runId);
                            }}
                          >
                            {runId}
                          </button>
                        ) : (
                          String(cell ?? "")
                        )}
                      </td>
                    ))}
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
