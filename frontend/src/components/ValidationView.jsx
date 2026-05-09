const STATUS_LABELS = {
  match: "Match",
  mismatch: "Mismatch",
  uncertain: "Uncertain",
  no_rule: "No rule",
};

export default function ValidationView({ validation }) {
  const items = validation?.items || [];

  return (
    <section className="panel">
      <header>
        <h2>Validation</h2>
      </header>
      {items.length === 0 ? (
        <p className="muted">Validation results appear after extraction.</p>
      ) : (
        <div className="validation-list">
          {items.map((item) => (
            <article className={`validation-row ${item.status}`} key={item.field}>
              <span>{item.field}</span>
              <strong>{STATUS_LABELS[item.status] || item.status}</strong>
              <div>
                <small>Expected</small>
                <p>{item.expected || "None"}</p>
              </div>
              <div>
                <small>Actual</small>
                <p>{item.actual || "None"}</p>
              </div>
              <p>{item.message}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

