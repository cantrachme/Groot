# GROOT — Current architecture

Verified: 2026-09-28 against baseline `231e3027fc4299dd94ed75451dc45dccf4b2dbc8` plus uncommitted setup changes. Python tests, fresh dependency installation, task registration and PostgreSQL/pgvector preflight were checked. Frontend and external-provider runtime behavior remain unverified.

## Service and technology map

| Location | Responsibility and technology |
| --- | --- |
| `frontend/` | Next.js 16.3, React 19.2, TypeScript, Tailwind 4; Three.js/React Three Fiber orb; browser speech APIs; MediaPipe gestures |
| `backend/config/`, `backend/core/` | Django 6.1 business models/admin, integration and document services, Celery configuration/tasks |
| `ai_engine/app/` | FastAPI, Pydantic HTTP models, provider/tool abstractions, RAG, standalone agent/control modules |
| `ai_engine/app/db/`, `models/`, `alembic/` | SQLAlchemy/psycopg, PostgreSQL pgvector embeddings, Alembic ownership of AI tables |
| `infrastructure/redis/` | Redis configuration; Django uses Redis database 0 as Celery broker and 1 for results |
| `docs/` | Product, architecture, engineering rules, design, roadmap, compact memory |

Frontend versions above are manifest declarations. Python dependencies for both services are in [backend/requirements.txt](../backend/requirements.txt), now including `langchain-core==1.5.6`, `langchain-groq==1.1.3`, and `langgraph==1.2.11`. Groq is pinned to `0.37.1`, matching the installed/tested adapter requirement `>=0.30,<1`; the previous `1.6.0` declaration conflicted with that adapter. A fresh Python 3.14.4 installation succeeded and `pip check` found no broken requirements. This manifest is not a complete transitive lockfile. No Docker/Compose, Kubernetes, CI pipeline, or MongoDB implementation was found. Root `scripts/` and `tests/` are empty; tests reside beside the services.

## HTTP path that exists today

```mermaid
flowchart LR
    UI[Next.js voice and orb UI] -->|POST /ai| API[FastAPI]
    API --> AI[AIService]
    AI --> ORCH[Orchestrator]
    ORCH --> GROQ[Groq LLM]
    ORCH --> TOOLS[ToolRegistry: health_check]
    TOOLS --> ORCH
    ADMIN[Django admin] --> DOMAIN[Django models]
    DOMAIN --> PG[(PostgreSQL)]
    RAG[POST /rag] --> RET[Embedding and retrieval services]
    RET --> OLLAMA[Ollama]
    RET --> PG
    RET --> ANSWER[Chunk text and LLM context]
    ANSWER --> GROQ
```

- `GET /health`: fixed AI engine health payload; not a dependency readiness check.
- `POST /ai`: requires UUID `user_id`, `organization_id`, `request_id`, and `message`; returns `LLMResponse` (`text`, `tool_calls`). The orchestrator supports an initial LLM call, tool execution, and one follow-up call, not an autonomous loop.
- `POST /rag`: same fields plus `top_k` (default 5); returns `query`, assembled `context`, and `response`. The UI currently calls `/ai`, not `/rag`.
- Django routes only `/admin/`; `core/views.py` remains a placeholder.

[FastAPI entry point](../ai_engine/app/main.py) allows local frontend origins on ports 3000/3001. It has no authentication dependency. Request UUIDs are supplied by callers and are not mapped to Django's integer user/organization keys. Blocking provider/database calls are currently made inside async route functions.

## Storage ownership and knowledge flow

Django owns users, organizations/memberships, teams, customers, projects/tasks, events/risks, integrations, documents, extracted content, and chunks. Django migrations manage these tables. The AI engine owns `document_chunk_embeddings`, managed by Alembic; its autogeneration filter limits reflected tables to that AI table.

The services expect access to the same PostgreSQL database: [RAGDocumentService](../ai_engine/app/services/rag_document_service.py) reads Django's `core_documentchunk` table directly through parameterized SQL. Embeddings reference integer chunk IDs without a database foreign key. `(document_chunk_id, model)` is unique; dimensions are stored separately in a variable-dimension pgvector column. The migration requires the vector extension to be enabled in the target database. The new read-only `python -m ai_engine.app.db.check` command checks connectivity and `pg_extension`, distinguishes an available-but-disabled extension from a missing server installation, and exits nonzero with operator guidance. It does not modify extensions or migrations. The configured database passed with pgvector 0.8.6.

Document preparation and retrieval are separate paths:

1. Django `process_document` task → text/PDF extractor → normalization → deterministic text chunks → Django persistence.
2. AI `DocumentChunkEmbeddingService` → configured embedding provider → AI embedding rows. No call from the document pipeline to this service was found.
3. Query → embedding → cosine search filtered by model/dimensions → chunk text lookup → assembled context → LLM answer.

Ollama defaults to `nomic-embed-text:latest`, 768 dimensions, batch size 32, local server port 11434. These are configured defaults, not a fresh live verification. The local provider creates deterministic hash vectors for development, not semantic embeddings.

Two answer-composition paths remain: `AIService.handle_rag()` and `RAGService.answer()`; both use the shared retrieval primitives. KnowledgeAgent uses the latter. Neither similarity search nor chunk lookup applies organization scope. Reprocessing deletes/recreates Django chunks, while embedding cleanup/replacement is not coordinated, allowing stale references. Embedding writes insert rather than upsert.

## Integrations and background jobs

GitHub is the only concrete connector: environment credentials → integration registry/service → HTTP GET → repository-shaped normalized events → ingestion service → event persistence. Events with external IDs are upserted by organization/source/external ID; events without an external ID are appended. Other `Integration.Provider` values do not have connector implementations.

Celery defines health, ingestion, and document tasks. Configuration autodiscovers `core.tasks`; nested `core.ingestion.tasks` and `core.documents.tasks` are not explicitly imported there. A fresh process loading Django and `config.celery.app` registered only `core.tasks.health_check_task`; nested tasks are not auto-registered. No recurring ingestion schedule, agent job pipeline, or automated embedding queue was found.

## Agent and control components outside HTTP routing

`AgentSelection` supplies names → `MultiAgentCoordinator` → `AgentSupervisor` → one `AgentGraph` per selected agent → `AgentResult` tuple. Execution is sequential. LangGraph wraps a single execution node; there is no checkpointer, branching, pause/resume, or automatic planning. Agent state may contain a live SQLAlchemy session and is not a durable workflow representation.

The LangChain Groq adapter implements GROOT's `LLMProvider`; `AIService` still defaults to the direct Groq adapter. Equaliator compares result summaries and evidence presence; contradiction detection always returns an empty tuple. `AgentEvaluator` scores result fields. Permission, approval, action, verification, and audit components are not connected to this HTTP flow. Audit storage is an in-memory list.

## Configuration and external dependencies

- Django settings and AI database setup resolve the repository-root `.env` from their source paths, with process environment values taking precedence. Both use `POSTGRES_DB/USER/PASSWORD/HOST/PORT` and matching existing local defaults (`groot_db`, `rachit`, empty password, `localhost`, `5432`). No new engine or shared configuration service was added.
- The AI URL is built with `SQLAlchemy.URL.create` and rendered as a string for existing Alembic callers. Credentials with URL special characters survive round trips; Alembic's existing percent escaping and ownership filter remain intact. `Base`, `SessionLocal`, engine settings and migration history are preserved.
- Root `.env.example` includes PostgreSQL, embeddings, Groq/GitHub credentials and Celery Redis URLs. Django reads `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`, retaining local Redis database 0/1 defaults.
- `frontend/.env.example` supplies `NEXT_PUBLIC_AI_ENGINE_URL=http://localhost:8001`; copy it to `frontend/.env.local`. The nested ignore file permits the example while keeping actual environment files ignored. No frontend application behavior changed.
- Django production settings only disable debug and leave allowed hosts empty; the base secret is a development constant.
- MediaPipe loads WASM/model assets from external URLs. Microphone/camera and speech support depend on browser capabilities and permission.

## Setup verification boundary

11 new setup tests cover environment precedence/defaults, root-file resolution, credential encoding, offline Alembic SQL, pgvector states and safe CLI diagnostics. The focused set passed 27/27. Both environments produced Django 84/84 and AI 172/173, retaining only the baseline browser extraction contract failure. Django system checks passed and no model migrations were detected. Existing SQLAlchemy `declarative_base` deprecation warnings remain. The preflight is an explicit operator command; it is not wired into `/health`, request handling, or Alembic startup. Fresh database provisioning, live providers, Redis workers and frontend builds were not exercised.

## Planned architecture, not current wiring

Authenticated request → orchestrator/selection → specialized agents with controlled tools → Equaliator → synthesis → persisted approval where required → real action → independent verification. Preserve Django business-data ownership and the existing SQLAlchemy/RAG foundation. Add persistence, background execution, tracing, and browser drivers incrementally. MongoDB, MCP, additional specialist agents, and container orchestration remain unimplemented possibilities.
