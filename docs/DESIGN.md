# GROOT — Design decisions and implementation patterns

Verified: 2026-09-28. Starting HEAD was clean at `a6d1b6e feat: add trusted read-only tools`. Setup, the knowledge backend and trusted read-only tools are committed. Coordination and Quality is implemented and verified in the working tree; no commit or push was made.

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

No new HTTP endpoint, automatic selection loop, external provider, dependency or migration was added. Registered agents can now use the server-side read registry within the coordinator; callers still establish the authenticated context and bind tool credentials. `/ai` discovery stays health-only. Credentials never appear in schemas or tool results. The contract targets the project's PostgreSQL database; it provides no alternate writable fallback or non-PostgreSQL implementation.

## Implemented coordination and quality design

### One result contract and explicit execution

CoordinationResult was extended with existing evaluation types, status, summary, evidence/citations and limitations. Existing two-argument construction remains valid through defaults. Selection and individual AgentResults stay intact, so consumers can inspect the original KnowledgeAgent answer, evidence similarity, citation IDs and metadata. Flat evidence/citation collections preserve order and duplicates rather than erasing provenance or conflicting sources.

The registry/supervisor/graph remain the execution path. The coordinator enables per-agent failure capture, preserving one result position per selected name, including missing agents and execution failures. A failed agent does not prevent the remaining selected agents from running. Direct supervisor behavior remains unchanged by default. Exception types are retained while raw messages are excluded from returned summaries/findings. The coordinator preserves the original context object, including task, query, IDs, permissions and runtime state; agents are trusted to leave that shared state unchanged.

### Checks with explicit limits

AgentEvaluator evaluates every result using existing MetricScore/EvaluationResult types. Success, confidence, evidence and errors remain visible; `groundedness` adds the result of literal support checks. Blank/missing evidence, blank summaries, citation references not present in evidence and summary statements not found in evidence text produce findings. Sentence comparison normalizes case, whitespace and terminal punctuation. It checks complete statements, so a matching substring inside a negated claim does not suffice. It does not recognize paraphrases, independently authenticate source content or assess arbitrary structured data fields.

Missing confidence stays null. Booleans, strings, nonfinite numbers and values outside 0–1 fail confidence validation. Original AgentResults are retained; metrics use null for invalid confidence and Equaliator excludes invalid/error-bearing/failed scores from its mean. No low-confidence threshold is introduced.

Equaliator now uses these shared support findings, reports errors/invalid confidence as missing information, and prevents those signals from completing its assessment. Evidence quality is HIGH only when every agent succeeds without errors and has usable evidence. Summary agreement remains a wording comparison. Contradictions cover the same explicit auxiliary-verb clause with and without `not` (excluding `not only`); broader contradictions are not inferred.

### Status and synthesis

The overall status is authoritative: `complete` requires all results to pass checks and supply evidence text. The existing Equaliator structural completion flag alone is insufficient, particularly for legacy source-only references. Mixed success/failure is partial, no successful error-free results is failed, and empty selections or otherwise unresolved quality are incomplete. An empty KnowledgeAgent retrieval remains incomplete even though its existing result represents successful execution.

Synthesis attributes original checked summaries in selection order and adds no new model-generated claims. Unsupported/failed summaries are withheld, and detected contradiction suppresses a combined conclusion. Evidence, citations, metrics and findings remain available even when synthesis is withheld. Missing confidence and unavailable evidence text are explicit limitations; every investigation also states the heuristic scope of its quality checks.

### Authorization boundary

No authentication or permission model changed. This is an internal coordinator invoked with trusted context; KnowledgeAgent continues its existing scoped RAG behavior. Agents that use bound read tools retain live membership/identity/permission/tenant checks inside the tools. Credentials never become coordinator arguments or tool-schema fields. The coordinator records returned tool-call metadata but does not execute it. No browser, write tool, action or autonomous agent-selection loop was added.

## Existing agent and control maturity

- KnowledgeAgent performs the implemented RAG flow and preserves evidence/citations. Its session in `state['db']` remains a live object, not durable workflow state.
- ResearchAgent packages supplied state; DataAnalyst and Operations still return placeholder summaries.
- The coordinator executes explicit selections sequentially, evaluates outputs and builds attributed summaries with status/limitations. LangGraph still wraps one node without checkpointing or autonomous planning.
- Equaliator and AgentEvaluator are connected to coordination with the support/contradiction limits above. They do not establish independent factual correctness.
- PermissionEngine and AgentCapabilityPolicy are connected to the trusted read-tool executor. Approval, action execution, verification and audit remain separate scaffolds; audit storage is in memory.

## Interface and scope boundary

No frontend files changed. The dark orb/HUD, speech and MediaPipe interactions still call `/ai`. Displayed online/confirm/cancel labels do not establish readiness or permission. There is no authenticated knowledge client, upload API, token-management UI, evidence browser, investigation timeline or persistent conversation UI.

## Verified design checks

The 29 new AI tests cover ordered multi-agent execution, original context, evaluation integration and metrics, complete/partial/failed/incomplete status, exceptions, invalid result identities, unsupported text/citations, missing/invalid confidence, literal contradictions, KnowledgeAgent evidence preservation, empty retrieval and no tool-call dispatch. The focused AI selection passed 103/103. Seven new PostgreSQL/pgvector tests coordinate actual KnowledgeAgent retrieval and guarded reads using fake external providers; they verify tenant isolation, permissions, expired/revoked credentials, revocation between agents and rejected mutation without data changes. Full AI: 231/232 with the baseline browser failure; full Django: 126/126. Migration, compilation, diff and changed-file lint checks passed. See [MEMORY.md](MEMORY.md).
