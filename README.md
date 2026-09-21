# DocuMind AI API

FastAPI backend for the existing DocuMind React UI.

## Run Locally

Start the backend:

```bash
cd /Users/sasitamda/Desktop/documind-ai-api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify it is running:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/dashboard/stats
```

The default database is SQLite at `data/documind.db` so the app can run immediately.

The React frontend should use:

```text
VITE_API_URL=http://127.0.0.1:8000
```

Allowed local frontend origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:5174`
- `http://127.0.0.1:5174`

## Use PostgreSQL

```bash
cd /Users/sasitamda/Desktop/documind-ai-api
cp .env.example .env
docker compose up -d postgres
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The `.env.example` file points to:

```text
postgresql://postgres:root123@localhost:5438/docmind-ai-db
```

## Gemini LLM

Set `GEMINI_API_KEY` in `.env` for LangChain/Gemini answers, summaries, and extraction:

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
```

The key is read only by the FastAPI backend and is never returned to the React frontend. Without a Gemini key, the backend still performs PDF extraction, chunking, embeddings, FAISS retrieval, and returns extractive fallback answers with source pages.

## Tests

```bash
.venv/bin/pytest
```

## Endpoints

- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{id}`
- `DELETE /api/documents/{id}`
- `POST /api/chat/ask`
- `GET /api/chat/{session_id}`
- `POST /api/documents/{id}/summary`
- `POST /api/documents/{id}/extract`
- `GET /api/dashboard/stats`
- `GET /health`
