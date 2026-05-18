# Agentic Research Assistant

An LLM-powered research assistant for technical literature, built with FastAPI, LangChain, OpenAI GPT-4o, FAISS, and Streamlit.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Streamlit UI  (port 8501)                                       │
│  • Collection management  • Document upload  • Chat interface    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP + X-API-Key
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend  (port 8000)                                    │
│  /collections  /documents  /chat                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
┌────────▼───────┐ ┌───────▼──────┐ ┌────────▼────────┐
│  LangChain     │ │  FAISS       │ │  In-memory       │
│  OpenAI-Tools  │ │  (per-       │ │  session memory  │
│  Agent         │ │  collection) │ │                  │
└────────┬───────┘ └──────────────┘ └─────────────────┘
         │
    ┌────┴──────────────┐
    │  Tools            │
    │  • search_docs    │  ← RAG over FAISS
    │  • web_search     │  ← Tavily API
    │  • extract_cites  │  ← Citation mining
    └───────────────────┘
```

## Features

- **Named collections** — create isolated knowledge bases per topic
- **Multi-format ingestion** — PDF, TXT, Markdown, HTML
- **FAISS vector search** — local, persistent, per-collection
- **Agentic reasoning** — ReAct loop with OpenAI function calling
- **Web search** — Tavily integration for out-of-document queries
- **Citation extraction** — mines bibliographic entries from documents
- **Conversation memory** — per-session sliding window (in-memory)
- **API key auth** — all endpoints protected via `X-API-Key` header
- **Auto-generated API docs** — FastAPI Swagger UI at `/docs`

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   OPENAI_API_KEY
#   TAVILY_API_KEY   (free at https://tavily.com)
#   API_KEY          (any secret string)
```

### 3. Run

```bash
chmod +x run.sh
./run.sh
```

Or start services individually:

```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload

# Terminal 2 — frontend
streamlit run frontend/app.py
```

Open **http://localhost:8501** for the UI, or **http://localhost:8000/docs** for the API.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/collections` | Create a collection |
| `GET` | `/collections` | List all collections |
| `GET` | `/collections/{name}` | Collection details |
| `DELETE` | `/collections/{name}` | Delete a collection |
| `POST` | `/documents/upload?collection=` | Upload & index a file |
| `GET` | `/documents?collection=` | List documents |
| `DELETE` | `/documents/{doc_id}?collection=` | Remove a document |
| `POST` | `/chat` | Send a message |
| `DELETE` | `/chat/sessions/{session_id}` | Clear session memory |

All requests require the `X-API-Key` header.

## Project Structure

```
Research-Assistant/
├── backend/
│   ├── main.py                    # FastAPI app + CORS + lifespan
│   ├── config.py                  # Settings (pydantic-settings + .env)
│   ├── auth.py                    # API key dependency
│   ├── models/schemas.py          # Pydantic request/response models
│   ├── services/
│   │   ├── document_processor.py  # PDF/HTML/TXT/MD → chunks
│   │   ├── vector_store.py        # FAISS collection manager
│   │   ├── agent.py               # LangGraph agent factory + tools
│   │   └── memory.py              # In-memory session history
│   └── routers/
│       ├── collections.py
│       ├── documents.py
│       └── chat.py
├── frontend/
│   └── app.py                     # Streamlit UI
├── data/collections/              # FAISS indexes (auto-created)
├── requirements.txt
├── .env.example
└── run.sh
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required |
| `TAVILY_API_KEY` | — | Required for web search |
| `API_KEY` | `dev-secret` | Shared secret for API auth |
| `LLM_MODEL` | `gpt-4o` | OpenAI chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `DATA_DIR` | `data/collections` | FAISS storage path |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `MAX_RETRIEVAL_DOCS` | `6` | Top-k docs per RAG query |
