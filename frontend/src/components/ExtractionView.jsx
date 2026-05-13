export default function ExtractionView({ fields, documentExtractions = [] }) {
  const byField = groupDocumentExtractions(documentExtractions);
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
              <th>From Files</th>
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
                  {byField[field.field_name]?.length ? (
                    <div className="extraction-file-list">
                      {byField[field.field_name].map((item) => (
                        <div className="extraction-file-item" key={item.filename}>
                          <strong>{item.filename}</strong>
                          <span>
                            {item.value || "Not found"} · {Math.round(item.confidence * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    "No per-file extraction"
                  )}
                </td>
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

function groupDocumentExtractions(documentExtractions) {
  const grouped = {};
  for (const document of documentExtractions) {
    for (const field of document.fields || []) {
      if (!grouped[field.field_name]) {
        grouped[field.field_name] = [];
      }
      grouped[field.field_name].push({
        filename: document.filename,
        value: field.value,
        confidence: field.confidence,
      });
    }
  }
  return grouped;
}
