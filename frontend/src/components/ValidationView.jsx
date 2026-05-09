const STATUS_LABELS = {
  match: "✓ Match",
  mismatch: "✕ Mismatch",
  uncertain: "— Uncertain",
};

export default function ValidationView({ results }) {
  return (
    <section className="panel">
      <header>
        <h2>Validation</h2>
      </header>
      {results.length === 0 ? (
        <p className="muted">Validation results appear after extraction.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Field</th>
              <th>Status</th>
              <th>Found</th>
              <th>Expected</th>
            </tr>
          </thead>
          <tbody>
            {results.map((item) => (
              <tr className={`validation-status ${item.status}`} key={item.field_name}>
                <td>{item.field_name}</td>
                <td>{STATUS_LABELS[item.status] || item.status}</td>
                <td>{item.found || "None"}</td>
                <td>{item.expected || "None"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
