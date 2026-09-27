# GROOT — Compact project memory

Verified: 2026-09-28. Clean starting HEAD was `231e3027fc4299dd94ed75451dc45dccf4b2dbc8`; setup changes below are uncommitted. All six living docs and service sources were audited before implementation. Do not rely on the older KT or the docs' former `06c15a9` snapshot. No commits or pushes were made.

## Purpose and architecture

Operational intelligence for growing startups: investigate company information, explain findings, recommend, then eventually approve/act/verify. Current product is a development prototype.

- `frontend/`: Next.js/React/TypeScript orb, browser speech and MediaPipe gestures. Calls FastAPI `/ai` directly; creates random user/organization UUIDs. Application code was not changed.
- `backend/`: Django business models/admin, GitHub integration/event ingestion, text/PDF document processing, Celery/Redis configuration. Only `/admin/` is routed.
- `ai_engine/`: FastAPI `/health`, `/ai`, `/rag`; Groq provider/tool loop; SQLAlchemy/Alembic pgvector RAG; standalone agents and control components.
- Shared PostgreSQL: Django owns business/document/chunk tables; AI owns `document_chunk_embeddings` and reads `core_documentchunk` directly. Reuse `Base`, `SessionLocal`, `get_db`; preserve Alembic's table ownership filter. No schemas or migrations changed in the setup module.

## Completed module — Make setup reproducible

This was the first numbered unfinished step in `docs/Task.md`. It is complete at the scope of dependency declarations, environment examples, database alignment, and pgvector prerequisite verification.

Files and decisions:

- `backend/requirements.txt`: added `langchain-core==1.5.6`, `langchain-groq==1.1.3`, `langgraph==1.2.11`. Replaced Groq `1.6.0` with the installed/tested `0.37.1` because the declared LangChain adapter requires Groq `>=0.30,<1`. Other pins were preserved.
- `backend/config/settings_base.py`: loads repository-root `.env`, with existing process variables taking precedence; PostgreSQL and Celery URLs now read environment values. Existing local defaults remain.
- `ai_engine/app/db/database.py`: resolves the same root `.env`, uses matching PostgreSQL defaults and `URL.create` for credential escaping. `DATABASE_URL` remains a string; existing engine/session/Base remain.
- `ai_engine/app/db/check.py`: read-only CLI for database connectivity and enabled pgvector version. Distinguishes available-but-disabled extension from missing server installation, returns exit code 1 with guidance, and avoids echoing driver connection details. No extension installation or DDL.
- `.env.example`: added Groq/GitHub credentials and Redis broker/result URLs. Existing `.env` was not edited.
- `frontend/.env.example`, `frontend/.gitignore`: public AI URL example for `frontend/.env.local`; example exempted from the nested ignore rule. Relevant bundled Next.js environment guide was read. No frontend feature/fix was implemented.
- `README.md`: local setup, operator extension provisioning, migrations, service commands and test instructions.
- `ai_engine/tests/test_setup.py`: 11 new tests; all existing tests left unchanged.
- All six living docs updated after implementation and regression checks.

Configuration contract: both services read `POSTGRES_DB/USER/PASSWORD/HOST/PORT`; defaults are `groot_db`, `rachit`, empty password, `localhost`, `5432`. Root dotenv loading is independent of launch directory and does not override exported values. Celery defaults remain local Redis databases 0 and 1. Frontend loads its own environment file; backend secrets never belong in public variables.

## Verified tests and checks

Commands below are from the repository root unless specified. Existing interpreter: `.venv/bin/python` (3.14.4). Fresh installation used a temporary venv with the same Python version, without modifying the project venv.

| Check | Exact result |
| --- | --- |
| Baseline: `.venv/bin/python -m unittest discover -s ai_engine/tests` | 162 run; 161 passed; 1 failure |
| Baseline: `../.venv/bin/python manage.py test core --noinput` from `backend/` | 84 run; 84 passed |
| Focused: `.venv/bin/python -m unittest ai_engine.tests.test_setup ai_engine.tests.test_database ai_engine.tests.test_models ai_engine.tests.test_langchain_groq ai_engine.tests.test_agent_graph ai_engine.tests.test_ai_engine` | 27 run; 27 passed, including all 11 new tests |
| Final AI discovery, existing and fresh environments | Each: 173 run; 172 passed; same 1 failure |
| Final Django `manage.py test core --noinput`, existing and fresh environments | Each: 84 run; 84 passed on PostgreSQL |
| Fresh venv `python -m pip install -r backend/requirements.txt` then `python -m pip check` | Installation succeeded; no broken requirements |
| `.venv/bin/python -m ai_engine.app.db.check` | PostgreSQL connected; pgvector 0.8.6 enabled |
| `.venv/bin/python backend/manage.py check` | 0 issues, 0 silenced |
| `.venv/bin/python backend/manage.py makemigrations --check --dry-run` | No changes detected |
| Alembic offline `upgrade head --sql` with special-character credentials | Passed as part of focused tests; embedding table SQL generated |
| Fresh Django/Celery process task registry inspection | Only `core.tasks.health_check_task` auto-registered |
| `git diff --check` | Passed |

The sole test failure is pre-existing: `test_browser_tool.BrowserToolTests.test_extracts_information` expects `"page heading"`; `BrowserTool.extract_information` returns `BrowserResult(action='extract_information', data={'query': 'page heading'})`. No regressions were observed. Browser implementation/tests are tracked in the baseline, not untracked local work.

Initial sandbox denial of PostgreSQL access and package-index DNS access was resolved with permitted access. These are not test regressions. Existing `declarative_base` deprecation warnings and expected malformed-PDF fixture diagnostics were not suppressed. The existing environment has pypdf 6.16.1; the fresh environment used the unchanged manifest pin 6.1.2, and both passed Django tests.

## Implementation reality and remaining gaps

- Agent contracts/registry/capability policy already exist: do not restart historical Module 09.
- LangChain Groq adapter exists; default AI uses direct Groq. LangGraph wraps one node; coordination is sequential and explicitly selected. Neither is wired into `/ai`.
- KnowledgeAgent calls RAG. ResearchAgent packages supplied state. DataAnalyst/Operations agents are placeholders. All currently declare empty allowed-tool lists.
- Equaliator is heuristic; contradiction detection is empty. Evaluator reports result fields. Executor returns success without invoking a tool; verifier copies success. Audit is memory-only. Default tool registry contains only `health_check`.
- Identity is unresolved: Django IDs are integers, AI IDs are UUIDs; no authentication connects them. RAG lacks organization filtering. Resolve both before real tenant use.
- Document processing does not enqueue embeddings. Chunk replacement can leave stale vectors; embedding writes insert rather than upsert. Preserve event idempotency and deterministic chunk behavior.
- `AIService.handle_rag` and `RAGService.answer` duplicate answer composition. Reuse existing retrieval services when consolidating.
- Nested ingestion/document tasks are not auto-registered in a fresh Celery process. No recurring ingestion, durable workflows, MongoDB, MCP, CI, or container deployment exists.
- Ollama defaults remain `nomic-embed-text:latest`, 768 dimensions, batch size 32. Local embeddings are deterministic hashes, not semantic vectors.
- Setup verification does not cover live Groq/GitHub/Ollama calls, running Redis workers, frontend lint/build, production deployment, or a full fresh PostgreSQL provisioning cycle. The explicit preflight is not a runtime readiness gate. Database owners still install/enable pgvector; requirements are not a full transitive lockfile. Development secret/host defaults remain unsuitable for production.

## Next module

**Finish the knowledge flow**, starting with authenticated membership/identity and organization-scoped retrieval. Then consolidate RAG composition, register nested tasks, and implement the processing-to-embedding handoff with retry/upsert and stale-vector cleanup; verify extraction → embeddings → scoped answer with evidence. These are pending tasks, not current behavior. Keep the existing architecture and avoid unrelated frontend/browser work. See [Task.md](Task.md).
