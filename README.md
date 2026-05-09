# Trade Document Validation

This repository contains a local document validation pipeline with a FastAPI backend, a SQLite persistence layer, a LangGraph pipeline, and a Vite React frontend.

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Gemini API key

## Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. The default model is `gemini-3.1-flash-lite`.

Run the backend:

```bash
uvicorn backend.main:app --reload
```

The API runs at `http://localhost:8000`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The UI runs at `http://localhost:5173` by default.

## Running the UI pipeline

1. Open the frontend.
2. Choose a customer. The included ruleset is `acme`.
3. Upload a `.pdf`, `.png`, `.jpg`, or `.jpeg` document.
4. Start the run.
5. Review extracted fields, validation results, and the routing decision.

The frontend polls `/api/pipeline/{run_id}` every two seconds until the run has an action or an error.

## Running natural-language queries

Use the query panel in the UI or call the API directly:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Show runs with mismatched fields"}'
```

The query layer asks Gemini to generate SQL, strips markdown fences, rejects non-`SELECT` statements, and returns the generated SQL, columns, and rows.

## Sample query and output

Question:

```text
Show runs with mismatched fields
```

Example response shape:

```json
{
  "sql": "SELECT DISTINCT p.run_id, p.customer_id, p.action FROM pipeline_runs p JOIN validation_results v ON p.run_id = v.run_id WHERE v.status = 'mismatch'",
  "columns": ["run_id", "customer_id", "action"],
  "rows": []
}
```

