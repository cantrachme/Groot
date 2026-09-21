# GROOT — Engineering rules

Reviewed: 2026-09-21. These rules preserve observed architecture; requirements addressing current gaps are labeled explicitly. They are not claims that every existing path already complies.

## Preserve current boundaries

1. **Keep business records in Django.** Extend `backend/core/models.py` through Django migrations. Keep AI-owned tables in SQLAlchemy/Alembic. Preserve the Alembic reflected-table filter so it does not propose dropping Django tables.
2. **Reuse the AI database foundation.** Use the existing `Base`, `SessionLocal`, and `get_db`; do not introduce a second engine/session setup for agents. Keep Django and AI database configuration aligned because retrieval reads Django tables directly.
3. **Adapt external libraries to GROOT contracts.** Keep `LLMProvider`, `LLMResponse`, `ToolCall`, `EmbeddingProvider`, `AgentContext`, and `AgentResult` as service boundaries. LangChain is an adapter; LangGraph currently wraps execution.
4. **Keep agent responsibilities narrow.** Register unique names and declare capabilities/allowed tools. Preserve duplicate/unknown-name errors. A capability label is not an implemented data query or a permission grant.
5. **Keep orchestration and quality assessment separate.** Selection/execution belong to coordinator/supervisor/orchestrator; cross-agent assessment belongs to Equaliator; evaluation metrics belong to `evaluation/`.

## Data contracts and lifecycle

- Preserve organization-scoped uniqueness for business entities and event idempotency by organization/source/external ID. Events lacking external identity intentionally append.
- Preserve document processing status transitions, deterministic chunk ordering, and replacement behavior. Coordinate embeddings when changing chunk lifecycle: the current integer reference has no foreign-key cascade.
- Validate embedding vector count/dimensions and query limits; search using matching model and dimensions. Changing embedding configuration requires a deliberate re-embedding plan. Do not treat the deterministic local provider as semantic retrieval.
- Preserve evidence/chunk IDs in internal RAG results. Reuse retrieval/context services instead of adding another retrieval implementation; the duplicated answer-composition paths are a consolidation opportunity.
- Keep SQL parameterized and integration credentials behind `CredentialProvider`. Do not place secrets in docs, frontend bundles, or stored integration metadata.

## Required before extending access or side effects

- Derive user, organization, and roles from authenticated server-side membership. Resolve the integer/UUID mismatch deliberately; random client UUIDs are demo input, not identity.
- Enforce tenant scope in database retrieval and chunk text access, not only in prompts or request metadata. Existing RAG does not enforce it.
- Apply tool authorization on execution, including direct orchestrator calls. `AgentCapabilityPolicy` currently checks an allowlist and only checks a permission if a mapping exists; `PermissionEngine` accepts supplied roles without resolving memberships. Wire both to trusted data before relying on them.
- Keep high-impact actions approval-gated. `ApprovalPolicy` marks only high-impact risk as requiring approval, while `ActionExecutor` currently requires `approved=True` for every request. Define their integration explicitly; never treat a client boolean or gesture label as sufficient approval.
- Real action success must come from tool execution; verification must observe the resulting state. Current executor/verifier results are scaffolding. Make audit records durable before depending on them for accountability.

## Working and verification conventions

- Inspect callers and focused tests before extending a named module; many KT modules already exist. Distinguish contract scaffolds, callable services, and integrated product flows in status updates.
- For frontend changes, follow [frontend/AGENTS.md](../frontend/AGENTS.md): read the relevant bundled Next.js guide before coding against this version.
- Maintain the Python dependency manifest when using imported libraries; LangChain/LangGraph imports are currently missing from it.
- Use focused `unittest` tests under `ai_engine/tests/`, Django tests in `backend/core/tests.py`, and frontend lint/build as appropriate. Database/model changes also need migration review. Typical suite commands are `python -m unittest discover -s ai_engine/tests` from the root and `python manage.py test core` from `backend/`, with dependencies/settings/database prepared.
- Do not repeat historical test counts as fresh validation. Do not assume mocked connector/provider tests demonstrate live integrations. Report what ran and what remains unverified.
- Preserve unrelated local changes. At this review, `ai_engine/app/browser/` and `ai_engine/tests/test_browser_tool.py` were untracked work in progress.
