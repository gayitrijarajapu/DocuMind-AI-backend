# DocuMind AI API

FastAPI backend for the existing DocuMind React UI.

## Run Locally

```bash
cd /Users/sasitamda/Desktop/documind-ai-api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The default database is SQLite at `data/documind.db` so the app can run immediately.

## Use PostgreSQL

```bash
cd /Users/sasitamda/Desktop/documind-ai-api
cp .env.example .env
docker compose up -d postgres
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The `.env.example` file points to:

```text
postgresql+psycopg2://postgres:postgres@localhost:5432/documind
```

## LLM Behavior

Set `OPENAI_API_KEY` in `.env` for LangChain/OpenAI answers. Without a key, the backend still performs PDF extraction, chunking, embeddings, FAISS retrieval, and returns an extractive answer with source pages.

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
