# arXiv Paper Curator - Production RAG System

## Project Overview

**Project Name**: arXiv Paper Curator (Part of "The Mother of AI Project")  
**Type**: Production-grade Retrieval-Augmented Generation (RAG) system  
**Purpose**: Educational course project teaching modern AI engineering through building a complete research assistant that fetches academic papers, understands content, and answers research questions using advanced RAG techniques.

**Core Philosophy**: Build RAG systems the professional way - solid keyword search foundations (BM25) first, then enhance with semantic vector search for hybrid retrieval. This mimics how successful companies build production systems.

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│  • Gradio Web UI (localhost:7861)                              │
│  • Telegram Bot (mobile access)                                │
│  • FastAPI REST endpoints (localhost:8000/docs)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Agentic RAG System                          │
│  LangGraph workflow with intelligent decision-making:           │
│  • Guardrail validation (out-of-domain detection)              │
│  • Adaptive retrieval strategies                               │
│  • Document relevance grading                                  │
│  • Query rewriting when results insufficient                   │
│  • Answer generation with streaming                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Search & Retrieval                         │
│  • OpenSearch 2.19 (hybrid search engine)                      │
│    - BM25 keyword search                                       │
│    - Vector semantic search (k-NN)                             │
│    - Hybrid scoring with RRF (Reciprocal Rank Fusion)          │
│  • Jina Embeddings API (text-to-vector)                        │
│  • Redis cache (performance optimization)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Data Pipeline                              │
│  • Apache Airflow 3.0 (workflow orchestration)                 │
│  • arXiv API integration (paper fetching)                      │
│  • Docling (PDF parsing & chunking)                            │
│  • PostgreSQL 16 (metadata storage)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LLM & Monitoring                             │
│  • Ollama (local LLM server - llama3.2:1b default)             │
│  • Langfuse (tracing & monitoring)                             │
└─────────────────────────────────────────────────────────────────┘
```

### Infrastructure Services (Docker Compose)

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| FastAPI | rag-api | 8000 | REST API, async endpoints, health checks |
| PostgreSQL | rag-postgres | 5432 | Paper metadata storage |
| OpenSearch | rag-opensearch | 9200 | Hybrid search engine (BM25 + vector) |
| OpenSearch Dashboards | rag-dashboards | 5601 | Search engine UI |
| Ollama | rag-ollama | 11434 | Local LLM inference |
| Airflow | rag-airflow | 8080 | Workflow orchestration |
| Langfuse | langfuse-web | 3000 | Observability & tracing |
| Redis | rag-redis | 6379 | Response caching |
| Gradio | Launched via CLI | 7861 | User-friendly chat interface |

## Project Structure

### Source Code Organization (`src/`)

```
src/
├── main.py                    # FastAPI app entry point, lifespan management
├── gradio_app.py             # Gradio web UI for chat interface
├── config.py                 # Pydantic settings from .env
├── database.py               # SQLAlchemy base
├── dependencies.py           # FastAPI dependency injection
├── exceptions.py             # Custom exceptions
├── middlewares.py            # Request/response middlewares
│
├── db/                       # Database layer
│   ├── factory.py           # Database connection factory
│   └── interfaces/          # Database interfaces
│       ├── base.py          # Base repository interface
│       └── postgresql.py    # PostgreSQL implementation
│
├── models/                   # SQLAlchemy ORM models
│   └── paper.py             # Paper metadata model
│
├── repositories/             # Data access layer
│   └── paper.py             # Paper CRUD operations
│
├── routers/                  # FastAPI route handlers
│   ├── ping.py              # Health check endpoint
│   ├── ask.py               # Non-agentic RAG endpoints
│   ├── agentic_ask.py       # Agentic RAG endpoints (Week 7)
│   └── hybrid_search.py     # Hybrid search endpoints
│
├── schemas/                  # Pydantic models for validation
│   ├── api/                 # API request/response schemas
│   ├── arxiv/               # arXiv paper schemas
│   ├── database/            # Database config schemas
│   ├── embeddings/          # Jina embeddings schemas
│   ├── indexing/            # OpenSearch indexing schemas
│   ├── pdf_parser/          # Docling parser schemas
│   ├── telegram/            # Telegram bot schemas
│   └── ollama.py            # Ollama LLM schemas
│
└── services/                 # Business logic layer
    ├── agents/              # Agentic RAG implementation (Week 7)
    │   ├── agentic_rag.py  # Main AgenticRAGService class
    │   ├── config.py        # Graph configuration
    │   ├── context.py       # LangGraph runtime context
    │   ├── factory.py       # Agent service factory
    │   ├── models.py        # Agent data models
    │   ├── nodes.py         # LangGraph node implementations
    │   ├── prompts.py       # System prompts for agents
    │   ├── state.py         # Agent state management
    │   └── tools.py         # LangChain retrieval tools
    │
    ├── arxiv/               # arXiv API integration
    ├── cache/               # Redis caching service
    ├── embeddings/          # Jina embeddings client
    ├── indexing/            # OpenSearch indexing
    ├── langfuse/            # Tracing and monitoring
    ├── ollama/              # LLM client (Ollama)
    ├── opensearch/          # Search client (hybrid search)
    ├── pdf_parser/          # Docling PDF parsing
    ├── telegram/            # Telegram bot service
    └── metadata_fetcher.py  # Paper metadata extraction
```

### Data Pipeline (`airflow/`)

```
airflow/
├── Dockerfile               # Airflow container build
├── entrypoint.sh           # Container startup script
├── requirements-airflow.txt # Airflow-specific dependencies
└── dags/
    ├── arxiv_paper_ingestion.py  # Main DAG definition
    └── arxiv_ingestion/          # Modular task implementations
        ├── common.py             # Shared utilities
        ├── fetching.py           # arXiv API fetching
        ├── indexing.py           # Hybrid search indexing
        ├── reporting.py          # Daily ingestion reports
        └── setup.py              # Environment setup
```

**DAG Schedule**: Monday-Friday at 6 AM UTC  
**Pipeline Flow**: `setup → fetch_papers → index_hybrid → report → cleanup`

### Notebooks (`notebooks/`)

Week-by-week learning progression with hands-on implementation:
- **Week 1**: Infrastructure setup & verification
- **Week 2**: arXiv integration & data ingestion
- **Week 3**: OpenSearch & BM25 retrieval
- **Week 4**: Chunking strategies & hybrid search
- **Week 5**: Complete RAG system with streaming
- **Week 6**: Production monitoring & caching
- **Week 7**: Agentic RAG with LangGraph

## Core Technologies

### Backend Framework
- **FastAPI 0.115+**: Modern async Python web framework
- **Uvicorn**: ASGI server with WebSocket support
- **Pydantic 2.11+**: Data validation and settings management
- **SQLAlchemy 2.0**: ORM for PostgreSQL

### Data Pipeline
- **Apache Airflow 3.0**: Workflow orchestration
- **Docling 2.43+**: PDF parsing with intelligent chunking
- **arxiv-py**: arXiv API Python wrapper

### Search & Embeddings
- **OpenSearch 2.19**: Hybrid search (BM25 + k-NN)
- **Jina Embeddings API**: Text-to-vector embeddings
- **sentence-transformers**: Local embedding models

### LLM & Agents
- **Ollama**: Local LLM inference (llama3.2:1b default)
- **LangGraph 0.2+**: Agent workflow orchestration
- **LangChain 0.3+**: LLM tooling & chains
- **langchain-ollama**: Ollama LangChain integration

### Monitoring & Caching
- **Langfuse 3.0+**: LLM observability & tracing
- **Redis 7**: In-memory caching for RAG responses

### User Interfaces
- **Gradio 4.0+**: Web-based chat UI
- **python-telegram-bot 21+**: Telegram bot integration

## Key Features

### 1. Hybrid Search Architecture
**The Professional Approach**: Combines keyword (BM25) and semantic (vector) search using Reciprocal Rank Fusion (RRF).

**Search Modes**:
- **Keyword-only**: Traditional BM25 for exact matching
- **Vector-only**: Semantic similarity via embeddings
- **Hybrid** (default): Best of both worlds with RRF scoring

**Implementation**: `src/services/opensearch/client.py`

### 2. Agentic RAG Workflow (Week 7)

Built with **LangGraph**, featuring intelligent decision-making nodes:

```
START → Guardrail → Out-of-Scope Detection
              ↓
         Retrieve Documents
              ↓
         Grade Documents → [Relevant?]
              ↓                    ↓
        [Yes: Generate]    [No: Rewrite Query]
              ↓                    ↓
         Stream Answer       Retry Retrieval
              ↓
            END
```

**Node Descriptions**:
- **Guardrail**: Validates query is in-domain (arXiv CS papers) using LLM scoring
- **Retrieve**: Fetches top-k documents via hybrid search
- **Grade Documents**: Evaluates relevance of each retrieved chunk
- **Rewrite Query**: Reformulates query when results are poor
- **Generate Answer**: Streams response with citations

**Implementation**: `src/services/agents/agentic_rag.py`

### 3. Intelligent PDF Chunking

Uses **Docling** for semantic-aware chunking:
- Preserves document structure (sections, paragraphs)
- Configurable chunk size and overlap
- Metadata preservation (title, authors, section headers)

### 4. Streaming Responses

Real-time answer generation with Server-Sent Events (SSE):
- Gradio UI shows live token streaming
- Source citations appended after generation
- Search metadata included (mode, chunks used, sources)

**Implementation**: `src/routers/ask.py` and `src/routers/agentic_ask.py`

### 5. Production Monitoring

**Langfuse Integration**:
- Trace every RAG execution
- Monitor LLM calls, retrieval quality, agent decisions
- Performance analytics & debugging

**Dashboard**: http://localhost:3000

### 6. Redis Caching

Semantic cache for repeated queries:
- Stores embeddings of queries
- Returns cached responses for similar questions
- Configurable TTL and similarity thresholds

## Configuration (`.env`)

Key environment variables:

```bash
# Database
POSTGRES_DATABASE_URL=postgresql+psycopg2://rag_user:rag_password@localhost:5432/rag_db

# OpenSearch
OPENSEARCH_HOST=http://localhost:9200
OPENSEARCH_INDEX_NAME=arxiv_papers_hybrid

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# Jina Embeddings (requires API key)
JINA_API_KEY=your_jina_api_key_here
JINA_MODEL=jina-embeddings-v3

# Langfuse (requires API key)
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_ENABLE_BOT=false

# arXiv API
ARXIV_MAX_RESULTS=10
ARXIV_CATEGORIES=cs.AI,cs.LG
```

## Development Workflow

### Initial Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd production-agentic-rag-course

# 2. Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys (Jina, Langfuse)

# 4. Install dependencies
uv sync

# 5. Start infrastructure
docker compose up --build -d

# 6. Verify health
curl http://localhost:8000/api/v1/health
```

### Running Services

```bash
# Start API server
docker compose up api -d

# Start Gradio UI (separate process)
uv run python gradio_launcher.py

# View logs
docker compose logs -f api

# Access Airflow
# Navigate to http://localhost:8080
# Credentials in: airflow/simple_auth_manager_passwords.json.generated
```

### Development Commands

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Code formatting (Ruff)
uv run ruff format src/
uv run ruff check src/ --fix

# Launch Jupyter notebooks
uv run jupyter notebook notebooks/
```

### Testing the System

```bash
# 1. Trigger Airflow DAG manually (first-time data ingestion)
# Go to http://localhost:8080 → arxiv_paper_ingestion → Trigger DAG

# 2. Test hybrid search
curl -X POST http://localhost:8000/api/v1/hybrid-search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer attention mechanisms",
    "top_k": 5,
    "use_hybrid": true
  }'

# 3. Test RAG endpoint
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do transformers work?",
    "top_k": 3,
    "use_hybrid": true,
    "model": "llama3.2:1b"
  }'

# 4. Test agentic RAG
curl -X POST http://localhost:8000/api/v1/agentic-ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain self-attention in transformers"
  }'
```

## Common Tasks

### Adding New API Endpoints

1. Create router in `src/routers/`
2. Define Pydantic schemas in `src/schemas/api/`
3. Implement business logic in `src/services/`
4. Register router in `src/main.py`

Example:
```python
# src/routers/new_feature.py
from fastapi import APIRouter
from src.schemas.api.new_feature import FeatureRequest, FeatureResponse

router = APIRouter(prefix="/api/v1", tags=["new-feature"])

@router.post("/new-feature", response_model=FeatureResponse)
async def new_feature(request: FeatureRequest):
    # Implementation
    pass
```

### Modifying the Agent Workflow

The agentic RAG system is in `src/services/agents/`:

1. **Add new nodes**: Define in `nodes.py`
2. **Modify routing**: Update conditional edges in `agentic_rag.py`
3. **Change prompts**: Edit system prompts in `prompts.py`
4. **Adjust configuration**: Update `config.py` (top_k, thresholds, model)

### Customizing Search Behavior

OpenSearch client: `src/services/opensearch/client.py`

- **Change index mapping**: Modify `create_hybrid_index()`
- **Adjust hybrid weights**: Update RRF parameters in `hybrid_search()`
- **Add filters**: Extend `build_filters()` method

### Adding New Data Sources

1. Create client in `src/services/your_source/`
2. Implement parser if needed
3. Add Airflow DAG in `airflow/dags/`
4. Update database models if schema changes

## Troubleshooting

### OpenSearch connection issues
```bash
# Check OpenSearch health
curl http://localhost:9200/_cluster/health

# View indices
curl http://localhost:9200/_cat/indices?v

# Check index settings
curl http://localhost:9200/arxiv_papers_hybrid/_settings
```

### Ollama model issues
```bash
# List available models
docker exec rag-ollama ollama list

# Pull model
docker exec rag-ollama ollama pull llama3.2:1b

# Test generation
docker exec rag-ollama ollama run llama3.2:1b "Hello!"
```

### Airflow DAG not running
```bash
# Check DAG status
docker compose logs airflow

# Access Airflow shell
docker exec -it rag-airflow bash

# Test Python imports
docker exec rag-airflow python -c "from arxiv_ingestion.fetching import fetch_daily_papers"
```

### Redis cache issues
```bash
# Connect to Redis CLI
docker exec -it rag-redis redis-cli

# View all keys
KEYS *

# Clear cache
FLUSHALL
```

## Educational Context

This is a **7-week progressive course** teaching production RAG systems:

**Learning Philosophy**:
- Start with infrastructure (Docker, databases, search engines)
- Master traditional search (BM25) before vectors
- Gradually add complexity (embeddings, LLMs, agents)
- Focus on production practices (monitoring, caching, error handling)

**Target Audience**: AI engineers, ML practitioners, backend developers wanting to build real-world RAG systems.

**Pedagogical Approach**: Each week builds on previous weeks with:
- Detailed blog posts explaining concepts
- Hands-on Jupyter notebooks
- Working code releases (git tags)
- Production-grade implementations

## Code Quality Standards

- **Type hints**: All functions use Python type annotations
- **Pydantic validation**: Strict data validation at API boundaries
- **Async/await**: Async programming for I/O operations
- **Error handling**: Custom exceptions with proper HTTP status codes
- **Logging**: Structured logging throughout the codebase
- **Testing**: Unit tests with pytest, integration tests with testcontainers
- **Documentation**: Docstrings for all public APIs
- **Formatting**: Ruff for consistent code style

## Key Design Patterns

1. **Factory Pattern**: Service creation in `src/services/*/factory.py`
2. **Repository Pattern**: Data access abstraction in `src/repositories/`
3. **Dependency Injection**: FastAPI dependencies in `src/dependencies.py`
4. **Service Layer**: Business logic separated from HTTP handlers
5. **Schema Validation**: Pydantic models for all data structures
6. **Async Context Managers**: Lifespan management in `src/main.py`

## API Conventions

- **Prefix**: All routes start with `/api/v1`
- **Health check**: `GET /api/v1/health`
- **Request validation**: Pydantic models in `src/schemas/api/`
- **Error responses**: Consistent JSON error format
- **Streaming**: SSE for real-time responses (`/stream` endpoints)
- **Documentation**: Auto-generated OpenAPI at `/docs`

## Agent Instructions for Development

When working on this codebase:

1. **Understand the week**: Check which week's features you're modifying
2. **Follow the architecture**: Services → Repositories → Models → Routers
3. **Use factories**: Don't instantiate clients directly, use factory functions
4. **Validate data**: Always use Pydantic schemas for API boundaries
5. **Handle async**: Use `async/await` for all I/O operations
6. **Log extensively**: Add logging for debugging and monitoring
7. **Test thoroughly**: Write tests for new features
8. **Document changes**: Update docstrings and comments
9. **Check dependencies**: Ensure Docker services are running
10. **Monitor traces**: Use Langfuse to debug RAG executions

## Design Context

### Users

**Primary user:** Power user / developer — AI/ML engineers, backend engineers, and data scientists who are either building or learning from this system. Technically fluent, comfortable in dark environments, deeply value density, keyboard control, and no hand-holding. They open the app to get a specific job done fast. The UI should get out of their way.

**Job to be done:** Find answers grounded in a corpus of research papers and security advisories using natural language and hybrid AI search, and manage the documents that feed that corpus.

**Emotional goal:** Confidence and control. A sharp, reliable instrument.

---

### Brand Personality

**Three words:** Precise · Powerful · Dark

**Voice:** Direct. Minimal prose. Data speaks for itself. Labels are short and informative. No cheerful copy. Error messages are honest and actionable.

**Reference:** Linear — dense, keyboard-first, muted dark backgrounds, surgical typography. Quiet UI that respects focus.

**Anti-references:**
- No enterprise / corporate grey (no SharePoint aesthetic)
- No cluttered dashboards without visual hierarchy

---

### Aesthetic Direction

**Theme:** Dark by default, light mode available as a toggle. CSS custom properties for every color — never hardcode.

**Primary accent:** Emerald / green (`#10b981`, `#34d399`) — technical, calm, precise. Reserved for positive states and active accents.

**Color palette:**
- Backgrounds: `#0a0a0b` → `#111113` → `#18181b` → `#1c1c1f` (surface steps)
- Borders: `#2e2e33` / `#3a3a40`
- Text primary: `#fafafa` | secondary: `#a1a1aa` | tertiary: `#71717a`
- Accent: emerald `#10b981` / `#34d399`
- Severity: Critical `#ef4444`, High `#f97316`, Medium `#eab308`, Low `#3b82f6`
- Score badges: green >0.8, amber >0.5, red ≤0.5
- Role badges: admin amber `#f59e0b`, user slate `#6b7280`

**Typography:**
- UI: Inter or Geist (tight scale: 11–12px labels, 13–14px body, 16–20px headings)
- Monospace (IDs, code, chunk text): JetBrains Mono or Fira Code

**Spacing:** 4px base unit. Cards 16–20px padding. Dense by design.

**Border radius:** 6–8px cards/inputs, 4px badges/chips. Nothing bubbly.

**Motion:** Fast and purposeful — ≤150ms state changes, ≤250ms panel slides. Always respect `prefers-reduced-motion`.

---

### Design Principles

1. **Density earns trust.** The user is technical. Show more information layered via accordions, tooltips, and side panels — not less.
2. **Dark is the default experience.** Every color decision is made in dark mode first. Light mode is a coherent inversion via CSS custom properties.
3. **Green means go.** Emerald is reserved for positive states and active accents. Severity uses its own semantic color system. Color is never the only signal.
4. **The interface should feel fast.** Skeleton screens not spinners. Streaming renders live. Cache hits surface immediately with a lightning bolt badge.
5. **Keyboard-first, mouse-friendly.** `/` focuses search. `Cmd+K` opens command palette. `Enter` submits. `Escape` dismisses. Focus states always visible.

---

### Frontend Stack (when building the React UI)

- Framework: React 18+ with Vite (or Next.js 14 App Router)
- Styling: Tailwind CSS + shadcn/ui
- Server state: TanStack Query v5 | UI state: Zustand
- Streaming: Native `fetch` + `ReadableStream`
- Charts: Recharts | Upload: react-dropzone | Markdown: react-markdown
- Toasts: sonner | Icons: Lucide React | Dates: date-fns
- All API calls target `.NET Gateway :8000` with JWT Bearer auth
- Full endpoint reference: `IntegrationDocs/FRONTEND_INTEGRATION_GUIDE.md`

---

## References

- **Blog Series**: https://jamwithai.substack.com/
- **GitHub Releases**: Tagged by week (week1.0, week2.0, etc.)
- **Architecture Diagrams**: `static/` folder
- **OpenSearch Docs**: https://opensearch.org/docs/latest/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
