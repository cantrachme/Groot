# GROOT — Design decisions and implementation patterns

Verified: 2026-09-28 against `3c42b23` plus uncommitted knowledge-flow changes. The design below describes implemented behavior and explicitly separates remaining work.

## Existing structure retained

Django owns company records; FastAPI coordinates provider/tool and knowledge operations. Shared PostgreSQL connects Django chunks with AI vectors. Native contracts, narrow injectable services, registry boundaries and separate orchestration/quality/control responsibilities remain. Setup configuration and dependency work was already committed in `3c42b23` and was not repeated.

## Implemented knowledge design

### Membership-bound access

An operator issues an opaque token for an existing active user's membership. The token carries no client-editable identity claims; its SHA-256 digest maps to a Django membership row with an expiry. Each request checks the current membership and active-user state, so removing membership, deleting the token or disabling the user denies subsequent requests. The token is limited to organization knowledge reads.

This establishes a backend authentication boundary without replacing the application's identity model or adding a login UI. Integer identities flow through existing context dataclasses; the old UUID-based `/ai` prototype remains separate and cannot use its random UUIDs to retrieve company data. `/rag` intentionally rejects its former unauthenticated identity payload.

### Evidence flow

The authenticated route invokes the existing KnowledgeAgent. Organization scope travels through RAGService and RetrievalService into the SQL query, then into an independent text lookup. Both queries also exclude documents whose extraction or embeddings are not ready. Filtering happens before top-k, so another organization's high-scoring vectors cannot displace authorized results.

`AIService.handle_rag` delegates answer composition to RAGService instead of duplicating it. Scoped callers cannot inject a text map around the database check. Missing scope returns no stored data. An empty assembled context returns a fixed insufficient-context answer without an LLM call; nonempty context uses the existing provider prompt. The response includes the actual context items and chunk citation IDs. The existing character-budget assembler is unchanged, including its nominal rather than tokenizer-based budget.

### Processing, readiness and retries

Extraction still produces normalized text, deterministic ordered chunks and its existing READY/FAILED state. A separate `embedding_status` and generic `embedding_error` distinguish searchable documents from documents that have only been extracted. Successful processing registers dispatch after transaction commit. Rollbacks and failed extraction do not enqueue work.

The processing pipeline, direct chunk replacement and embedding task use the same document-row lock. The embedding task loads current chunks while holding that lock, uses the existing AI session, and marks readiness only after the vector transaction commits. This prevents stale queued jobs from writing vectors for replaced chunks. Holding a lock during provider calls trades per-document concurrency for a simple, verified consistency contract.

The vector service validates all batches before performing upserts and rolls back the whole write transaction on failure. Upsert preserves the chunk/model row identity and creation time. The legacy low-level insert methods remain available for compatibility; the document workflow uses upserts. Retryable provider/database exceptions get three automatic retries with backoff; invalid configuration/vector responses and dispatch failures need operator correction/retry.

Alembic owns the cascading foreign key to Django chunks. Reference-only metadata avoids transferring Django table ownership to SQLAlchemy. The migration removes historical orphans before creating the constraint; chunk/document deletion and failed/successful reprocessing then remove obsolete vectors automatically.

### Dispatch and configuration

Celery autodiscovery is deferred until Django is initialized, and `core.tasks` exposes the nested tasks. Backend-launched workers can import the existing AI services through the repository-root import path. Query and worker code use a shared embedding provider factory, including `OLLAMA_BASE_URL`.

Dispatch failures are recorded, but there is no durable outbox. A process crash between commit and publish, or a lost worker job, can leave pending work requiring manual retry. The two service transactions are not a distributed transaction: vectors commit first and readiness gates visibility until Django commits. Existing documents start pending after migration and need embedding before retrieval.

## Existing agent and control maturity

- KnowledgeAgent performs the implemented RAG flow and preserves evidence/citations. Its session in `state['db']` remains a live object, not durable workflow state.
- ResearchAgent packages supplied state; DataAnalyst and Operations still return placeholder summaries.
- The general coordinator executes selected agents sequentially without planning or synthesis. LangGraph wraps one node without checkpointing.
- Equaliator measures summary agreement/evidence heuristics; contradiction detection remains empty. AgentEvaluator reports result fields rather than independent correctness.
- Permission, approval, execution, verification and audit components remain disconnected scaffolds; audit storage is in memory.

## Interface and scope boundary

No frontend files changed. The dark orb/HUD, speech and MediaPipe interactions still call `/ai`. Displayed online/confirm/cancel labels do not establish readiness or permission. There is no authenticated knowledge client, upload API, token-management UI, evidence browser, investigation timeline or persistent conversation UI.

## Verified design checks

The 19 new AI tests and 23 new Django tests cover authentication, spoofed identity rejection, fail-closed scope, evidence responses, empty context, task dispatch timing/rollback/retries and registration. Eleven Django integration tests use real PostgreSQL/pgvector and both migration systems; they verify cross-tenant exclusion even when a foreign vector ranks higher, token expiry/revocation, upsert idempotency/rollback, cascade cleanup, and document locking. External providers are fake. Focused AI: 55/55; full AI: 191/192 with the baseline browser failure; full Django: 107/107. See [MEMORY.md](MEMORY.md).
