# GROOT — Compact project memory

Verified: 2026-09-28. Starting HEAD was clean at `20008e6 feat: complete tenant-scoped knowledge flow`. All six living docs and the actual implementation were audited before edits. **Trusted Read-Only Tools is complete and verified in the working tree.** No commit or push was made; setup (`3c42b23`) and knowledge backend (`20008e6`) were already committed and were not redone.

## Current architecture and completed modules

Django owns users, memberships, company/document/chunk data, knowledge tokens and document readiness. SQLAlchemy/Alembic own vectors using the existing engine/Base/SessionLocal/get_db. AI reads Django-owned records through scoped queries without adding their tables to Base.metadata. Frontend remains the voice/orb/gesture prototype calling `/ai`.

- Setup: compatible dependency declarations, shared environment-based PostgreSQL/Redis configuration, example environments, read-only pgvector preflight and setup instructions.
- Knowledge backend: authenticated `/rag` → KnowledgeAgent → shared RAGService → tenant-scoped vector/text retrieval → answer, evidence and citation IDs. Empty authorized context returns a fixed insufficient-context response without an LLM call. Processing dispatches embeddings after commit; document locks and cascading chunk foreign keys coordinate replacement/deletion.
- **Trusted Read-Only Tools:** private registry for ready-document inventory and ordered chunk inspection. Each execution checks live membership, both integer IDs, PermissionEngine, AgentCapabilityPolicy, tenant scope and PostgreSQL read-only transaction semantics. Direct tool use and the existing Orchestrator are verified. `/ai` remains health-only; `/rag` still uses its existing RAG path.

## Files changed in this module

| File | Implemented change |
| --- | --- |
| `ai_engine/app/tools/read_only/base.py` | Strict bounded parameters; `ReadOnlyTool` guarded executor; live role-derived permission plus agent checks; central tenant predicate/LIMIT; private read-only registry; rollback/close on all outcomes |
| `ai_engine/app/tools/read_only/documents.py` | `list_documents` and `read_document_chunks` definitions, query-only Django table expressions, readiness, pagination and SQL text truncation |
| `ai_engine/app/tools/read_only/__init__.py` | Request-local registry factory with server-bound credential/agent/context and injectable session factory |
| `ai_engine/app/tools/schema.py` | Typed Pydantic argument schemas for new tools, preserving the legacy empty object schema |
| `ai_engine/app/agents/knowledge.py` | Two allowed tool names and `read_only_tools(context, credentials)` factory method; existing `execute` behavior preserved |
| `ai_engine/app/permissions/models.py` | Integer identity annotations alongside UUID compatibility in AuthorizationContext |
| `ai_engine/tests/test_read_only_tools.py` | 11 new unit tests for registry/schema contracts, authorization, strict input, tenant parameters and existing orchestrator integration |
| `backend/core/test_read_only_tools.py` | 12 new real PostgreSQL tests for reads, isolation, membership changes, pagination/truncation and read-only enforcement |
| `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/RULES.md`, `docs/DESIGN.md`, `docs/Task.md`, `docs/MEMORY.md` | Verified capability, architecture, rules, design, roadmap and exact verification record |

No existing test files, dependencies, models, migrations, HTTP routes, frontend files, browser code or action scaffolds were changed.

## Read-tool decisions and contracts

1. Current credentials grant **knowledge reads only**. The first tools therefore inspect ready documents/chunks. Project/task/customer queries would need a separately trusted grant; no general business or action permission was inferred.
2. Definitions extend the existing Tool contract; ReadOnlyToolRegistry extends the existing registry. Trusted declarations supply SELECT, parameter model, permission, tenant column and cursor field. Registration rejects general tools, non-SELECT definitions, unsupported permissions and overridden execution methods. Extension authors are trusted Python developers, not sandboxed plugins.
3. Construct a new registry per trusted request. `KnowledgeAgent.read_only_tools(context, credentials, session_factory=...)` binds server dependencies; normal production default is the existing SessionLocal. Call `registry.get(name).execute(**arguments)` or supply the registry to the existing Orchestrator. Do not share a credential-bound registry across callers or put it in the global `/ai` registry.
4. Credentials and context are not model arguments. Strict Pydantic models reject extra fields (including operation, SQL, credentials, tenant and identity), coercion, booleans as integers and out-of-range values. All tools require explicit `knowledge.read` permission mapping and an agent allowlist entry.
5. Each execution starts a **fresh** session and sets `SET TRANSACTION READ ONLY` before the credential SELECT. The existing authentication function rechecks expiry, membership and active user. Both bound IDs must be exact integers matching that identity. Only live `admin`/`member` roles yield a knowledge grant to PermissionEngine; unknown roles fail closed. AgentCapabilityPolicy separately checks context permission and agent allowlist.
6. The executor adds the organization predicate and `limit + 1`, materializes a bounded page, then rolls back and closes on success or failure. It never commits or uses the RAG session from `state['db']`. PostgreSQL rejects modifying CTEs hidden inside SELECT (verified SQLSTATE `25006`), and subsequent sessions return to ordinary transaction mode.
7. `list_documents`: `after_id` default 0 (0 through signed bigint max), `limit` default 20, range 1–100. Ascending document ID; output only ID/name/document_type/mime_type/size.
8. `read_document_chunks`: positive bigint `document_id`, `after_index` default -1 (-1 through signed int max), `limit` default 5, range 1–20. Ascending chunk index; output document_chunk_id/document_id/chunk_index/text/truncated. SQL caps text at 4,000 Unicode characters; longer chunks explicitly set `truncated=true`.
9. Both definitions require ready extraction **and** embeddings. Pages are `{items, next_cursor}`; null cursor means no additional row was found. Foreign, missing and unready document IDs return identical empty chunk pages. Storage keys, internal errors, credentials and personal fields are excluded.
10. Existing native exceptions remain visible: invalid arguments raise Pydantic ValidationError, invalid credentials raise the existing HTTPException(401), authorization raises PermissionError subclasses, missing tool names raise KeyError, and database write rejection propagates. There is no writable fallback or new HTTP error mapping.

## Exact verification results and commands

Python: existing `.venv/bin/python` (3.14.4). Commands are from repository root unless specified. Existing tests were preserved; none skipped or suppressed. Baselines were run before implementation on clean `20008e6`.

| Check | Command / method | Exact result |
| --- | --- | --- |
| Baseline AI | `.venv/bin/python -m unittest discover -s ai_engine/tests` | 192 run; 191 passed; 1 failed |
| Baseline Django | `../.venv/bin/python manage.py test core --noinput` from `backend/` | 107 run; 107 passed |
| Focused new AI | `.venv/bin/python -m unittest ai_engine.tests.test_read_only_tools` | 11 run; 11 passed |
| Focused AI regression | `.venv/bin/python -m unittest ai_engine.tests.test_read_only_tools ai_engine.tests.test_agents ai_engine.tests.test_permission_engine ai_engine.tests.test_knowledge_agent ai_engine.tests.test_ai_engine ai_engine.tests.test_knowledge_flow ai_engine.tests.test_rag_service` | 65 run; 65 passed |
| Focused PostgreSQL | `../.venv/bin/python manage.py test core.test_read_only_tools --noinput` from `backend/` | 12 run; 12 passed |
| Full AI regression | `.venv/bin/python -m unittest discover -s ai_engine/tests` | 203 run; 202 passed; same 1 failure |
| Full Django regression | `../.venv/bin/python manage.py test core --noinput` from `backend/` | 119 run; 119 passed |
| Django checks | `.venv/bin/python backend/manage.py check` | 0 issues, 0 silenced |
| Django migration drift | `.venv/bin/python backend/manage.py makemigrations --check --dry-run` | No changes detected |
| Python compilation | `.venv/bin/python -m compileall -q ai_engine/app ai_engine/alembic backend/core backend/config` | Passed |
| Offline Alembic | `.venv/bin/python -m alembic -c ai_engine/alembic.ini upgrade head --sql` | Both existing migrations generated successfully |
| Live migration regression | Existing knowledge-flow lifecycle test within `test core`: temporary Django DB, Alembic upgrade/downgrade/orphan seed/upgrade/check | Passed; no new upgrade operations detected |
| Ruff 0.16.9 | `check` on all 8 changed/new Python files; KnowledgeAgent HEAD compared with `git show HEAD:ai_engine/app/agents/knowledge.py` piped to `check --stdin-filename ai_engine/app/agents/knowledge.py -` | Same 1 pre-existing ISC004; **0 new diagnostics**. The other 7 files pass |
| Patch formatting | `git diff --check` | Passed |

Lint binary: `/tmp/groot-knowledge-lint/bin/ruff` already available from the previous module. No dependencies were installed or changed. No Python static type checker configuration or installed mypy/pyright was found; no static type-check result is claimed. Frontend lint/build is unrelated to these changes.

New PostgreSQL tests create their own engine **only against the temporary `test_` database selected by Django** and dispose it after testing. They verify both known membership roles, denied unknown roles, missing/bad/expired/revoked credentials, disabled users, deleted memberships, mismatched identities, same-user multiple-membership isolation, readiness, bounded cursors, Unicode truncation, unchanged application rows, read-only transaction reset, and rejection/rollback of an UPDATE CTE hidden inside a SELECT. Existing regression tests also cover the prior knowledge lifecycle, pgvector queries and migrations. No migrations were applied to the developer database.

## Pre-existing failures and visible diagnostics

- `test_browser_tool.BrowserToolTests.test_extracts_information` expects `"page heading"` but receives `BrowserResult(action='extract_information', data={'query': 'page heading'})`. Identical baseline and final failure; browser remains a stub.
- `ai_engine/app/agents/knowledge.py` has one existing Ruff ISC004 implicit-string-concatenation diagnostic. Confirmed with HEAD source using the same linter. No suppressions or rule changes. The 15 model diagnostics recorded by the previous module remain outside this module's changed-file lint scope; models were not touched.
- SQLAlchemy declarative-base and installed Starlette/httpx deprecations remain visible. Malformed-PDF fixture messages are expected diagnostics, not failures.
- No new regression failures were introduced.

## Prior knowledge implementation facts to retain

- `backend/core/models.py` / `0013_knowledge_flow.py`: token digest/membership/expiry plus document embedding status/error. `core/knowledge_tokens.py` and `management/commands/issue_knowledge_token.py` issue operator-controlled 32-random-byte tokens for active memberships (1–168 hours, default 24). Only the SHA-256 digest is stored.
- `ai_engine/app/core/authentication.py` and `main.py`: `/rag` resolves identity from current membership and rejects client identity fields; body is request UUID, nonblank message up to 12,000 characters and top_k 1–50. Response retains query/context/response and includes evidence/citations.
- RAGService/AIService share answer composition. Retrieval and chunk text loading independently scope ready records; tenant filtering precedes vector top-k. Scoped RAG ignores supplied text maps. Missing integer scope yields no stored data.
- Django processing and chunk persistence use a document lock. `documents/tasks.py` publishes embeddings only after commit; task uses current chunks and transactional upsert with three bounded retries for retryable errors. `core/tasks.py` and deferred Celery discovery expose nested jobs. No durable dispatch outbox exists.
- `embedding_service.py` / `chunk_embedding_service.py` validate batches, roll back partial writes and upsert unique chunk/model vectors. `b17d32a0e901` removes legacy orphan vectors and adds cascading chunk deletion. Reference-only metadata preserves Django ownership.
- Rollout remains: Django `0013_knowledge_flow`, enable pgvector, then Alembic `b17d32a0e901`. Existing documents need embedding before retrieval; legacy-orphan cleanup is not reversible. See README for issuance, migrations and ingestion/retry commands.

## Remaining limitations and next module

- Read tools are a server-side library, with no new endpoint or automatic invocation from `/rag`. Callers must bind a fresh registry using trusted context and credentials. Only knowledge records have grants; other agent/business tools remain pending.
- Definitions are trusted code; read-only transactions are not a Python sandbox. The database contract is PostgreSQL-specific. Chunk text has a 4,000-character cap and no text-offset continuation. Separate pages have no snapshot guarantee during concurrent reprocessing.
- Knowledge backend remains verified with plain-text fixtures and fake external providers; live Groq/Ollama/GitHub, semantic answer correctness, PDF-through-LLM execution, live Redis workers and production deployment were not tested. Frontend sign-in/knowledge requests, upload API and token-management UI remain absent.
- Lost dispatch/jobs need operator retry. Per-document locks span provider work. Context assembly has a nominal character budget; local hash embeddings are nonsemantic. Production configuration still needs hardening.
- Coordination remains standalone/sequential; ResearchAgent packages state; DataAnalyst/Operations are placeholders. Equaliator has no contradiction implementation; actions/verification are scaffolds and audit is memory-only. No persistent conversations/workflows, CI, MongoDB or MCP was added.

**NEXT: Connect coordination and quality** — explicit selection, evidence collection, Equaliator and synthesis, with supported contradiction/groundedness checks before claiming them. Preserve the completed knowledge and read-tool boundaries. See [Task.md](Task.md).
