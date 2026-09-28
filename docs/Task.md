# GROOT — Implementation roadmap

Verified: 2026-09-28. Starting HEAD was clean at `0d7d2da feat: add coordination and quality`. Setup, the knowledge backend, trusted read-only tools, and Coordination and Quality are committed. Controlled Actions is implemented and verified in the working tree; nothing was committed or pushed.

## Completed foundations

- [x] Django company models/admin, users/memberships, organizations, documents/chunks and migrations.
- [x] Existing SQLAlchemy engine/session/Base, AI vector model and Alembic ownership boundary.
- [x] FastAPI health and `/ai`, Groq/tool contracts, health tool and the original voice/orb/gesture prototype.
- [x] Text/PDF extraction, normalization, deterministic chunking, GitHub connector and organization-scoped event ingestion.
- [x] Local/Ollama embedding providers, vector retrieval, context assembly, agent contracts/registry/capabilities, LangChain adapter and LangGraph wrapper.
- [x] Sequential supervisor/coordinator, KnowledgeAgent; ResearchAgent state packaging and DataAnalyst/Operations scaffolds.
- [x] Original Equaliator/evaluator, permission/approval/action/verification contracts and in-memory audit; connected implementations are recorded in the completed modules below.
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

## Completed module — Coordination and Quality, committed `0d7d2da`

- [x] Audit current HEAD, all six living docs, existing infrastructure and tests; record clean baseline `a6d1b6e`.
- [x] Use the existing registry/supervisor/AgentGraph for multiple explicit selections, preserving original context and deterministic ordering.
- [x] Capture per-agent failures/invalid identities without aborting remaining selected agents; retain direct supervisor exception behavior by default.
- [x] Connect AgentEvaluator and Equaliator using their existing result types; add support findings, safe confidence handling and narrow literal contradiction checks.
- [x] Extend CoordinationResult with evaluation, quality, status, attributed summary, evidence/citations and limitations; preserve original KnowledgeAgent results.
- [x] Represent incomplete, partial and failed investigations explicitly. Withhold unsupported summaries and conflicting conclusions.
- [x] Verify trusted read tools retain authorization/tenant isolation, including credential revocation between agent calls and rejected mutation.
- [x] Run focused/full regressions, system/migration/Alembic/compilation/diff/lint checks; update all six docs. No existing tests weakened, edited, skipped or suppressed.

**Status: complete and committed in `0d7d2da`.** That module added no endpoint, authentication, browser behavior, action execution, frontend, database ownership or schema change.

## Completed module — Controlled Actions

- [x] Audit clean HEAD `0d7d2da`, all six living documents and existing implementations/tests; establish AI and Django baselines.
- [x] Add a trusted strict action registry and one ControlledActionPipeline reusing PermissionEngine, AgentCapabilityPolicy, ApprovalPolicy, ActionExecutor, ActionVerifier and AuditLog.
- [x] Enforce role/context/agent permission and matching user/tenant/agent identity; keep knowledge grants read-only.
- [x] Use trusted READ/LOW/HIGH_IMPACT classification; automatic READ/LOW and separate human approval for HIGH_IMPACT. Ignore incoming approval flags and reject invalid risk.
- [x] Snapshot action parameters, bind approval/resumption to the original context, recheck execution grants, and keep denial and completed outcomes terminal.
- [x] Execute registered callbacks through the existing executor and verify every attempt through the existing verifier; failed execution/verification stays failed.
- [x] Persist safe decision events in the existing audit log's optional local journal, required for this pipeline. Keep secrets/payloads/raw errors out of audit and controlled results; fail closed on required audit writes.
- [x] Add explicit coordinator submission using the existing supervisor registry. Investigations/tool-call metadata still never trigger actions automatically.
- [x] Verify 34 focused tests plus existing regressions, lint, compilation, system, migration and diff checks; update all six docs.

**Status: complete and verified in the working tree; no commit or push.** Decisions persist, but pending payloads/approvals cannot resume after restart. No domain/external action, approval endpoint, authentication extension, browser, frontend, dependency or schema change was added.

## Verification record — current module

| Check | Baseline `0d7d2da` | Final |
| --- | --- | --- |
| Full AI unittest discovery | 232 run; 231 passed; 1 failed | 266 run; 265 passed; same 1 failed |
| Full Django `test core` | 126 run; 126 passed | 126 run; 126 passed |
| New controlled-action tests | — | 34 run; 34 passed |
| Focused AI regression selection | — | 100 run; 100 passed |
| Ruff 0.16.9, changed Python files | 0 on 6 existing files | 0 on all 9 changed/new files |

Django system check: 0 issues. Migration drift: No changes detected. Real Alembic lifecycle/drift regression: passed, no new upgrade operations. Offline migration SQL, Python compilation and `git diff --check`: passed. No migrations were applied to the developer database. No configured/installed Python type checker was found.

The sole failure remains `test_browser_tool.BrowserToolTests.test_extracts_information` (string versus BrowserResult), confirmed before edits. The 16 existing Ruff diagnostics in untouched KnowledgeAgent/models files remain. SQLAlchemy/Starlette deprecations and malformed-PDF fixture messages remain visible. No new regressions; existing tests were not edited, weakened or suppressed. Files and commands are recorded in [MEMORY.md](MEMORY.md).

## Next unfinished module

**NEXT — Finish browser work when needed.** Choose a scoped use case/driver, then implement navigation/extraction under the existing controlled boundary and resolve the pre-existing browser contract failure. Browser work was excluded from Controlled Actions.

## Remaining limitations and later work

- [ ] Add trusted host approval/authentication interfaces and domain action implementations when required. Current controlled execution is an internal API with an empty default registry; callers establish human identity and current grants.
- [ ] Add approval expiry, journal operational hardening and durable executable workflow recovery if required. Decisions persist locally; pending payloads/approvals are lost on restart. No distributed exactly-once guarantee, automatic rollback or retry of ambiguous effects is provided. Callbacks must enforce their own tenant-scoped domain access.
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
