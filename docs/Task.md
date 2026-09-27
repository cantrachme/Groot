# GROOT — Implementation roadmap

Verified: 2026-09-28. Starting HEAD was clean at `3c42b23 feat: make setup reproducible`. This module's changes are uncommitted. All six living docs and existing implementation were audited before edits; no commits or pushes were made.

## Completed foundations

- [x] Django company models/admin, users/memberships, organizations, documents/chunks and migrations.
- [x] Existing SQLAlchemy engine/session/Base, AI vector model and Alembic ownership boundary.
- [x] FastAPI health and `/ai`, Groq/tool contracts, health tool and the original voice/orb/gesture prototype.
- [x] Text/PDF extraction, normalization, deterministic chunking, GitHub connector and organization-scoped event ingestion.
- [x] Local/Ollama embedding providers, vector retrieval, context assembly, agent contracts/registry/capabilities, LangChain adapter and LangGraph wrapper.
- [x] Sequential supervisor/coordinator, KnowledgeAgent; ResearchAgent state packaging and DataAnalyst/Operations scaffolds.
- [x] Equaliator/evaluator, permission/approval/action/verification contracts and in-memory audit at their documented scaffold scope.
- [x] **Make setup reproducible**, committed as `3c42b23`: dependency declarations, matching environment configuration, examples, pgvector preflight and setup instructions. Not redone in this module.

## Completed module — Finish the knowledge flow (backend)

- [x] Resolve knowledge-request identity using expiring, Django-owned membership tokens and active-user checks. Integer identities come from current membership, never a client UUID.
- [x] Require authentication on `/rag` and reject identity fields in its body; retain `/ai`'s existing prototype contract.
- [x] Filter vectors by organization and ready status before ranking/top-k; independently scope chunk text loading. No stored data is returned without scope.
- [x] Reach the existing KnowledgeAgent through `/rag`, consolidate answer composition in RAGService, and return evidence/citations plus a deterministic empty-context response.
- [x] Dispatch embedding generation after processing commits, register nested Celery tasks, serialize processing/embedding with a document lock, and persist embedding status/errors.
- [x] Upsert workflow embeddings with bounded retries, validate batches before writes and roll back failed writes. Add cascading vector cleanup and migrate away legacy orphans.
- [x] Verify plain text → processing → vectors → authenticated, organization-scoped answer using real PostgreSQL/pgvector and fake external providers.
- [x] Update all six living docs after tests/regression checks.

This completes the backend module. It does not complete the frontend identity checklist from the earlier milestone: the frontend still calls `/ai` with random UUIDs. A user sign-in/knowledge client and upload API remain explicitly pending interface work, not claimed delivered here.

## Verification record

| Check | Baseline `3c42b23` | Final |
| --- | --- | --- |
| AI unittest discovery | 173 run; 172 passed; 1 failed | 192 run; 191 passed; same 1 failed |
| Django `test core` | 84 run; 84 passed | 107 run; 107 passed |
| Focused AI selection | — | 55 run; 55 passed, including 19 new tests |
| Focused Django knowledge module | — | 23 run; 23 passed, including 11 database integration tests |
| Ruff 0.16.9 on changed Python files | 23 diagnostics on HEAD versions | 16 pre-existing diagnostics; zero new diagnostics |

Additional checks passed: Django system check (0 issues), migration drift (No changes detected), Python compilation, offline Alembic SQL, and `git diff --check`. Integration tests applied Django/Alembic migrations in a temporary database and verified Alembic downgrade → orphan seed → upgrade → drift check. The existing developer database was not migrated. No existing tests were edited, skipped or suppressed.

The sole test failure is `test_browser_tool.BrowserToolTests.test_extracts_information`: a pre-existing string-versus-`BrowserResult` mismatch. Remaining lint diagnostics are 15 existing model warnings (duplicate field/mutable class lists) and one existing KnowledgeAgent string-concatenation diagnostic. SQLAlchemy deprecation and malformed-PDF diagnostics remain visible; HTTP tests also expose the installed Starlette/httpx deprecation. No static Python type checker is configured or installed in the project; compilation is not a substitute for it.

## Next unfinished module

**NEXT — Add useful read-only tools.** Implement one real business-data query or research source behind an allowed tool and trusted authorization. Replace the relevant placeholder agent output with meaningful results or failures. Preserve the completed knowledge flow; do not extend the unauthenticated `/ai` demo to company data without a trusted execution boundary.

Subsequent roadmap modules remain:

1. [ ] **Connect coordination and quality:** explicit selection, evidence collection, Equaliator and synthesis; supported contradiction/groundedness checks before advertising them.
2. [ ] **Connect controlled actions:** trusted risk classification, durable approvals/audit, actual tool execution and independent verification; align approval policy/executor semantics.
3. [ ] **Finish browser work when needed:** choose a scoped use case/driver, implement navigation/extraction under the same control boundary and resolve the existing browser contract failure.

## Remaining limitations and later work

- [ ] Add frontend sign-in, authenticated knowledge requests and an evidence interface. Existing gestures remain presentation, not authorization.
- [ ] Add a user-facing upload/ingestion API and token-management UI. Operators currently use Django admin, a credential command and existing processing tasks.
- [ ] Add durable dispatch/recovery if required: current on-commit publication is not an outbox. Broker/process/worker loss can need manual retries. Holding document locks across provider calls serializes work per document.
- [ ] Validate live provider behavior, semantic answer quality and actual Redis worker delivery. Current end-to-end tests use fake external providers with a real database.
- [ ] Persist conversations/workflows, checkpoint/resume, add schedules/event triggers and task activity UI when needed.
- [ ] Add domain-driven connectors/specialists, evaluation datasets, latency/cost metrics, durable tracing and CI.
- [ ] Harden production settings and deployment. Consider containers, MCP, MongoDB or distributed infrastructure only for demonstrated needs.

## Rollout requirement

Apply Django `0013_knowledge_flow`, enable pgvector, then apply Alembic `b17d32a0e901`. The Alembic migration deletes orphan vectors before adding its constraint. Existing documents begin embedding-pending; schedule `embed_document` for them before expecting retrieval. `/rag` callers must migrate to bearer tokens and the new body. See [README.md](../README.md) and [MEMORY.md](MEMORY.md) for commands and details.
