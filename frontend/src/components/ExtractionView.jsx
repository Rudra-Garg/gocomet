export default function ExtractionView({ fields }) {
  return (
    <section className="panel">
      <header>
        <h2>Extracted fields</h2>
      </header>
      {fields.length === 0 ? (
        <p className="muted">Fields appear after a run completes extraction.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Field</th>
              <th>Extracted Value</th>
              <th>Confidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.field_name}>
                <td>{field.field_name}</td>
                <td>{field.value || "Not found"}</td>
                <td>
                  <div className="confidence compact">
                    <span>{Math.round(field.confidence * 100)}%</span>
                    <div>
                      <i
                        className={confidenceClass(field.confidence)}
                        style={{ width: `${Math.round(field.confidence * 100)}%` }}
                      />
                    </div>
                  </div>
                </td>
                <td>
                  {field.uncertain ? (
                    <span className="badge uncertain">UNCERTAIN</span>
                  ) : (
                    <span className="badge clear">OK</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function confidenceClass(confidence) {
  if (confidence >= 0.8) {
    return "high";
  }
  if (confidence >= 0.5) {
    return "medium";
  }
  return "low";
}
