import { Send, Upload } from "lucide-react";
import { useState } from "react";

const ACCEPTED_TYPES = ".pdf,.png,.jpg,.jpeg";

export default function UploadPanel({ onUpload, isSubmitting }) {
  const [file, setFile] = useState(null);
  const [customerId, setCustomerId] = useState("acme");

  function submit(event) {
    event.preventDefault();
    if (!file) {
      return;
    }
    onUpload({ file, customerId });
  }

  return (
    <form className="upload-panel" onSubmit={submit}>
      <label>
        Customer
        <select value={customerId} onChange={(event) => setCustomerId(event.target.value)}>
          <option value="acme">acme</option>
          <option value="globex">globex</option>
          <option value="initech">initech</option>
        </select>
      </label>

      <label className="file-input">
        <Upload size={18} />
        <span>{file ? file.name : "Choose document"}</span>
        <input
          accept={ACCEPTED_TYPES}
          type="file"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
      </label>

      <button type="submit" disabled={!file || isSubmitting}>
        <Send size={16} />
        {isSubmitting ? "Running" : "Run"}
      </button>
      {isSubmitting && <span className="spinner" aria-label="Pipeline is running" />}
    </form>
  );
}
