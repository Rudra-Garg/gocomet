# Trade Document Validation

Local multi-agent trade document validation pipeline with a FastAPI backend, LangGraph orchestration, SQLite persistence, a natural-language query layer, and a Vite React frontend.

## Prerequisites

- Python 3.11+
- Node.js 18+
- uv
- A Gemini API key
- Docker and Docker Compose, for the containerized local setup

## Docker Compose Setup

Create a local environment file and set `GEMINI_API_KEY`:

```bash
cp .env.example .env
```

Start the backend and frontend together:

```bash
docker compose up --build
```

The backend is available from the host at `http://localhost:8123`. Inside the Docker network, the FastAPI container still listens on port `8000`.

The frontend is available at `http://localhost:5173` and is configured with `VITE_API_BASE=http://localhost:8123`, so browser requests go to `http://localhost:8123/api/...`.

The compose setup mounts the source tree for hot reload. Dependencies stay container-managed: Python packages live in the backend image virtual environment, and frontend packages live in the `frontend_node_modules` Docker volume.

## Manual Backend Setup

```bash
uv sync
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. The default model is `gemini-3.1-flash-lite`. Langfuse keys are optional; local runs work without them.

Run the backend:

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

The API runs at `http://localhost:8000` when started manually.

## Manual Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The UI runs at `http://localhost:5173` by default.

## Pipeline API

`POST /api/pipeline/run` accepts multipart form data:

- `file`: `.pdf`, `.png`, `.jpg`, or `.jpeg`
- `customer_id`: for example `abc`

Response:

```json
{
  "run_id": "uuid",
  "status": "complete",
  "error": null
}
```

`GET /api/pipeline/{run_id}` returns the persisted state:

```json
{
  "run_id": "uuid",
  "customer_id": "abc",
  "document_name": "invoice.pdf",
  "action": "auto_approve",
  "extraction": [
    {"field_name": "incoterms", "value": "FOB", "confidence": 0.97, "uncertain": false}
  ],
  "validation": [
    {"field_name": "incoterms", "status": "match", "found": "FOB", "expected": "FOB", "rule_ref": "incoterms"}
  ],
  "decision": {
    "action": "auto_approve",
    "reasoning": "All configured rules match.",
    "amendment_email": null
  }
}
```

`GET /api/runs` returns the latest 20 rows from `pipeline_runs`.

## Running The UI Pipeline

1. Open the frontend.
2. Choose customer `abc imports`.
3. Upload a trade document.
4. Start the run.
5. Review extracted fields, validation results, the router decision, and any draft amendment email.

## Natural-Language Query

Use the query panel in the UI or call the API directly:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"what fields failed most often?"}'
```

For Docker Compose, use `http://localhost:8123/api/query`.

The query layer asks Gemini for one SQLite `SELECT`, strips markdown fences, rejects non-`SELECT` and multi-statement SQL, and returns:

```json
{
  "sql": "SELECT field_name, COUNT(*) as failures FROM validation_results WHERE status = 'mismatch' GROUP BY field_name ORDER BY failures DESC",
  "columns": ["field_name", "failures"],
  "rows": []
}
```

## Data Shape

The extractor returns fixed fields: `invoice_number`, `consignee_name`, `hs_code`, `port_of_loading`, `port_of_discharge`, `incoterms`, `description_of_goods`, and `gross_weight`. Confidence below `0.5` marks a field uncertain. Validation is pure Python: uncertain fields block approval, mismatches draft an amendment, and clean runs auto-approve.

SQLite tables:

- `pipeline_runs(run_id, customer_id, document_name, action, has_mismatches, has_uncertain, created_at)`
- `extraction_fields(id, run_id, field_name, value, confidence, uncertain)`
- `validation_results(id, run_id, field_name, status, found, expected, rule_ref)`
- `router_decisions(run_id, action, reasoning, amendment_email, created_at)`

## Tests

```bash
docker compose config
uv run pytest
python -m compileall backend
npm --prefix frontend run build
```
