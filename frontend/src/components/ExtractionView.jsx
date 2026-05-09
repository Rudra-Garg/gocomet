export default function ExtractionView({ extraction }) {
  const fields = extraction?.fields || [];

  return (
    <section className="panel">
      <header>
        <h2>Extracted fields</h2>
      </header>
      {fields.length === 0 ? (
        <p className="muted">Fields appear after a run completes extraction.</p>
      ) : (
        <div className="field-grid">
          {fields.map((field) => (
            <article className="field-card" key={field.name}>
              <div>
                <span className="label">{field.name}</span>
                <strong>{field.value || "Not found"}</strong>
              </div>
              <div className="confidence">
                <span>{Math.round(field.confidence * 100)}%</span>
                <div>
                  <i style={{ width: `${Math.round(field.confidence * 100)}%` }} />
                </div>
              </div>
              {field.source_text && <p>{field.source_text}</p>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

