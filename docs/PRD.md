# GROOT — Product requirements and current scope

Verified: 2026-09-28. Starting HEAD was clean at `0d7d2da feat: add coordination and quality`. Setup, the knowledge backend, trusted read-only tools, and Coordination and Quality are committed. Controlled Actions is implemented and verified in the working tree; nothing was committed or pushed.

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
| Agents | Registry/supervisor/LangGraph execution with explicit ordered multi-agent investigation, per-agent evaluations and aggregate quality/status | Trusted server-side caller supplies the original context; ResearchAgent packages state; DataAnalyst/Operations remain placeholders |
| Quality | AgentEvaluator and Equaliator connected to coordination; evidence/citation preservation, support findings, bounded contradiction checks and attributed summaries | Deterministic checks, not semantic truth verification; no investigation HTTP endpoint |
| Actions | ControlledActionPipeline connects existing permissions, trusted registered risk, approval policy, executor, independent verifier and durable local audit; explicit coordinator handoff | Server-side API with trusted callbacks; no domain/external actions registered, approval endpoint or restart/resume of pending requests |
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

## Completed module — Coordination and Quality

`MultiAgentCoordinator.execute(selection, context)` now runs every explicitly selected agent through the existing supervisor and graph, preserving selection order and the original request/context. Agent failures, unknown selections and invalid returned identities become ordered failed results; remaining selected agents still run. Exceptions expose their type without forwarding raw provider/SQL messages.

The existing CoordinationResult retains selection/results and adds existing EvaluationResult/EqualiatorResult objects, status, attributed summary, evidence, citations and limitations. KnowledgeAgent's original evidence, citations and metadata survive. The coordinator neither dispatches returned tool calls nor changes credentials, permissions or tenant scope.

Status is `complete` only when all selected results are successful, error-free, pass quality checks and have evidence text for statement checking. Mixed success/failure is `partial`; no successful error-free output is `failed`; empty selections, unsupported output, conflicts or source-only evidence are `incomplete`. The summary includes only attributed agent summaries that passed checks and had evidence text; detected conflicts withhold a combined conclusion.

Quality measures actual success, reported confidence, evidence and errors. It verifies literal summary statements against supplied evidence text after normalizing case/whitespace/terminal punctuation, checks citation references, and detects identical explicit clauses with opposite `not` polarity. Unmatched paraphrases remain unverified. Agreement is wording agreement, and confidence is an average of valid reported scores, not a calibrated probability of truth.

## Completed module — Controlled Actions

The server-side `ControlledActionPipeline` accepts the existing ActionRequest with an agent and trusted identity/authorization context. Registration defines the tool, strict parameter schema, permission, risk and separate execution/verification callbacks. PermissionEngine checks the role grant; AgentCapabilityPolicy checks the agent allowlist and context grant. User, organization and agent identities must match. Existing membership tokens still grant knowledge reads only.

The existing ApprovalPolicy makes READ and LOW automatic and requires human approval for HIGH_IMPACT. Caller-supplied `approved=True` cannot authorize the pipeline. A separate trusted host call records a same-tenant human decision with `actions.approve`; approval does not itself execute. Execution rechecks permission and is bound to the original request, agent and captured parameters. A denied request remains denied, and a repeated operation does not rerun its callback within the pipeline instance.

The existing ActionExecutor invokes the registered handler and produces ActionResult. Every execution attempt then reaches ActionVerifier; registered verification checks independently observed state. Failed execution or verification cannot become success. Controlled results contain status, identity, ApprovalRequirement, safe ActionResult and VerificationResult, with no input payload, provider output, task/state or raw error text. Approval and execution decisions are recorded through the existing AuditLog, extended with a local JSON-lines journal. The pipeline requires that journal and blocks before execution if auditing fails.

`MultiAgentCoordinator.submit_action` is an explicit host handoff using the existing agent registry. Investigation execution and returned tool-call metadata remain inert. No endpoint, browser, domain write tool, external side-effect integration or authentication extension was added.

## Verification and product limits

- New controlled-action tests: **34/34 passed**; focused AI regressions: **100/100 passed**. Full AI: **266 run, 265 passed, 1 failed**, the same browser extraction mismatch as baseline **232 run, 231 passed, 1 failed**. Full Django: **126/126 passed**, unchanged from baseline. Django system checks: **0 issues**; migration drift: **No changes detected**; real Alembic lifecycle/drift regression: passed with **no new upgrade operations**; offline Alembic SQL, Python compilation and `git diff --check`: passed. Changed-file Ruff: **0 diagnostics across 9 Python files**; **16 pre-existing diagnostics** remain in untouched files. No new regressions, schemas, dependencies or frontend changes. Exact commands, changed-file inventory and limitations are in [MEMORY.md](MEMORY.md).
- Audit decisions persist locally; executable requests, payloads and approval state stay in memory. Restart requires a new request/approval. There is no approval expiry, distributed replay protection, rollback or automatic recovery of ambiguous effects. Callbacks and host-supplied authorization are trusted code; no human-authentication UI is provided.
- Live Groq/Ollama/GitHub, running Redis workers, semantic answer correctness and frontend runtime/build remain unverified. Existing PostgreSQL/pgvector regressions use fake external providers.
- Tokens remain operator-issued; frontend sign-in, token-management UI and upload API remain absent. Lost document dispatch/jobs can need manual retry.
- Browser extraction retains its string-versus-BrowserResult test mismatch. Persistent conversations and workflow resumption remain pending.

## Next product increment

The next unfinished roadmap module is **Finish browser work when needed**, starting with a scoped use case and driver under the controlled-action boundary. Browser work is not implemented here. See [Task.md](Task.md).
