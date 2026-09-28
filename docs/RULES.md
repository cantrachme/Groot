# GROOT — Engineering rules

Verified: 2026-09-28. Starting HEAD was clean at `a6d1b6e feat: add trusted read-only tools`. Setup, the knowledge backend and trusted read-only tools are committed. Coordination and Quality is implemented and verified in the working tree; no commit or push was made.

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

The read-only knowledge tools now enforce trusted authorization, including direct orchestrator calls. Other tools still need a trusted execution boundary; the generic capability and supplied-role contracts alone do not provide one. High-impact actions need durable approval, actual tool execution, durable audit and independent outcome checks. Current executor/verifier/audit do not provide these guarantees. Frontend gestures are not approval.

## Verification and working conventions

- Implement only the current roadmap module. Add focused tests, run applicable regression suites and checks, then update PRD, ARCHITECTURE, RULES, DESIGN, Task and MEMORY before reporting. Do not commit/push unless requested.
- Do not weaken, skip or suppress tests to hide failures. No existing tests were edited in this module. Baseline AI: 202/203; final: 231/232, with the same browser extraction failure. Baseline Django: 119/119; final: 126/126. New suites: AI 29/29 and PostgreSQL 7/7; relevant AI selection 103/103.
- Database integration tests must target the temporary Django test database. Tests involving vectors apply both migration systems there and clean up AI tables before Django teardown; document-only tool tests use the Django tables. The tests do not migrate the developer database.
- Distinguish real database verification from fake external providers. Live Groq/Ollama/GitHub, worker/broker execution and frontend builds were not verified here.
- Ruff 0.16.9 reports zero diagnostics on this module’s seven changed/new Python files. HEAD comparison had one Equaliator import-order diagnostic, resolved when editing its imports. The untouched KnowledgeAgent/models files still report their 16 pre-existing diagnostics. Preserve unrelated code instead of suppressing those diagnostics. No Python type-checker configuration exists; compilation is not a static type check.
- Before future frontend code changes, read `frontend/AGENTS.md` and the relevant bundled Next.js guide. The current module changes no frontend files.
