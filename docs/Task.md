# GROOT — Implementation roadmap

Verified: 2026-09-28 against baseline `231e3027fc4299dd94ed75451dc45dccf4b2dbc8` plus the uncommitted setup module. “Completed” means implementation at the stated scope, not production readiness. Tests now have fresh results below. No commits or pushes were made.

## Completed work

- [x] Django company models, custom user/memberships, admin, PostgreSQL settings and migrations.
- [x] SQLAlchemy engine/session/dependency/Base, pgvector model and Alembic ownership boundary.
- [x] FastAPI health, `/ai`, `/rag`, Groq adapter, tool schemas/registry and health tool.
- [x] Text/PDF extraction, normalization, deterministic chunks, document task implementation.
- [x] GitHub read-only connector, normalized events, organization-scoped idempotent persistence and ingestion task implementation.
- [x] Local deterministic and Ollama embedding providers, embedding persistence, cosine retrieval, chunk loading and context assembly.
- [x] Agent contracts/registry/capability policy, LangChain adapter, single-node LangGraph wrapper, sequential supervisor/coordinator.
- [x] KnowledgeAgent using RAG; basic ResearchAgent state handling; DataAnalyst/Operations contract scaffolds.
- [x] Equaliator/result evaluation, role-permission and approval contracts, action/verification scaffolds, in-memory audit log.
- [x] Next.js orb, speech input/output, MediaPipe gesture prototype, voice-to-`/ai` connection.
- [x] Focused Django and AI test files for these modules. Current full results: Django 84/84; AI 172/173 with one pre-existing browser contract failure.
- [x] **Make setup reproducible:** declared LangChain/LangGraph and a compatible Groq SDK; completed environment examples; aligned PostgreSQL/Redis configuration; added a read-only pgvector preflight and README setup instructions. Fresh Python 3.14.4 installation and dependency check passed. Existing service/data boundaries remain unchanged.

## Remaining integration and scaffold work

- [ ] Review and finish `ai_engine/app/browser/` and `ai_engine/tests/test_browser_tool.py`: tracked in baseline `231e302`. The current abstraction stores URL/title and echoes requested operations; it has no browser driver or real extraction. `test_extracts_information` fails on the existing string-versus-`BrowserResult` mismatch. Deferred to the browser module.
- [ ] Integrate the existing standalone agent/control modules into a useful request flow. No evidence identifies an assigned owner or active implementation schedule.

## Current priority

**Deliver one authenticated, tenant-scoped knowledge investigation with evidence.** Do not restart Agent Contracts & Registry (historical Module 09), which already exists.

- [ ] Resolve Django integer IDs versus AI UUID contracts and replace random frontend identity with authenticated membership context.
- [ ] Apply organization filtering to vector search and chunk text loading; add a cross-organization isolation check.
- [ ] Wire document processing to embedding generation with explicit reprocessing/cleanup behavior.
- [ ] Route one request through the existing KnowledgeAgent/RAG service and expose answer evidence.

## Next implementation steps

1. [x] **Make setup reproducible:** completed and verified on 2026-09-28. See the verification record below.
2. [ ] **NEXT — Finish the knowledge flow:** begin with authenticated membership/identity and tenant-scoped retrieval from the current-priority checklist, then consolidate duplicated RAG answer assembly; fix nested Celery task registration; establish embedding retry/upsert semantics and stale-vector cleanup. Test extraction → embeddings → scoped answer. A fresh process confirmed that only the health task is auto-registered today.
3. **Add useful read-only tools:** implement one real business-data query or research source behind allowed tools and trusted permissions. Replace placeholder agent success responses with meaningful results/failures.
4. **Connect coordination and quality:** select agents explicitly, collect evidence, run Equaliator and synthesize. Implement supported contradiction/groundedness checks before advertising those abilities.
5. **Connect controlled actions:** define trusted risk classification and approval records, invoke a real tool, record durable audit events, and verify external state. Align approval policy with executor semantics.
6. **Finish browser work when needed:** choose a driver and scoped browser use case, then add real navigation/extraction with the same control boundary.

## Completed setup module: verification record

- Baseline checkout was clean at `231e3027fc4299dd94ed75451dc45dccf4b2dbc8`; all six docs and service sources were inspected before edits.
- Baseline AI suite: **162 run, 161 passed, 1 failed** (`test_browser_tool.BrowserToolTests.test_extracts_information`). Baseline Django: **84 run, 84 passed** on PostgreSQL.
- Added **11 setup tests** for shared configuration, dotenv precedence/path, special-character credentials, offline migrations, pgvector states and CLI error handling. Focused selection: **27 run, 27 passed**.
- Final existing-environment and fresh-environment regressions each: **AI 173 run, 172 passed, same 1 failed; Django 84 run, 84 passed**. No existing test was changed, skipped or suppressed.
- Fresh temporary Python 3.14.4 environment: full manifest installation succeeded; `pip check` passed. The original virtual environment was left unchanged.
- Live read-only database preflight: **PostgreSQL connected, pgvector 0.8.6 enabled**. Django system check: **0 issues**. Migration drift check: **No changes detected**. Offline Alembic SQL passed within the focused suite. `git diff --check` passed.
- Initial sandbox network/database denials were resolved through permitted access; they were environment restrictions, not application failures. Existing SQLAlchemy deprecation warnings and invalid-PDF fixture diagnostics remain visible.
- No database schema, agent behavior, frontend application code, or browser implementation was changed. New setup limits: preflight is manually invoked, operator provisioning is required, and dependencies are not fully transitively locked. Live provider calls, running Redis workers, frontend lint/build and a complete fresh database provisioning cycle were not tested.
- All six living docs were updated after implementation and regression checks. Detailed commands and file inventory are in [MEMORY.md](MEMORY.md).

## Long-term improvements

- [ ] Persist conversations and workflow state; checkpoint/resume long-running work when a use case requires it.
- [ ] Add background agent jobs, schedules, retries, and event-triggered investigations.
- [ ] Expose agent activity/evidence/progress to the frontend; improve voice compatibility and accessible non-voice interaction.
- [ ] Add specialist agents and connectors based on available business data, not roadmap counts.
- [ ] Add regression datasets, retrieval/trajectory evaluation, latency/token/cost metrics, and durable tracing.
- [ ] Harden deployment settings/secrets, tenant isolation, worker configuration, and service readiness; introduce CI and containers.
- [ ] Consider MCP, MongoDB, Redis workflow state, distributed coordination, or Kubernetes only after demonstrating the need.

## Reconciliation with the supplied KT

| Historical claim | Current evidence |
| --- | --- |
| Next work is Module 09: agent contracts | Already implemented, along with capability policy, LangChain/LangGraph foundations, specialist shells and sequential coordination |
| Evaluation/permissions/approvals/actions/verification are future modules | Their contracts and basic implementations exist, but are disconnected from HTTP and often only scaffolds |
| RAG cleanup is complete | Shared retrieval exists, but `AIService.handle_rag` and `RAGService.answer` still duplicate answer composition |
| Voice is a late future phase | Browser STT/TTS and voice-to-AI UI already exist |
| Browser abstraction is future work | Tracked stub exists in `231e302`; real browser automation remains future work |
| Latest commit `25d7391`; 46 AI / 84 Django tests passed | Baseline is `231e302`; fresh results after setup are AI 172/173 and Django 84/84, with the browser failure confirmed before edits |
| Ollama 768 dimensions verified | Source defaults agree; no live Ollama check performed here. PostgreSQL/pgvector preflight was verified separately |
| RAG/organization foundation is complete | Subsystems exist, but request identity, tenant-safe retrieval and ingestion-to-embedding wiring remain incomplete |

The KT's separation of orchestrator, specialist agents, Equaliator, and controlled actions remains a useful intended direction. Its module numbering and completion claims should not dictate the next implementation blindly.
