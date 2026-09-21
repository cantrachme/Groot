# GROOT — Compact project memory

Snapshot: 2026-09-21, HEAD `06c15a9` plus untracked browser prototype. Lightweight source review only; services/tests were not run. Use current code over the historical KT.

## Purpose

Operational intelligence for growing startups: investigate company information, explain findings, recommend, then eventually approve/act/verify. Current product is a development prototype.

## Architecture

- `frontend/`: Next.js/React/TypeScript orb, browser speech input/output and MediaPipe gestures. Calls FastAPI `/ai` directly; creates random user/organization UUIDs.
- `backend/`: Django business models/admin, GitHub integration/event ingestion, text/PDF document processing, Celery/Redis configuration. Only `/admin/` is routed.
- `ai_engine/`: FastAPI `/health`, `/ai`, `/rag`; Groq provider/tool loop; SQLAlchemy/Alembic pgvector RAG; standalone agents and control components.
- Shared PostgreSQL: Django owns business/document/chunk tables; AI owns `document_chunk_embeddings` and reads `core_documentchunk` directly. Reuse `Base`, `SessionLocal`, `get_db`; preserve Alembic's table ownership filter.

## Implementation reality

- Agent contracts/registry/capability policy already exist: do not restart historical Module 09.
- LangChain Groq adapter exists; default AI path uses direct Groq. LangGraph is a single-node wrapper; coordination is sequential and explicitly selected. Neither is wired into `/ai`.
- KnowledgeAgent calls RAG. ResearchAgent packages supplied state. DataAnalyst/Operations agents are placeholders. All currently declare empty allowed-tool lists.
- Equaliator is heuristic; contradiction detection is empty. Evaluator reports result fields. Executor returns success without invoking a tool; verifier copies success. Audit is memory-only.
- Default global tool registry contains only `health_check`.
- Ollama defaults: `nomic-embed-text:latest`, 768 dimensions, batch size 32. Local embeddings are deterministic hashes, not semantic vectors.
- `ai_engine/app/browser/` and its test were untracked: state/result stubs, not automation. Preserve this unrelated local work.

## Things not to break / gaps to remember

- Preserve organization-scoped event idempotency and deterministic document chunk behavior.
- Identity is unresolved: Django IDs are integers, AI IDs are UUIDs; no authentication connects them. RAG lacks organization filtering. Resolve both before real tenant use.
- Document processing does not enqueue embedding generation. Chunk replacement can leave stale vectors; embedding writes insert rather than upsert.
- `AIService.handle_rag` and `RAGService.answer` duplicate answer composition. Reuse existing retrieval services when consolidating.
- Python manifest is `backend/requirements.txt`; LangChain/LangGraph imports are undeclared. Django DB/Redis settings are hard-coded, while AI DB uses environment values.
- Nested Celery ingestion/document tasks need worker-registration verification. No persistent workflows, MongoDB, MCP, CI, or container deployment was found.
- Follow `frontend/AGENTS.md` before frontend coding. Tests live in `backend/core/tests.py` and `ai_engine/tests/`; historical KT test counts are not fresh results.

## Next direction

First deliver an authenticated, tenant-scoped document-to-evidence answer through existing services. Then add real tools/agent work, coordinated assessment, durable approvals/actions/verification, and activity UI. Keep orchestrator, Equaliator and evaluation responsibilities separate. See [Task.md](Task.md) for priorities and KT discrepancies, [ARCHITECTURE.md](ARCHITECTURE.md) for wiring, and [RULES.md](RULES.md) for extension constraints.
