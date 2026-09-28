# GROOT — Compact project memory

Verified: 2026-09-28. Starting HEAD was clean at `a6d1b6e feat: add trusted read-only tools`. Setup, the knowledge backend and trusted read-only tools are committed. Coordination and Quality is implemented and verified in the working tree; no commit or push was made.

## Current architecture and completed modules

Django owns users, memberships, company/document/chunk data, knowledge tokens and document readiness. SQLAlchemy/Alembic own vectors using the existing engine/Base/SessionLocal/get_db. AI reads Django-owned records through scoped queries without adding their tables to Base.metadata. Frontend remains the voice/orb/gesture prototype calling `/ai`.

- Setup: compatible dependency declarations, shared environment-based PostgreSQL/Redis configuration, example environments, read-only pgvector preflight and setup instructions.
- Knowledge backend: authenticated `/rag` → KnowledgeAgent → shared RAGService → tenant-scoped vector/text retrieval → answer, evidence and citation IDs. Empty authorized context returns a fixed insufficient-context response without an LLM call. Processing dispatches embeddings after commit; document locks and cascading chunk foreign keys coordinate replacement/deletion.
- Trusted Read-Only Tools (committed `a6d1b6e`): private registry for ready-document inventory and ordered chunk inspection. Each execution checks live membership, both integer IDs, PermissionEngine, AgentCapabilityPolicy, tenant scope and PostgreSQL read-only transaction semantics. Direct tool use and the existing Orchestrator are verified. `/ai` remains health-only; `/rag` still uses its existing RAG path.
- **Coordination and Quality:** existing coordinator now returns ordered agent outputs, AgentEvaluator evaluations, Equaliator assessment, overall status, attributed summary, evidence/citations and explicit limitations. Agent failures are isolated; original context is preserved. No endpoint, new authentication, write/action dispatch, browser or frontend capability was added.

## Files changed in this module

| File | Implemented change |
| --- | --- |
| `ai_engine/app/agents/coordinator.py` | Extended existing CoordinationResult; evaluator/Equaliator integration; status, attribution, evidence/citation aggregation and limitations |
| `ai_engine/app/agents/supervisor.py` | Optional per-agent failure capture and result-identity validation; default direct-call exception behavior preserved |
| `ai_engine/app/evaluation/agent_evaluator.py` | Existing four metrics plus groundedness; findings, invalid confidence handling and stricter passed flag |
| `ai_engine/app/evaluation/support.py` | Shared literal statement, usable evidence, citation reference and confidence checks |
| `ai_engine/app/equaliator/evaluator.py` | Shared support findings, errors/invalid confidence completion gates, evidence coverage, bounded opposite-polarity conflicts and valid-score averaging |
| `ai_engine/tests/test_coordination_quality.py` | 29 new unit tests covering coordination, quality, KnowledgeAgent results and compatibility |
| `backend/core/test_coordination_quality.py` | 7 real PostgreSQL/pgvector tests coordinating knowledge and guarded reads, including denied access and mutation rejection |
| `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/RULES.md`, `docs/DESIGN.md`, `docs/Task.md`, `docs/MEMORY.md` | Verified capability, architecture, rules, design, roadmap and results |

No existing test files, dependencies, models, migrations, HTTP routes, read-tool permission checks, frontend files, browser code or action scaffolds were changed.

## Coordination design decisions and operational contract

1. Keep `MultiAgentCoordinator.execute(selection, context)` as the entry point. AgentSelection, the registry, supervisor and existing one-node AgentGraph remain in use. Every agent receives the same original AgentContext object, including IDs/request/task/permissions/state. No previous output replaces the query or task. Shared state can contain a live Session; trusted agents must leave it unchanged.
2. The coordinator opts into `AgentSupervisor.execute(..., capture_failures=True)`. Each selected name has one ordered result; unknown agents, raised Exceptions, wrong result types or mismatched result names become failed AgentResults and execution continues. Raw exception messages are omitted; the error retains the exception class name. Direct supervisor use defaults to existing raise behavior. BaseExceptions such as interrupts are not captured.
3. Extend CoordinationResult instead of duplicating result/evaluation models. Original selection/results remain, and added fields have defaults to preserve two-argument construction. `evaluations` uses EvaluationResult/MetricScore; `quality` uses EqualiatorResult/AgentAssessment. Additional fields are `status`, `summary`, `evidence`, `citations`, `limitations`.
4. Original results, including failed or unsupported evidence, remain intact. Aggregate evidence and list/tuple citation collections are flattened in selection order with duplicates preserved. Per-agent results preserve provenance, KnowledgeAgent similarity scores, citation IDs and metadata. Invalid citation containers remain in the original data and generate findings; they are not treated as valid aggregate citations.
5. AgentEvaluator reports success, reported confidence, evidence availability and errors with actual supplied evidence/error counts. New `groundedness` is 1 for passed literal statement/citation support, 0 for support findings, null for failed results or unavailable text checks. `passed` requires reported success and no errors/support/invalid-confidence findings. Findings retain explicit agent errors, and metadata identifies the agent.
6. Evidence is usable if it is a nonblank string reference or a dictionary with nonblank `text`, `source` or `url`. Text verification uses dictionaries' `text`. Split summary/evidence at sentence boundaries/newlines, normalize case/whitespace/terminal punctuation, and require each summary statement to equal an evidence statement. Paraphrases are conservatively unverified, not proved false; substrings inside a negated statement do not count. Arbitrary data fields and source truth are not evaluated.
7. Explicit citations must be lists/tuples of string or integer references matching evidence strings or `document_chunk_id`/`source`/`url` fields with the same type; booleans do not substitute for IDs. Blank summaries/evidence, unmatched statements and unmatched citations are findings. Source references alone retain the legacy structural support behavior, but cannot complete the coordinator's overall investigation.
8. Confidence is optional. Missing values remain null. Values must be actual int/float, finite and within 0–1; bool/string/NaN/infinity/huge/out-of-range values become findings and null metric values. Equaliator averages only valid confidence from successful error-free results. It measures reported confidence, not calibrated correctness; no low-confidence threshold is invented.
9. Equaliator blocks its preliminary completion on failed/error-bearing/invalid-confidence results, support findings or detected contradictions. Evidence quality is HIGH only when every result succeeds without errors and supplies usable evidence. Agreement compares normalized summary wording among successful error-free results: NO_RESULTS/INSUFFICIENT/HIGH/PARTIAL, or CONFLICT when the implemented polarity pattern matches.
10. Contradiction checking is deliberately narrow: identical clauses using `is/are/was/were/has/have/had/can/will/does/do/did` with versus without `not`, excluding `not only`. Broader semantic, numeric and causal conflicts are not inferred. Conflicts are deterministic findings in result order; they do not prove which agent is correct.
11. Overall status precedence: no results → incomplete; no successful error-free results → failed; mixed execution outcomes → partial; all evaluations passed plus Equaliator preliminary completion plus evidence text for every result → complete; otherwise incomplete. Thus the legacy Equaliator structural completion flag alone is not the overall status. Missing confidence alone is a reported limitation, not a failure. Empty KnowledgeAgent retrieval is incomplete despite its successful-execution flag.
12. Synthesis attributes original passed summaries with evidence text, in order. It adds no new LLM-generated claims. Failed/unsupported summaries are omitted; any detected conflict withholds the combined conclusion. When no summary qualifies, report no supported conclusion. Limitations carry findings, absent confidence/text and the heuristic scope of the checks.
13. This is a server-side coordinator, not an authentication endpoint. Existing callers authenticate KnowledgeAgent requests and supply trusted context. Bound read tools continue to recheck credentials, membership, identity, allowlist and permissions on each execution. The coordinator creates no grants, changes no tenant scope and never dispatches tool-call metadata, actions, additional agents or browser work.

## Retained read-tool decisions and contracts — committed `a6d1b6e`

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

Python: existing `.venv/bin/python` (3.14.4). Commands are from repository root unless specified. Baselines ran on clean `a6d1b6e` before changes. Existing tests were not edited, skipped or suppressed.

| Check | Command / method | Exact result |
| --- | --- | --- |
| Baseline AI | `.venv/bin/python -m unittest discover -s ai_engine/tests` | 203 run; 202 passed; 1 failed |
| Baseline Django | `../.venv/bin/python manage.py test core --noinput` from `backend/` | 119 run; 119 passed |
| Focused new AI | `.venv/bin/python -m unittest ai_engine.tests.test_coordination_quality` | 29 run; 29 passed |
| Focused AI regression | `.venv/bin/python -m unittest ai_engine.tests.test_coordination_quality ai_engine.tests.test_multi_agent_coordinator ai_engine.tests.test_agent_supervisor ai_engine.tests.test_agent_graph ai_engine.tests.test_agent_evaluator ai_engine.tests.test_equaliator ai_engine.tests.test_evaluation_models ai_engine.tests.test_knowledge_agent ai_engine.tests.test_read_only_tools ai_engine.tests.test_permission_engine` | 103 run; 103 passed |
| Focused PostgreSQL | `../.venv/bin/python manage.py test core.test_coordination_quality --noinput` from `backend/` | 7 run; 7 passed |
| Final full AI regression | `.venv/bin/python -m unittest discover -s ai_engine/tests` | 232 run; 231 passed; same 1 failure |
| Final full Django regression | `../.venv/bin/python manage.py test core --noinput` from `backend/` | 126 run; 126 passed |
| Django checks | `.venv/bin/python backend/manage.py check` | 0 issues, 0 silenced |
| Django migration drift | `.venv/bin/python backend/manage.py makemigrations --check --dry-run` | No changes detected |
| Python compilation | `.venv/bin/python -m compileall -q ai_engine/app ai_engine/alembic backend/core backend/config` | Passed |
| Offline Alembic | `.venv/bin/python -m alembic -c ai_engine/alembic.ini upgrade head --sql` | Both existing migrations generated successfully |
| Live migration checks | Django temporary test DB plus Alembic; existing knowledge-flow downgrade/orphan seed/upgrade/drift regression within full Django suite | Passed; no new upgrade operations detected |
| Changed-file lint | Ruff 0.16.9 `check` on the 7 Python files listed above; HEAD versions of 4 existing files checked via `git show HEAD:<path>` piped to Ruff `--stdin-filename <path> -` | Baseline: 1 Equaliator I001; final: 0 diagnostics. Import order corrected while editing; no suppressions |
| Known untouched-file lint | Ruff `check --output-format json backend/core/models.py ai_engine/app/agents/knowledge.py` | 16 existing diagnostics: 14 RUF012, 1 PIE794, 1 ISC004; files unchanged |
| Patch formatting | `git diff --check` | Passed |

Ruff binary `/tmp/groot-knowledge-lint/bin/ruff` was already available; no dependencies were installed or changed. No configured/installed mypy or pyright was found, so no static type check is claimed. Frontend checks were not applicable.

New PostgreSQL tests explicitly target only the Django-selected `test_` database, apply existing Django/Alembic migrations there, clean up AI tables and dispose the test engine. They exercise real KnowledgeAgent/RAG/pgvector plus registered readers using the unchanged guarded read registry. Only embedding/LLM providers are fake. Coverage includes preserved evidence/citations, excluded foreign data, denied agent/context permissions and identities, invalid/expired/revoked tokens, revocation between agents, empty foreign reads, rejected mutation and unchanged rows. No migrations were applied to the developer database.

## Pre-existing failures and visible diagnostics

- `test_browser_tool.BrowserToolTests.test_extracts_information` expects `"page heading"` but receives `BrowserResult(action='extract_information', data={'query': 'page heading'})`. Identical baseline and final failure; browser remains a stub.
- Untouched lint issues were rechecked: KnowledgeAgent ISC004 implicit-string concatenation; models PIE794 duplicate field and 14 RUF012 mutable-class-list diagnostics. All 16 remain. Changed files have zero diagnostics; the Equaliator's previous import-order diagnostic was resolved while editing its imports. No rules or tests were suppressed.
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

- Coordination is a server-side API with explicit selections. No HTTP investigation route, authentication extension, parallelism, retry planner, workflow persistence or automatic follow-up selection was added. Registered agents and context are trusted; state is shared and agents must leave it unchanged. Direct low-level KnowledgeAgent calls retain the existing caller-authentication responsibility.
- Groundedness checks literal summary text and citation references only. Valid paraphrases may remain unverified. Evidence labels without text cannot complete an investigation; matching supplied text is not independent truth/source verification. Broader semantic/numerical contradiction detection is absent. Confidence is reported data, not calibrated probability. Overall status is stricter than the legacy Equaliator structural completion flag.
- Returned tool-call metadata is preserved but never executed by coordination. Read-tool definitions remain trusted code; read-only transactions are not a Python sandbox. Their PostgreSQL contract, 4,000-character chunk cap and lack of pagination snapshot/text-offset continuation remain unchanged.
- Live Groq/Ollama/GitHub, semantic answer correctness, PDF-through-LLM execution, live Redis workers and production deployment were not tested. Frontend sign-in/knowledge requests, upload API and token-management UI remain absent.
- Lost dispatch/jobs need operator retry. Per-document locks span provider work. Context assembly has a nominal character budget; local hash embeddings are nonsemantic. Production configuration still needs hardening.
- ResearchAgent packages supplied state; DataAnalyst/Operations remain placeholders and their unsupported summaries do not complete investigations. Actions/verification are scaffolds; audit is memory-only. No persistent conversations/workflows, CI, MongoDB or MCP was added.

**NEXT: Connect controlled actions** — trusted risk classification, durable approvals/audit, actual execution and independent verification, with approval-policy/executor alignment. Preserve the completed knowledge, read-tool and coordination boundaries. Browser work remains a later module. See [Task.md](Task.md).
