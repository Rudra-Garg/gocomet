import { Search } from "lucide-react";
import { useState } from "react";

export default function QueryPanel({ apiBase, onNavigateToRun }) {
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
    <section className="panel query-panel-full">
      <form className="query-form" onSubmit={submit}>
        <div className="query-input-wrapper">
          <Search size={20} className="query-icon" />
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question about your documents..."
          />
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Querying..." : "Run Query"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <div className="query-result">
          <div className="query-meta">
            <pre className="sql-preview">{result.sql}</pre>
            <span className="badge clear">{result.rows.length} rows returned</span>
          </div>
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
                    className={isClickableRun ? "query-run-row" : ""}
                    key={index}
                    onClick={isClickableRun ? () => onNavigateToRun(runId) : undefined}
                  >
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex}>
                        {cellIndex === runIdColumnIndex && isClickableRun ? (
                          <button
                            className="query-run-link"
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              onNavigateToRun(runId);
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
