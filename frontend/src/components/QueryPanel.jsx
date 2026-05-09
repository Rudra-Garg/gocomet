import { Search } from "lucide-react";
import { useState } from "react";

export default function QueryPanel({ apiBase }) {
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
              {result.rows.map((row, index) => (
                <tr key={index}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex}>{String(cell ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

