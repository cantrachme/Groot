# GROOT — Engineering rules

Verified: 2026-09-28 against `3c42b23` plus the uncommitted knowledge-flow module. Enforced contracts below are backed by code/tests. Remaining requirements are identified separately.

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

Trusted authorization must be applied when adding real tools, including direct orchestrator calls. Existing capability mappings and supplied-role permission contracts are not a complete execution boundary. High-impact actions need durable approval, actual tool execution, durable audit and independent outcome checks. Current executor/verifier/audit do not provide these guarantees. Frontend gestures are not approval.

## Verification and working conventions

- Implement only the current roadmap module. Add focused tests, run applicable regression suites and checks, then update PRD, ARCHITECTURE, RULES, DESIGN, Task and MEMORY before reporting. Do not commit/push unless requested.
- Do not weaken, skip or suppress tests to hide failures. No existing tests were edited in the knowledge module. Baseline AI: 172/173; final: 191/192, with the same browser extraction failure. Baseline Django: 84/84; final: 107/107.
- Database integration tests must target the temporary Django test database, apply both migration systems there, and clean up AI tables before Django teardown. The tests do not migrate the developer database.
- Distinguish real database verification from fake external providers. Live Groq/Ollama/GitHub, worker/broker execution and frontend builds were not verified here.
- Ruff 0.16.9 on changed Python files reports 16 pre-existing diagnostics (15 in models, 1 in KnowledgeAgent); baseline comparison found zero new diagnostics. Preserve unrelated code instead of suppressing those diagnostics. No Python type-checker configuration exists; compilation is not a static type check.
- Before future frontend code changes, read `frontend/AGENTS.md` and the relevant bundled Next.js guide. The current module changes no frontend files.
