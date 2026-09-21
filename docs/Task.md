# GROOT — Implementation roadmap

Reviewed: 2026-09-21 at `06c15a9`, plus local untracked browser files. “Completed” below means source-level implementation at the stated scope, not production readiness or a freshly passing test suite. Priorities are recommendations from this review; no active sprint tracker was supplied.

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
- [x] Focused Django and AI test files for these modules; execution status not established by this documentation review.

## Ongoing / local work

- [ ] Review and finish `ai_engine/app/browser/` and `ai_engine/tests/test_browser_tool.py`: untracked at inspection. The current abstraction stores URL/title and echoes requested operations; it has no browser driver or real extraction.
- [ ] Integrate the existing standalone agent/control modules into a useful request flow. No evidence identifies an assigned owner or active implementation schedule.

## Current priority

**Deliver one authenticated, tenant-scoped knowledge investigation with evidence.** Do not restart Agent Contracts & Registry (historical Module 09), which already exists.

- [ ] Resolve Django integer IDs versus AI UUID contracts and replace random frontend identity with authenticated membership context.
- [ ] Apply organization filtering to vector search and chunk text loading; add a cross-organization isolation check.
- [ ] Wire document processing to embedding generation with explicit reprocessing/cleanup behavior.
- [ ] Route one request through the existing KnowledgeAgent/RAG service and expose answer evidence.

## Next implementation steps

1. **Make setup reproducible:** declare LangChain/LangGraph dependencies, complete environment examples, align database configuration, and verify pgvector extension prerequisites.
2. **Finish the knowledge flow:** consolidate duplicated RAG answer assembly; verify nested Celery task registration; establish embedding retry/upsert semantics and stale-vector cleanup. Test extraction → embeddings → scoped answer.
3. **Add useful read-only tools:** implement one real business-data query or research source behind allowed tools and trusted permissions. Replace placeholder agent success responses with meaningful results/failures.
4. **Connect coordination and quality:** select agents explicitly, collect evidence, run Equaliator and synthesize. Implement supported contradiction/groundedness checks before advertising those abilities.
5. **Connect controlled actions:** define trusted risk classification and approval records, invoke a real tool, record durable audit events, and verify external state. Align approval policy with executor semantics.
6. **Finish browser work when needed:** choose a driver and scoped browser use case, then add real navigation/extraction with the same control boundary.

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
| Browser abstraction is future work | Local untracked stub exists; real browser automation remains future work |
| Latest commit `25d7391`; 46 AI / 84 Django tests passed | Inspected HEAD is `06c15a9`; more AI test modules exist. Historical results are not current validation |
| Ollama 768 dimensions verified | Source defaults agree; no live provider check performed here |
| RAG/organization foundation is complete | Subsystems exist, but request identity, tenant-safe retrieval and ingestion-to-embedding wiring remain incomplete |

The KT's separation of orchestrator, specialist agents, Equaliator, and controlled actions remains a useful intended direction. Its module numbering and completion claims should not dictate the next implementation blindly.
