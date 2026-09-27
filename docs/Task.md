# GROOT — Implementation roadmap

Verified: 2026-09-28. Starting HEAD was clean at `20008e6 feat: complete tenant-scoped knowledge flow`. The knowledge backend and setup modules are committed. Trusted Read-Only Tools is implemented and verified in the working tree; no commit or push was made.

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

## Completed module — Trusted Read-Only Tools

- [x] Audit all six docs and the actual agent, permission, membership, RAG, database and tool implementation before edits.
- [x] Add a small read-only Tool/ToolRegistry extension with typed schemas and guarded execution.
- [x] Implement `list_documents` and `read_document_chunks` on existing ready knowledge records with bounded cursor pagination and chunk text.
- [x] Reuse membership authentication, PermissionEngine and AgentCapabilityPolicy; verify both context IDs and recheck live access on every call.
- [x] Enforce the organization predicate in the executor and PostgreSQL read-only transactions with rollback/close on all outcomes.
- [x] Add KnowledgeAgent's request-local registry/allowlist integration and verify use through the existing Orchestrator. Keep the global registry health-only and preserve `/rag` behavior.
- [x] Verify discovery, authorized reads, denied credentials/permissions, tenant isolation, strict argument rejection, unchanged data and database rejection of hidden writes.
- [x] Run focused tests, broader regressions, lint, compilation and migration/diff checks; update all six docs. No existing tests modified, skipped or suppressed; no commit or push.

**Status: complete and verified in the working tree.** This is a server-side read-tool layer. It adds no HTTP route, automatic tool selection, general business-data grant or placeholder specialist behavior.

## Verification record — current module

| Check | Baseline `20008e6` | Final |
| --- | --- | --- |
| AI unittest discovery | 192 run; 191 passed; 1 failed | 203 run; 202 passed; same 1 failed |
| Django `test core` | 107 run; 107 passed | 119 run; 119 passed |
| New read-tool AI tests | — | 11 run; 11 passed |
| Focused AI regression selection | — | 65 run; 65 passed |
| New PostgreSQL read-tool tests | — | 12 run; 12 passed |
| Ruff 0.16.9 on changed Python files | 1 KnowledgeAgent diagnostic | Same 1; zero new diagnostics |

Django system check: 0 issues. Migration drift: No changes detected. Existing real Alembic lifecycle/drift regression: passed, no new upgrade operations. Offline migration SQL, Python compilation and `git diff --check`: passed. No schema changes or migrations applied to the developer database. No Python static type checker is configured/installed; compilation is not a type check.

The sole failing test remains `test_browser_tool.BrowserToolTests.test_extracts_information` (string versus `BrowserResult`), confirmed before edits. Existing SQLAlchemy/Starlette deprecations and malformed-PDF fixture diagnostics remain visible. No unrelated frontend or browser changes were made.

## Next unfinished module

**NEXT — Connect coordination and quality.** Connect explicit selection, evidence collection, Equaliator and synthesis. Implement supported contradiction/groundedness checks before advertising them. Reuse the trusted read-tool boundary and preserve existing knowledge behavior.

Subsequent roadmap modules remain:

1. [ ] **Connect controlled actions:** trusted risk classification, durable approvals/audit, actual tool execution and independent verification; align approval policy/executor semantics.
2. [ ] **Finish browser work when needed:** choose a scoped use case/driver, implement navigation/extraction under the same control boundary and resolve the existing browser contract failure.

## Remaining limitations and later work

- [ ] Connect the new server-side read registry to the authenticated coordination flow when that module is implemented. Definitions remain trusted code; only knowledge reads have grants. Chunk text is capped at 4,000 characters without text-offset continuation, and pagination has no snapshot guarantee during reprocessing.
- [ ] Add frontend sign-in, authenticated knowledge requests and an evidence interface. Existing gestures remain presentation, not authorization.
- [ ] Add a user-facing upload/ingestion API and token-management UI. Operators currently use Django admin, a credential command and existing processing tasks.
- [ ] Add durable dispatch/recovery if required: current on-commit publication is not an outbox. Broker/process/worker loss can need manual retries. Holding document locks across provider calls serializes work per document.
- [ ] Validate live provider behavior, semantic answer quality and actual Redis worker delivery. Current end-to-end tests use fake external providers with a real database.
- [ ] Persist conversations/workflows, checkpoint/resume, add schedules/event triggers and task activity UI when needed.
- [ ] Add domain-driven connectors/specialists, evaluation datasets, latency/cost metrics, durable tracing and CI.
- [ ] Harden production settings and deployment. Consider containers, MCP, MongoDB or distributed infrastructure only for demonstrated needs.

## Rollout requirement

Apply Django `0013_knowledge_flow`, enable pgvector, then apply Alembic `b17d32a0e901`. The Alembic migration deletes orphan vectors before adding its constraint. Existing documents begin embedding-pending; schedule `embed_document` for them before expecting retrieval. `/rag` callers must migrate to bearer tokens and the new body. See [README.md](../README.md) and [MEMORY.md](MEMORY.md) for commands and details.
