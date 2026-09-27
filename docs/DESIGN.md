# GROOT — Design decisions and implementation patterns

Verified: 2026-09-28. Starting HEAD was clean at `20008e6 feat: complete tenant-scoped knowledge flow`. The knowledge backend and setup modules are committed. Trusted Read-Only Tools is implemented and verified in the working tree; no commit or push was made.

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

## Implemented read-only tool design

### Small declarations, one guarded executor

The existing Tool/ToolRegistry interfaces remain the integration point. The new registry admits only read-only declarations with a SELECT, argument model, explicit permission, tenant column and cursor field. Authentication, authorization, scope and transaction handling live in one base executor. No arbitrary SQL string or callback comes from the model. Table expressions describe projections of Django data without claiming migration ownership.

Knowledge was chosen because current credentials already grant knowledge reads. General projects/tasks/customer queries would require a new authorization scope. `KnowledgeAgent.read_only_tools(context, credentials)` binds server dependencies and adds both names to its existing allowlist. Callers use the usual `registry.get(name).execute(**arguments)` or pass that request-local registry to the existing Orchestrator. Existing RAG execution and other agent outputs are unchanged. Authorization/validation failures propagate through the current tool exception contract; inaccessible document IDs return empty pages.

### Independent checks at execution

Strict argument validation runs before opening a session. The fresh PostgreSQL session is marked read-only before the credential lookup. Membership supplies the identity and role; both IDs must match the trusted context. PermissionEngine receives only a live membership-derived knowledge grant, and AgentCapabilityPolicy checks the allowlist and `knowledge.read` context permission. A permissive generic policy mapping cannot bypass these checks because the tool supplies its explicit mapping. Expiry, revocation, disabled users and removed membership are rechecked on each call.

The executor adds the tenant predicate and page limit. It rolls back and closes its own session after materializing results, even on errors, so it cannot flush pending RAG writes. PostgreSQL rejects modifying CTEs inside SELECTs, verified against the real database. This protects application data from accidental write definitions; trusted Python extension authors still control source code and require review.

### Bounded document evidence

`list_documents` returns ID, name, document type, MIME type and size; `read_document_chunks` returns chunk/document IDs, chunk index, text and truncation flag. Both require ready extraction and embeddings and omit internal storage/error/user fields. Missing, foreign and unready chunk requests are indistinguishable empty pages.

Pagination uses ascending document IDs (`after_id`, initially 0) or chunk indices (`after_index`, initially -1). A query fetches at most `limit + 1` rows to determine `next_cursor`; the cursor is null at the end. Document default/max limits are 20/100; chunk limits are 5/20. Each chunk is capped in SQL at 4,000 characters, including Unicode characters, and truncation is explicit. A truncated chunk has no text-offset continuation. Pages are separate reads, not a stable snapshot across concurrent document reprocessing.

### Deployment boundary

No new HTTP endpoint, automatic selection loop, external provider, dependency or migration was added. The server-side registry is usable now; routing it through an authenticated agent workflow remains subsequent coordination work. `/ai` discovery stays health-only. Credentials never appear in schemas or tool results. The contract targets the project's PostgreSQL database; it provides no alternate writable fallback or non-PostgreSQL implementation.

## Existing agent and control maturity

- KnowledgeAgent performs the implemented RAG flow and preserves evidence/citations. Its session in `state['db']` remains a live object, not durable workflow state.
- ResearchAgent packages supplied state; DataAnalyst and Operations still return placeholder summaries.
- The general coordinator executes selected agents sequentially without planning or synthesis. LangGraph wraps one node without checkpointing.
- Equaliator measures summary agreement/evidence heuristics; contradiction detection remains empty. AgentEvaluator reports result fields rather than independent correctness.
- PermissionEngine and AgentCapabilityPolicy are connected to the trusted read-tool executor. Approval, action execution, verification and audit remain separate scaffolds; audit storage is in memory.

## Interface and scope boundary

No frontend files changed. The dark orb/HUD, speech and MediaPipe interactions still call `/ai`. Displayed online/confirm/cancel labels do not establish readiness or permission. There is no authenticated knowledge client, upload API, token-management UI, evidence browser, investigation timeline or persistent conversation UI.

## Verified design checks

Read-tool tests cover discovery, strict schemas, registration rejection, direct and orchestrated use, authorization, tenant isolation, pagination and explicit bounds. Twelve PostgreSQL tests verify real membership/token behavior, readiness, Unicode truncation, read-only transaction reset, application-row immutability and rejection of a modifying CTE with SQLSTATE `25006`. New unit tests: 11/11; focused AI regression: 65/65; full AI: 202/203 with the pre-existing browser failure; full Django: 119/119. Existing knowledge-flow tests and migration lifecycle checks still pass. See [MEMORY.md](MEMORY.md).
