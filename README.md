# Agentic Research Assistant

> An LLM-powered research assistant for technical literature. Upload documents, ask questions, get grounded answers — backed by a ReAct agent, vector search, and persistent named knowledge bases.

---

## What It Does

The Agentic Research Assistant lets you build private knowledge bases from your own documents and chat with an AI that answers strictly from what those documents say. It combines a retrieval pipeline (your documents → vector embeddings → FAISS index) with an agentic reasoning loop (LangGraph ReAct) so the model searches before it speaks, cites what it finds, and refuses to guess when the answer isn’t there.

**Key capabilities:**
- Upload PDFs, Markdown, plain text, and HTML into named, persistent collections
- Ask natural-language questions; the agent retrieves the most relevant passages before answering
- Answers are grounded — the model is explicitly constrained to retrieved text only
- Every response shows which source file it drew from and the relevance score
- Web search (Tavily) available for explicitly external queries
- Conversation memory maintained per session (last 20 exchanges)
- Full REST API with auto-generated Swagger docs

---

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
│  LangGraph     │ │  FAISS       │ │  In-memory       │
│  ReAct Agent   │ │  (per-       │ │  session memory  │
│  (GPT-4o)      │ │  collection) │ │  (sliding window)│
└────────┬───────┘ └──────────────┘ └──────────────────┘
         │
    ┌────┴───────────────────┐
    │  Agent Tools           │
    │  • search_documents    │  ← FAISS vector search
    │  • web_search          │  ← Tavily API
    │  • extract_citations   │  ← Bibliography mining
    └────────────────────────┘
```

### How a query flows

1. User sends a message via the Streamlit UI
2. FastAPI receives the request, authenticates the API key, loads session history
3. The LangGraph agent calls `search_documents` → FAISS returns the top-k most semantically similar chunks
4. The agent reasons over the retrieved text and formulates an answer (or calls `web_search` if the user asks about something external)
5. The answer, source citations, and tool call list are returned to the UI
6. The exchange is appended to the in-memory session history

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Streamlit | Browser UI — no JavaScript required |
| Backend | FastAPI + Uvicorn | Async REST API with auto-generated docs |
| Agent | LangGraph `create_react_agent` | ReAct reasoning loop with tool use |
| LLM | OpenAI GPT-4o | Reasoning, grounding, answer generation |
| Embeddings | OpenAI `text-embedding-3-small` | Text → vector conversion for semantic search |
| Vector store | FAISS (local) | Fast similarity search, persisted per collection |
| Document parsing | pypdf, BeautifulSoup, lxml | PDF, HTML, TXT, Markdown ingestion |
| Web search | Tavily API | Clean summarised results for LLM consumption |
| Config | pydantic-settings | Typed `.env` loading with validation |
| Auth | FastAPI `APIKeyHeader` | Shared-secret protection on all endpoints |

---

## Project Structure

```
Research-Assistant/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, lifespan
│   ├── config.py                  # All settings via pydantic-settings + .env
│   ├── auth.py                    # X-API-Key dependency
│   ├── models/
│   │   └── schemas.py             # Pydantic request/response models
│   ├── services/
│   │   ├── document_processor.py  # Parse files → chunk → LangChain Documents
│   │   ├── vector_store.py        # FAISS index management per collection
│   │   ├── agent.py               # LangGraph agent + tool definitions
│   │   └── memory.py              # Thread-safe in-memory session store
│   └── routers/
│       ├── collections.py         # CRUD for knowledge base collections
│       ├── documents.py           # Upload, list, delete documents
│       └── chat.py                # Chat endpoint + session clear
├── frontend/
│   └── app.py                     # Streamlit UI
├── data/
│   └── collections/               # FAISS indexes + metadata (auto-created)
├── requirements.txt
├── .env.example
└── run.sh                         # Starts both services (Mac/Linux)
```

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com) with billing enabled
- A [Tavily API key](https://tavily.com) (free tier available)

### 2. Clone and install

```bash
git clone https://github.com/lihiniranaweera/Research-Assistant
cd Research-Assistant
git checkout claude/agentic-research-assistant-iI7Hx
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
API_KEY=any-secret-string-you-choose
```

### 4. Run

**Mac / Linux:**
```bash
chmod +x run.sh && ./run.sh
```

**Windows (two terminals):**
```powershell
# Terminal 1 — backend
python -m uvicorn backend.main:app --reload

# Terminal 2 — frontend
python -m streamlit run frontend/app.py
```

| Service | URL |
|---|---|
| Chat UI | http://localhost:8501 |
| API (Swagger docs) | http://localhost:8000/docs |

### 5. Use it

1. Open the UI at `http://localhost:8501`
2. Create a collection in the sidebar (e.g. `my-papers`)
3. Upload a document (PDF, TXT, MD, or HTML)
4. Ask a question in the chat — the agent retrieves relevant passages and answers from them

---

## API Reference

All endpoints require the header `X-API-Key: <your API_KEY>`.

### Collections

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/collections` | Create a named collection |
| `GET` | `/collections` | List all collections |
| `GET` | `/collections/{name}` | Get collection details and document list |
| `DELETE` | `/collections/{name}` | Delete a collection and its index |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/upload?collection=` | Upload and index a file |
| `GET` | `/documents?collection=` | List documents in a collection |
| `DELETE` | `/documents/{doc_id}?collection=` | Remove a document (rebuilds index) |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a message, get a grounded answer |
| `DELETE` | `/chat/sessions/{session_id}` | Clear a session's conversation history |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |

#### Example chat request

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123",
    "collection": "my-papers",
    "message": "What methodology does the paper use?"
  }'
```

#### Example chat response

```json
{
  "session_id": "abc-123",
  "answer": "According to paper.pdf, the authors use a transformer-based architecture...",
  "sources": [
    {
      "filename": "paper.pdf",
      "page_content": "We propose a transformer-based...",
      "score": 0.891
    }
  ],
  "tool_calls_made": ["search_documents"]
}
```

---

## Configuration Reference

All values can be overridden in `.env`. The backend reads them at startup via pydantic-settings.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. OpenAI API key |
| `TAVILY_API_KEY` | — | Required. Tavily search API key |
| `API_KEY` | `dev-secret` | Shared secret for all API endpoints |
| `LLM_MODEL` | `gpt-4o` | OpenAI chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `DATA_DIR` | `data/collections` | Directory for FAISS indexes |
| `CHUNK_SIZE` | `400` | Characters per document chunk |
| `CHUNK_OVERLAP` | `80` | Overlap between consecutive chunks |
| `MAX_RETRIEVAL_DOCS` | `12` | Top-k chunks retrieved per query |
| `AGENT_MAX_ITERATIONS` | `10` | Max agent reasoning steps per query |

---

## Design Decisions

**Why FAISS instead of a managed vector DB?**
FAISS runs entirely locally with no external service, API key, or network dependency. For a single-user research tool this is simpler, faster to set up, and free. The tradeoff is that it doesn’t support distributed access or real-time sync — a managed DB like Pinecone would be the right call for a multi-user production deployment.

**Why named collections instead of a single index?**
Different research projects shouldn’t bleed into each other. A question about your ML papers shouldn’t pull in chunks from your legal documents. Collections give you isolation with near-zero overhead.

**Why chunk at 400 characters with 80 overlap?**
Smaller chunks mean each retrieved unit contains a single discrete fact rather than a whole section. This improves retrieval precision — especially for structured documents like resumes, reports, and technical specs where a specific claim might occupy just one sentence. Overlap prevents facts that straddle a chunk boundary from being unretrievable.

**Why k=12?**
With 400-character chunks, individual chunks are small. Retrieving 12 of them gives the agent ~4,800 characters of context — enough to cover a question that touches multiple parts of a document — without blowing the GPT-4o context window.

**Why a strict grounding system prompt?**
LLMs default to being helpful, which often means filling gaps with plausible-sounding hallucinations. Explicit rules (“answer ONLY from retrieved text”, “say exactly this phrase if not found”) override that tendency more reliably than soft suggestions like “try to stick to the documents.”
