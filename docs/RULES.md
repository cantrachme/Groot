# GROOT — Engineering rules

Verified: 2026-09-28. Starting HEAD was clean at `0d7d2da feat: add coordination and quality`. Setup, the knowledge backend, trusted read-only tools, and Coordination and Quality are committed. Controlled Actions is implemented and verified in the working tree; nothing was committed or pushed.

## Preserve ownership and service boundaries

1. Keep business data, memberships, credentials and document status in Django with Django migrations. Keep vectors in the existing SQLAlchemy/Alembic foundation; reuse `Base`, `SessionLocal` and `get_db`.
2. Preserve Alembic's reflected-table ownership filter. A Django table referenced by the embedding foreign key must remain outside AI-owned metadata. Run Django migrations before Alembic migrations on a fresh database.
3. Keep native provider, tool, agent context and result contracts. LangChain is an adapter; LangGraph is an execution wrapper. Selection/execution, Equaliator quality assessment and evaluation metrics remain separate concerns.
4. Keep organization-scoped business uniqueness and event idempotency. Do not change unrelated agent scaffolds, frontend behavior, browser contracts or setup dependencies while extending knowledge.

## Enforced knowledge identity and data access

- `/rag` requires an unexpired bearer token bound to a current Django membership and active user. Persist only the token digest. Resolve integer user/organization IDs and role in the database; reject identity fields in the HTTP body.
- Membership tokens authorize organization knowledge reads only. Do not reuse them as action approval, general tool permission or administrator authentication. Both existing membership roles may read knowledge in their organization.
- Keep UUID request IDs and prototype `/ai` identity contracts. Do not coerce random UUIDs to Django primary keys. Missing integer organization scope must not return stored chunks/vectors.
- Apply tenant and ready-state predicates in both similarity search and chunk text loading. Scope must precede ranking/top-k. For scoped RAG, supplied text maps must not bypass the authorized database lookup.
- Keep SQL parameterized. Do not log bearer credentials, raw connection parameters or provider secrets. Frontend public configuration must not contain knowledge tokens or provider credentials.
- Preserve evidence IDs/text/similarity. Reuse the single `RAGService.answer` composition. With no assembled authorized context, return an explicit insufficient-context answer without an LLM call.

## Enforced trusted read-tool contracts

- Build a private registry for each trusted request; bind credentials, agent and context on the server. Never put a credential or caller-controlled tenant/permission in tool arguments. Do not share a bound registry between users or register it globally for `/ai`.
- Execute through `ReadOnlyTool`: strict Pydantic parameters reject extra fields, coercion, SQL, mutation operations and identity overrides. Definitions must use a SELECT and `knowledge.read`; the read registry rejects general tools and overridden executors.
- Authenticate the token on **every execution**, including direct calls and the existing orchestrator path. The current membership must match both integer context IDs; UUIDs and booleans cannot stand in for database IDs.
- Derive the knowledge grant only from current `admin`/`member` membership roles. Unknown roles fail closed. Require both PermissionEngine authorization and AgentCapabilityPolicy authorization with an explicit mapping; context permissions alone cannot grant data access.
- Start a fresh session with `SET TRANSACTION READ ONLY` before authentication or data queries. Always roll back and close it; never commit or reuse a caller's pending-write session. A rejected database write must remain an error, not trigger a writable fallback.
- Apply organization filtering centrally before LIMIT. Document tools additionally require ready extraction and embeddings. Foreign, missing and unready documents all produce an empty chunk page.
- Keep document pages at 1–100 rows, chunk pages at 1–20 rows, and chunk text at 4,000 characters with `truncated`. Preserve chunk/document IDs and ordered continuation cursors. Exclude storage keys, error details, credentials and personal fields.
- Extensions are trusted source code: use the guarded executor, scoped projections, bounded argument models and focused isolation/mutation tests. Do not accept model-supplied SQL or treat Python definitions as sandboxed untrusted plugins. New data domains require their own trusted grants; knowledge tokens confer no general business/action authority.

## Enforced coordination and quality contracts

- Use the existing registry, supervisor and AgentGraph with explicit selection. Preserve selection order and pass the original context/request to each agent; do not replace its task/query with another agent's output or inject earlier results into state. Registered agents remain trusted Python and must not mutate shared context state.
- Coordinator execution captures each agent's exception or invalid result identity as a failed AgentResult and continues. Keep failure type but omit raw exception messages. Direct supervisor execution preserves its existing exception behavior unless capture is explicitly requested.
- Reuse CoordinationResult, AgentResult, EvaluationResult/MetricScore and EqualiatorResult/AgentAssessment. Preserve original result evidence, citations, errors and metadata; aggregate collections retain ordering and duplicates. Failed evidence remains attributable to its individual failed result, not promoted into a conclusion.
- Run AgentEvaluator on every result and Equaliator on the ordered result tuple. Missing confidence stays null; invalid type/range/nonfinite confidence is a finding and must not contaminate averaged scores. Result errors block passed evaluation even when success is true.
- Treat missing/blank evidence, unmatched summary statements and invalid citation references as support findings. Literal normalization checks are conservative: unverified paraphrases are not proved false, and matching text is not independently verified truth. String/source labels alone cannot complete an overall investigation.
- Detect only the implemented contradiction pattern: identical explicit clauses with opposite `not` polarity. Do not advertise general semantic, numerical or causal contradiction detection. Wording agreement and reported confidence are separate from correctness.
- Mark mixed execution outcomes partial, all unsuccessful/error-bearing outcomes failed, and empty/unsupported/conflicting investigations incomplete. Complete requires every result to pass the current checks with evidence text. Missing confidence alone is reported as a limitation rather than assigned an invented score.
- Build an attributed summary only from passed outputs with evidence text. Detected conflicts withhold combined conclusions. Preserve findings/limitations; do not fabricate a synthesis or dispatch returned tool calls, actions or additional agents.
- Coordination does not authenticate an untrusted context or create grants. Existing callers authenticate KnowledgeAgent requests; existing read tools still perform their own live authorization. Keep the global `/ai` registry health-only.

## Enforced controlled-action contracts

- Enter through ControlledActionPipeline; coordinator action submission is an explicit host call. Investigation summaries, quality scores, returned tool-call metadata, gestures and incoming `approved` flags cannot authorize execution.
- Register trusted action/tool identifiers, Permission, ActionRisk, strict extra-forbidding parameter schema, handler and independent checker. Risk comes from registration. Reject invalid risks; the existing policy keeps READ/LOW automatic and HIGH_IMPACT approval-required.
- Require matching user/organization/agent authority, the PermissionEngine role grant and AgentCapabilityPolicy's explicit tool mapping, context grant and allowlist. Recheck current supplied authority before executing a pending approved action. Knowledge credentials confer no action grant.
- Bind approval to the original operation, user/organization/request/agent and serialized parameter snapshot. `decide` requires a same-tenant human host context with `actions.approve`; the host authenticates the human. Approval alone does not execute; denial is terminal. Never accept untrusted roles or the human marker from a model or request body as authenticated authority.
- Route each execution through the existing ActionExecutor and ActionVerifier. Only literal boolean callback success counts. Failed execution cannot be upgraded by a checker; failed verification stays failed. Handler/checker exceptions yield safe failures. Trusted implementations must scope domain reads/writes to the preserved organization and user context; Python callbacks are not sandboxed.
- Require AuditLog's local journal for the pipeline. Record request/authorization/risk/approval/execution/verification decisions, identities and timestamps. Complete mandatory pre-execution writes before invoking the callback. If auditing fails after execution, still verify, return `audit_failed` and do not automatically execute again.
- Keep parameters, task/state, raw output and raw exception text out of controlled results and audit. Registered identifiers and static result/error metadata are the only descriptive values returned. Existing low-level legacy executor behavior is retained for compatibility; it is not a safe entry point for untrusted callers.
- Prevent duplicate execution within an instance, including concurrent/reentrant requests. Claim the operation before calling a handler and retain terminal outcomes. Restart rejects old operations: durable decision records are not executable approval recovery. No rollback or distributed exactly-once guarantee is claimed.
- Provision a journal owned by one application process. Do not claim tamper resistance, retention/rotation, approval expiry, a user-facing approval flow or crash recovery; these are not implemented. No default domain/external actions are registered.

## Enforced document/vector lifecycle

- Preserve extraction results and deterministic chunk ordering/replacement. Embedding readiness is separate from extraction readiness; only documents with both states ready may be retrieved.
- Lock the Django document row during processing/chunk replacement and during embedding generation/persistence. Enqueue embeddings only after successful processing commits. A rollback or extraction failure must not publish an embedding job.
- Keep the AI-owned chunk foreign key with `ON DELETE CASCADE`; reprocessing/deletion must remove old embeddings. Do not remove the constraint to bypass invalid references. Legacy orphan cleanup in the migration is intentional and not reversible.
- Use `DocumentChunkEmbeddingService.upsert_chunks` for workflow retries. Validate all vector batches before writes and commit upserts atomically; roll back partial writes on failure. Preserve uniqueness by chunk/model, and filter searches by the configured model/dimensions.
- Record embedding success/failure in Django after the AI operation. Runtime/provider and SQLAlchemy failures have at most three automatic retries with backoff. Broker/configuration/validation failures require operator recovery. Do not imply a durable outbox or guaranteed crash recovery exists.
- Keep Celery autodiscovery deferred until Django is ready and keep nested ingestion/document/embedding tasks registered. Reuse the shared provider factory in query and worker paths.

## Setup contracts retained from `3c42b23`

Both Python services locate the root `.env` independently of launch directory; exported values win. Preserve matching `POSTGRES_*` defaults and configurable Redis URLs. Construct SQLAlchemy URLs through `URL.create`, keep the string URL/Alembic percent-escaping contract, and use the read-only pgvector preflight before migrations. Operators install/enable extensions. The manifest declares compatible LangChain/LangGraph/Groq dependencies but is not a complete transitive lockfile.

## Still required before further automation

The controlled pipeline now joins permissions, policy, approval decisions, execution, verification and local audit. Trusted host authentication and callback tenant scoping remain essential. An action/approval endpoint, domain handlers, expiry, recoverable workflows and operational audit hardening are not provided. Next roadmap module: **Finish browser work when needed**, with a scoped use case under this boundary. Frontend gestures remain presentation only.

## Verification and working conventions

- Implement only the current roadmap module. Add focused tests, run applicable regression suites and checks, then update PRD, ARCHITECTURE, RULES, DESIGN, Task and MEMORY before reporting. Do not commit/push unless requested.
- Do not weaken, skip or suppress tests to hide failures. No existing tests were edited in this module. Baseline AI: 231/232; final: 265/266, with the same browser extraction failure. Baseline and final Django: 126/126. New controlled tests: 34/34; relevant AI selection: 100/100. System checks: 0 issues; migration drift: no changes; real/offline Alembic, compilation and diff checks passed. No new regression failures.
- Database integration tests must target the temporary Django test database. Tests involving vectors apply both migration systems there and clean up AI tables before Django teardown; document-only tool tests use the Django tables. The tests do not migrate the developer database.
- Distinguish real database verification from fake external providers. Live Groq/Ollama/GitHub, worker/broker execution and frontend builds were not verified here.
- Ruff 0.16.9 reports zero diagnostics on this module’s nine changed/new Python files. HEAD versions of the six existing Python files also report zero. The untouched KnowledgeAgent/models files retain 16 diagnostics. No suppressions were added. No Python type-checker configuration exists; compilation is not a static type check. See [MEMORY.md](MEMORY.md) for files, commands, exact results and limitations.
- Before future frontend code changes, read `frontend/AGENTS.md` and the relevant bundled Next.js guide. The current module changes no frontend files.
