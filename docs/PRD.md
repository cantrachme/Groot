# GROOT — Product requirements and current scope

Verified: 2026-09-28. Starting HEAD was clean at `20008e6 feat: complete tenant-scoped knowledge flow`. The knowledge backend and setup modules are committed. Trusted Read-Only Tools is implemented and verified in the working tree; no commit or push was made.

## Purpose and users

GROOT aims to provide operational intelligence for growing startups: connect company information, investigate problems, explain findings, recommend actions, and eventually execute approved actions and verify outcomes. Founders, operations leaders and functional teams are intended users, not validated personas. The product remains a developer-facing prototype.

## Current capabilities

| Area | Implemented | Boundary |
| --- | --- | --- |
| Setup | Compatible declared dependencies, shared environment-based PostgreSQL/Redis configuration, environment examples, read-only pgvector preflight | Completed in `3c42b23`; external services remain operator-provisioned |
| Company foundation | Django company models/admin, memberships, integrations, document content/chunks | Business administration and credential issuance remain operator-facing |
| Knowledge | Authenticated `/rag` → KnowledgeAgent → tenant-scoped vectors/text → answer, evidence and citations | Operator-issued membership token; no upload API or frontend knowledge/sign-in flow |
| Document lifecycle | Text/PDF processing; after-commit embedding task; atomic vector upsert; chunk deletion cascades vectors; separate embedding status | No durable dispatch outbox or automatic recovery of lost jobs; operators can retry |
| Trusted read tools | Request-local registry with `list_documents` and `read_document_chunks`; live membership, permission and agent checks; database-enforced read-only transactions | Knowledge data only; server-side API, no new HTTP route or automatic tool selection |
| Assistant | `/ai`, Groq and one tool-execution round | Existing UUID-based demo identity; only `health_check` registered; no company-data access through this path |
| External data | Read-only GitHub connector and organization-scoped event ingestion | Other integrations remain enum choices |
| Agents | Contracts, registry, policy, LangGraph wrapper, sequential coordinator; KnowledgeAgent now reached by `/rag` | ResearchAgent packages supplied state; DataAnalyst/Operations remain placeholders |
| Quality/actions | Equaliator, evaluator, permission/approval contracts, action/verification scaffolds, in-memory audit | Unconnected to the HTTP knowledge flow; no real action execution or independent verification |
| Interface/browser | Orb, speech and MediaPipe gesture prototype; browser state/result stub | Frontend still calls `/ai` with random UUIDs; gestures are not authorization; browser stub has no driver |

## Completed module — Finish the knowledge flow (backend)

The authenticated document-to-evidence backend path is implemented and verified at these boundaries:

1. An expiring opaque token is tied to a Django membership. Only its digest is stored. Each request checks expiry, active user and current membership, deriving integer user/organization IDs from the database.
2. The existing processing pipeline commits normalized chunks, then dispatches an embedding task. The job records ready/failed status independently of extraction, uses upserts for retries, and locks the document against reprocessing.
3. Vector search filters by organization and ready status before ranking/limiting. Text loading independently checks the same scope. Missing scope returns no stored data. Replaced/deleted chunks delete their embeddings through a database constraint.
4. `/rag` reaches KnowledgeAgent and returns the answer plus the actual chunk evidence and citation IDs. Empty authorized context returns a fixed insufficient-context answer without asking the LLM to invent an answer.

The old unauthenticated `/rag` contract is intentionally replaced: a bearer token is required, and caller-supplied identity fields are rejected. `request_id`, `message`, optional `top_k` (1–50), and existing response fields remain; evidence/citations are added. `/ai` is unchanged. This is a backend capability, not a completed authenticated frontend workspace.

## Completed module — Trusted Read-Only Tools

KnowledgeAgent can build a private tool registry for a trusted caller or the existing tool orchestrator. Tools list ready documents and read ordered chunks using the current membership token. Every execution authenticates again, checks the bound integer identity, requires `knowledge.read` through the permission engine and agent policy, and adds the current organization predicate before limiting results.

Document pages contain at most 100 records (default 20). Chunk pages contain at most 20 records (default 5), with each text capped at 4,000 characters and an explicit truncation flag. Both return a continuation cursor. Foreign, missing and unready documents produce the same empty chunk page. Storage keys, embedding errors, credentials and user details are not exposed.

Strict schemas reject mutations, SQL, identity overrides and invalid arguments. PostgreSQL read-only transactions also reject a write hidden in a SELECT. Existing `/rag` answer behavior is preserved; `/ai` still has only the health tool. Tokens do not grant access to unrelated business records or actions.

## Verification and product limits

- New read-tool coverage: **11/11 AI unit tests and 12/12 PostgreSQL integration tests passed**. Focused AI regression selection: **65/65 passed**.
- Full regression: AI **202 passed / 203 run**, retaining the sole pre-existing browser extraction failure; Django **119/119 passed**. Current-module baseline: AI **191/192**, Django **107/107**. No new failures. Lint has only the unchanged KnowledgeAgent diagnostic among changed files.
- Django migration creation/drift checks and real Alembic upgrade/downgrade/upgrade/drift checks passed in a temporary test database. No migrations were applied to the developer's existing database.
- Live Groq/Ollama/GitHub calls, a running Redis worker, semantic answer correctness, PDF-through-LLM behavior and frontend runtime/build were not verified by this module. The end-to-end fixture used plain text and fake providers with real pgvector queries.
- Tokens are issued by an operator; there is no user sign-in, token-management UI or upload API. Old documents require embedding after the new migrations. Lost dispatch/process crashes can require manual retry.
- Browser extraction still has a pre-existing string-versus-`BrowserResult` test mismatch. Persistent conversations, workflow resumption, automated risk detection and real controlled actions remain unimplemented.

## Next product increment

The next roadmap module is **Connect coordination and quality**: explicit agent selection, evidence collection, Equaliator and synthesis, with supported contradiction/groundedness checks before claiming them. Preserve the verified knowledge and read-tool boundaries. See [Task.md](Task.md).
