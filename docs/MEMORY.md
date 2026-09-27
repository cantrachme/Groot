# GROOT — Compact project memory

Verified: 2026-09-28. Starting HEAD was clean at `3c42b23 feat: make setup reproducible`. All six docs and existing code were audited. The knowledge-flow changes described below are uncommitted; no commit or push was made. Use this verified state over the older KT or earlier module numbers.

## Completed module and current architecture

**Finish the knowledge flow (backend)** is complete: membership-authenticated `/rag` → existing KnowledgeAgent → shared RAGService → organization-scoped pgvector/text lookup → answer with evidence/citations. Django processing now dispatches retry-safe embeddings after commit; a document lock and cascading chunk foreign key coordinate reprocessing/deletion. The previous setup module remains committed in `3c42b23`.

Ownership is unchanged: Django owns users, memberships, company/document data and new knowledge credentials/status fields. SQLAlchemy/Alembic own vectors using existing engine/Base/SessionLocal/get_db. AI reads Django tables with parameterized SQL. Celery invokes existing AI embedding services; no new database engine or workflow framework was added. Frontend remains the voice/orb/gesture prototype calling `/ai`.

## Important changed files

### Identity and HTTP

- `backend/core/models.py`, `backend/core/migrations/0013_knowledge_flow.py`: `KnowledgeAccessToken` with unique digest, membership and expiry; `Document.embedding_status` and `embedding_error`.
- `backend/core/knowledge_tokens.py`, `backend/core/management/commands/issue_knowledge_token.py`, plus the two management package initializers: operator issuance for an existing active membership, 32 random bytes, SHA-256 stored digest, 1–168 hour lifetime (default 24).
- `ai_engine/app/core/authentication.py`: bearer token digest lookup joined to current membership and active user; expired/unknown/revoked/inactive-user credentials return 401.
- `ai_engine/app/main.py`: authenticated synchronous `/rag` reaches KnowledgeAgent; request accepts request UUID/message/top_k only; preserves query/context/response and adds evidence/citations. Message is nonblank and <=12,000 characters; top_k is 1–50. Identity fields are rejected. `/ai` and `/health` retain their existing contracts.
- `ai_engine/app/core/context.py`, `ai_engine/app/agents/context.py`, `ai_engine/app/agents/knowledge.py`: integer identities for the trusted flow, UUID compatibility for prototype contracts, scope propagation and context/evidence preservation.

### Retrieval and embeddings

- `ai_engine/app/services/tenant_scope.py`, `similarity_search_service.py`, `rag_document_service.py`, `retrieval_service.py`, `rag_service.py`: validate/propagate scope, enforce organization and extraction/embedding readiness before top-k and again in text lookup; absent scope returns no stored data. Scoped calls reload authorized text rather than trusting supplied maps. Empty assembled context returns a fixed insufficient-context response without an LLM call.
- `ai_engine/app/services/ai_service.py`: delegates answer composition to RAGService and uses the shared embedding factory. Removed duplicate RAG assembly/imports.
- `ai_engine/app/embeddings/factory.py`: shared local/Ollama construction for query and job paths, honoring `OLLAMA_BASE_URL`.
- `ai_engine/app/services/embedding_service.py`, `chunk_embedding_service.py`: reuse batch validation; add transactional upsert for workflow retries. Unique key remains chunk/model; updates preserve record ID/creation time and replace vector/dimensions/update time. Existing low-level insert methods remain available; workflow uses upsert.
- `ai_engine/app/models/embedding.py`, `ai_engine/alembic/versions/b17d32a0e901_embedding_chunk_lifecycle.py`: cleanup legacy orphan vectors and add `embedding_chunk_fk ON DELETE CASCADE`. Reference-only Django chunk metadata is separate from AI Base metadata.
- `ai_engine/alembic/env.py`: uses the model's existing Base metadata and accepts an explicit connection for integration migration tests; ownership filter remains intact.

### Processing and registration

- `backend/core/documents/pipeline.py`, `chunk_persistence.py`: atomic processing/replacement under the document lock; invalidate embeddings; publish only after successful commit.
- `backend/core/documents/tasks.py`: post-commit dispatch, visible broker failure status, `embed_document` task, current-chunk loading under document lock, existing SessionLocal handoff, ready/failed state and three automatic retries with backoff for runtime/provider/SQLAlchemy exceptions. Validation/configuration errors are recorded and re-raised without automatic retry.
- `backend/core/tasks.py`, `backend/config/celery.py`: expose nested tasks and defer autodiscovery until Django initializes. Worker-style loader test verifies health, ingestion, processing and embedding registrations.
- `backend/config/settings_base.py`: makes root AI modules importable when a worker starts from `backend/`; existing environment/dependency setup is retained.
- `README.md`: migration order, token issuance and `/rag` request contract, ingestion/retry instructions and test prerequisites.
- All six living docs updated after verification. No frontend files or existing test files were changed.

### New tests

- `ai_engine/tests/test_knowledge_flow.py`: 19 tests for credential handling, scope, SQL/forwarding, composition, evidence HTTP responses, body spoofing/validation, empty context, atomic upsert validation/errors and shared provider configuration.
- `backend/core/test_knowledge_flow.py`: 23 tests (12 token/handoff tests and 11 PostgreSQL integration tests). Integration uses Django/Alembic tables and real pgvector, with fake external embedding/LLM providers.

## Decisions and operational contracts

- Authentication is knowledge-specific. Token membership supplies integer user/organization IDs and role; all current membership roles may read organization knowledge. This does not authorize actions or make the unauthenticated `/ai` prototype a trusted business interface.
- `/rag` intentionally replaces the previous unauthenticated UUID-identity contract. Missing credentials return 401; body identity fields return 422 after authentication. Existing response fields remain and evidence/citations are additive.
- The document lock spans embedding provider work and the AI commit. Reprocessing uses the same lock; duplicate/delayed jobs read current chunks. Queries require both extraction and embeddings ready. Vectors commit before Django readiness; a failed final status commit may require a safe retry.
- Chunk/document deletion cascades vectors. The Alembic upgrade deletes legacy orphans before creating the constraint; downgrade cannot restore deleted orphan rows. Apply Django migrations before Alembic. Existing documents become pending and require an embedding job.
- `process_document` keeps its extraction result semantics, independently of embedding status. A broker dispatch failure is recorded on the document. There is no durable outbox; process/worker loss or a missed publication can leave pending work requiring manual retry.
- Production configuration, dependencies, architecture and unrelated agent/browser features were not redesigned. Native providers/services are reused. No migrations were applied to the developer's existing database; only the temporary test database was migrated.

## Exact verification results and commands

Python: existing `.venv/bin/python` (3.14.4). Commands below are from repository root unless stated. All existing tests were preserved; none skipped/suppressed.

| Check | Command / method | Exact result |
| --- | --- | --- |
| Baseline AI | `.venv/bin/python -m unittest discover -s ai_engine/tests` | 173 run; 172 passed; 1 failed |
| Baseline Django | `../.venv/bin/python manage.py test core --noinput` from `backend/` | 84 run; 84 passed |
| New AI tests | `.venv/bin/python -m unittest ai_engine.tests.test_knowledge_flow` | 19 run; 19 passed |
| Focused AI + impacted existing modules | `.venv/bin/python -m unittest ai_engine.tests.test_knowledge_flow ai_engine.tests.test_rag_service ai_engine.tests.test_retrieval_service ai_engine.tests.test_similarity_search_service ai_engine.tests.test_knowledge_agent ai_engine.tests.test_embedding_service ai_engine.tests.test_setup` | 55 run; 55 passed |
| Focused Django | `../.venv/bin/python manage.py test core.test_knowledge_flow --noinput` from `backend/` | 23 run; 23 passed |
| Final full AI | `.venv/bin/python -m unittest discover -s ai_engine/tests` | 192 run; 191 passed; same 1 failure |
| Final full Django | `../.venv/bin/python manage.py test core --noinput` from `backend/` | 107 run; 107 passed |
| Django checks | `.venv/bin/python backend/manage.py check` | 0 issues, 0 silenced |
| Django migration drift | `.venv/bin/python backend/manage.py makemigrations --check --dry-run` | No changes detected |
| Python compilation | `.venv/bin/python -m compileall -q ai_engine/app ai_engine/alembic backend/core backend/config` | Passed |
| Offline Alembic | `.venv/bin/python -m alembic -c ai_engine/alembic.ini upgrade head --sql` | Both migrations generated successfully |
| Live migrations in temporary test DB | Django test runner + Alembic upgrade; lifecycle test downgrade → orphan insertion → upgrade → `command.check` | Passed; orphan removed; Django tables preserved; no new upgrade operations detected |
| Lint | Ruff 0.16.9 default `check` on all changed/new Python files, compared with HEAD source using `--stdin-filename` | HEAD: 23 diagnostics; final: 16 pre-existing; **0 new** |
| Patch formatting | `git diff --check` | Passed |

Ruff was installed only in `/tmp/groot-knowledge-lint`; project dependencies and the existing virtual environment were not changed. No project Python type-checker configuration or installed mypy/pyright was found; no static type check is claimed. Frontend lint/build was not relevant because no frontend files changed.

The integration tests verify a higher-ranked foreign vector cannot reach another organization's top-k/context/evidence; expired, removed-membership and inactive-user credentials fail; retries retain vector row IDs; partial vector writes roll back; reprocessing/deletion/extraction failure remove obsolete vectors; unscoped services expose no stored data; and a second DB connection cannot acquire a document lock during embedding.

## Pre-existing failures and visible diagnostics

- `test_browser_tool.BrowserToolTests.test_extracts_information` still expects `"page heading"` but receives `BrowserResult(action='extract_information', data={'query': 'page heading'})`. Present before edits; unchanged. Browser automation remains a stub.
- Ruff baseline diagnostics retained: `backend/core/models.py` has 15 existing diagnostics (duplicate `Organization.created_at` and mutable class lists); `ai_engine/app/agents/knowledge.py` has one existing implicit-string-concatenation diagnostic. No rules were disabled and no noqa suppressions were added.
- Existing SQLAlchemy declarative-base warnings and expected malformed-PDF fixture diagnostics remain. New HTTP tests expose the installed Starlette/httpx deprecation; it is not a failing test. Initial sandbox database access denial was resolved through permitted access.

## Remaining limitations / next module

The knowledge backend is verified with plain-text fixtures and fake external providers; live Groq/Ollama/GitHub calls, semantic answer correctness, PDF-through-LLM execution, live Redis worker delivery and production deployment were not tested. Frontend sign-in/knowledge requests, upload API and token-management UI remain absent. Tokens are operator-issued and expire; existing documents need embedding after migration. Lost dispatch/jobs need operator retry. Per-document locks remain held during provider work. The context assembler's nominal character budget, local nonsemantic embeddings and development production-settings gaps remain.

General coordination is still standalone/sequential. ResearchAgent packages state; DataAnalyst/Operations are placeholders. Equaliator has no contradiction implementation; actions/verification are scaffolds and audit is memory-only. No persistent conversations/workflows, CI, MongoDB or MCP was added.

**NEXT: Add useful read-only tools** — a real business-data query or research source under trusted authorization and allowed tools, with meaningful agent results/failures. Preserve knowledge isolation and lifecycle guarantees. See [Task.md](Task.md).
