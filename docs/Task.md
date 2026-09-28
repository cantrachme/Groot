# GROOT — Implementation roadmap

Verified: 2026-09-28. Starting HEAD was clean at `a6d1b6e feat: add trusted read-only tools`. Setup, the knowledge backend and trusted read-only tools are committed. Coordination and Quality is implemented and verified in the working tree; no commit or push was made.

## Completed foundations

- [x] Django company models/admin, users/memberships, organizations, documents/chunks and migrations.
- [x] Existing SQLAlchemy engine/session/Base, AI vector model and Alembic ownership boundary.
- [x] FastAPI health and `/ai`, Groq/tool contracts, health tool and the original voice/orb/gesture prototype.
- [x] Text/PDF extraction, normalization, deterministic chunking, GitHub connector and organization-scoped event ingestion.
- [x] Local/Ollama embedding providers, vector retrieval, context assembly, agent contracts/registry/capabilities, LangChain adapter and LangGraph wrapper.
- [x] Sequential supervisor/coordinator, KnowledgeAgent; ResearchAgent state packaging and DataAnalyst/Operations scaffolds.
- [x] Equaliator/evaluator, permission/approval/action/verification contracts and in-memory audit at their documented scaffold scope.
- [x] **Make setup reproducible**, committed as `3c42b23`: dependency declarations, matching environment configuration, examples, pgvector preflight and setup instructions. Not redone in this module.

## Completed module — Finish the knowledge flow (backend), committed `20008e6`

- [x] Resolve knowledge-request identity using expiring, Django-owned membership tokens and active-user checks. Integer identities come from current membership, never a client UUID.
- [x] Require authentication on `/rag` and reject identity fields in its body; retain `/ai`'s existing prototype contract.
- [x] Filter vectors by organization and ready status before ranking/top-k; independently scope chunk text loading. No stored data is returned without scope.
- [x] Reach the existing KnowledgeAgent through `/rag`, consolidate answer composition in RAGService, and return evidence/citations plus a deterministic empty-context response.
- [x] Dispatch embedding generation after processing commits, register nested Celery tasks, serialize processing/embedding with a document lock, and persist embedding status/errors.
- [x] Upsert workflow embeddings with bounded retries, validate batches before writes and roll back failed writes. Add cascading vector cleanup and migrate away legacy orphans.
- [x] Verify plain text → processing → vectors → authenticated, organization-scoped answer using real PostgreSQL/pgvector and fake external providers.
- [x] Update all six living docs after tests/regression checks.

This completes the backend module. It does not complete the frontend identity checklist from the earlier milestone: the frontend still calls `/ai` with random UUIDs. A user sign-in/knowledge client and upload API remain explicitly pending interface work, not claimed delivered here.

## Completed module — Trusted Read-Only Tools, committed `a6d1b6e`

- [x] Audit all six docs and the actual agent, permission, membership, RAG, database and tool implementation before edits.
- [x] Add a small read-only Tool/ToolRegistry extension with typed schemas and guarded execution.
- [x] Implement `list_documents` and `read_document_chunks` on existing ready knowledge records with bounded cursor pagination and chunk text.
- [x] Reuse membership authentication, PermissionEngine and AgentCapabilityPolicy; verify both context IDs and recheck live access on every call.
- [x] Enforce the organization predicate in the executor and PostgreSQL read-only transactions with rollback/close on all outcomes.
- [x] Add KnowledgeAgent's request-local registry/allowlist integration and verify use through the existing Orchestrator. Keep the global registry health-only and preserve `/rag` behavior.
- [x] Verify discovery, authorized reads, denied credentials/permissions, tenant isolation, strict argument rejection, unchanged data and database rejection of hidden writes.
- [x] Run focused tests, broader regressions, lint, compilation and migration/diff checks; update all six docs. No existing tests modified, skipped or suppressed; no commit or push.

**Status: complete and committed in `a6d1b6e`.** This is a server-side read-tool layer. It adds no HTTP route, automatic tool selection, general business-data grant or placeholder specialist behavior.

## Completed module — Coordination and Quality

- [x] Audit current HEAD, all six living docs, existing infrastructure and tests; record clean baseline `a6d1b6e`.
- [x] Use the existing registry/supervisor/AgentGraph for multiple explicit selections, preserving original context and deterministic ordering.
- [x] Capture per-agent failures/invalid identities without aborting remaining selected agents; retain direct supervisor exception behavior by default.
- [x] Connect AgentEvaluator and Equaliator using their existing result types; add support findings, safe confidence handling and narrow literal contradiction checks.
- [x] Extend CoordinationResult with evaluation, quality, status, attributed summary, evidence/citations and limitations; preserve original KnowledgeAgent results.
- [x] Represent incomplete, partial and failed investigations explicitly. Withhold unsupported summaries and conflicting conclusions.
- [x] Verify trusted read tools retain authorization/tenant isolation, including credential revocation between agent calls and rejected mutation.
- [x] Run focused/full regressions, system/migration/Alembic/compilation/diff/lint checks; update all six docs. No existing tests weakened, edited, skipped or suppressed.

**Status: complete and verified in the working tree.** No commit or push. No new endpoint, authentication, browser behavior, action execution, frontend, database ownership or schema change.

## Verification record — current module

| Check | Baseline `a6d1b6e` | Final |
| --- | --- | --- |
| AI unittest discovery | 203 run; 202 passed; 1 failed | 232 run; 231 passed; same 1 failed |
| Django `test core` | 119 run; 119 passed | 126 run; 126 passed |
| New coordination/quality AI tests | — | 29 run; 29 passed |
| Focused AI regression selection | — | 103 run; 103 passed |
| New PostgreSQL coordination tests | — | 7 run; 7 passed |
| Ruff 0.16.9, changed Python files | 1 Equaliator import-order diagnostic | 0 diagnostics; import sorted while editing |

Django system check: 0 issues. Migration drift: No changes detected. Existing real Alembic lifecycle/drift regression: passed, no new upgrade operations. Offline migration SQL, Python compilation and `git diff --check`: passed. No schema changes or migrations applied to the developer database. No static Python type checker is configured/installed.

The sole failing test remains `test_browser_tool.BrowserToolTests.test_extracts_information` (string versus BrowserResult), confirmed before edits. The 16 existing Ruff diagnostics in untouched KnowledgeAgent/models files remain. SQLAlchemy/Starlette deprecations and malformed-PDF fixture diagnostics remain visible. No new regression failures.

## Next unfinished module

**NEXT — Connect controlled actions.** Add trusted risk classification, durable approvals/audit, actual tool execution and independent verification; align approval policy/executor semantics. Preserve the completed knowledge, read-tool and coordination boundaries. No action capability was added by the current module.

Subsequent roadmap module:

1. [ ] **Finish browser work when needed:** choose a scoped use case/driver, implement navigation/extraction under the same control boundary and resolve the existing browser contract failure.

## Remaining limitations and later work

- [ ] Add an authenticated investigation client/endpoint if needed. Coordination is currently server-side with explicit selections and trusted context; agents can use the existing guarded read registry. No parallel execution, retries, persistence or autonomous selection is implemented.
- [ ] Expand quality verification only with tested semantics/evaluation data. Current checks cover literal statement support, citation references and explicit opposite-polarity clauses; paraphrases, numerical reasoning and independent truth remain unverified.
- [ ] Read-tool definitions remain trusted code; only knowledge reads have grants. Chunk text is capped at 4,000 characters without text-offset continuation, and pagination has no snapshot guarantee during reprocessing.
- [ ] Add frontend sign-in, authenticated knowledge requests and an evidence interface. Existing gestures remain presentation, not authorization.
- [ ] Add a user-facing upload/ingestion API and token-management UI. Operators currently use Django admin, a credential command and existing processing tasks.
- [ ] Add durable dispatch/recovery if required: current on-commit publication is not an outbox. Broker/process/worker loss can need manual retries. Holding document locks across provider calls serializes work per document.
- [ ] Validate live provider behavior, semantic answer quality and actual Redis worker delivery. Current end-to-end tests use fake external providers with a real database.
- [ ] Persist conversations/workflows, checkpoint/resume, add schedules/event triggers and task activity UI when needed.
- [ ] Add domain-driven connectors/specialists, evaluation datasets, latency/cost metrics, durable tracing and CI.
- [ ] Harden production settings and deployment. Consider containers, MCP, MongoDB or distributed infrastructure only for demonstrated needs.

## Rollout requirement

Apply Django `0013_knowledge_flow`, enable pgvector, then apply Alembic `b17d32a0e901`. The Alembic migration deletes orphan vectors before adding its constraint. Existing documents begin embedding-pending; schedule `embed_document` for them before expecting retrieval. `/rag` callers must migrate to bearer tokens and the new body. See [README.md](../README.md) and [MEMORY.md](MEMORY.md) for commands and details.
