# GROOT — Product requirements and current scope

Reviewed: 2026-09-21. Lightweight source review at commit `06c15a9`, including the local, untracked browser prototype. Source code is authoritative; the supplied KT is historical context. This review did not run application services or test suites.

## Purpose and users

GROOT aims to provide operational intelligence for growing startups: connect company information, investigate problems, explain findings, recommend actions, and eventually execute approved actions and verify outcomes. This intent comes from the root README and the supplied KT.

Intended users are startup founders, operations leaders, and functional teams; these are product assumptions, not validated personas. Current access is a developer-facing voice/orb prototype and Django administration, not a finished organization workspace.

## Current capabilities

| Area | Implemented | Product limitation |
| --- | --- | --- |
| Company foundation | Django user, organization, membership, team, customer, project, task, event, risk, document, integration models and migrations | Only `/admin/` is routed; no business REST API or frontend sign-in flow |
| Assistant | FastAPI `/ai`, Groq provider, tool schemas and registry, one tool-execution round followed by an LLM response | Default registry contains only `health_check`; no agent investigation pipeline behind this endpoint |
| Knowledge | Text/PDF extraction, normalization, chunking, embedding services, pgvector retrieval, context assembly, `/rag` | No upload-to-embedding workflow is wired end to end; retrieval lacks tenant filtering |
| External data | Read-only GitHub connector, normalized repository events, organization-scoped event persistence, ingestion task | Other integration names are enum choices only; no integration management UI |
| Agents | Contracts, registry, capability policy, LangGraph wrapper, supervisor, sequential coordinator, KnowledgeAgent | ResearchAgent packages supplied state; DataAnalystAgent and OperationsAgent return placeholder results |
| Quality and actions | Equaliator, result evaluator, permission/approval contracts, action/verification scaffolds, in-memory audit | Standalone components; action executor does not invoke tools, verifier only echoes success |
| Interface | Next.js 3D orb, browser speech recognition and synthesis, MediaPipe hand gestures, `/ai` requests | Generates random user/organization UUIDs; gestures do not authorize business actions |

Evidence: [domain models](../backend/core/models.py), [HTTP routes](../ai_engine/app/main.py), [AI service](../ai_engine/app/services/ai_service.py), [agents](../ai_engine/app/agents/), [frontend page](../frontend/app/page.tsx).

## Current boundary

This is a development prototype with reusable backend foundations. Model presence or a passing contract test does not imply a working product feature. In particular:

- There is no authenticated link between Django identities and AI requests. Django uses integer IDs; AI request contracts require UUIDs.
- RAG queries filter embedding model/dimensions, but not organization. They must be scoped before using shared tenant data.
- Risk records exist; automated risk detection and continuous investigations do not.
- Browser operations currently exist only as an untracked state/result stub, without browser automation.
- No persistent conversations, resumable agent workflows, approval inbox, or investigation activity feed was found.

## Near-term product outcome

The recommended next milestone is one authenticated, organization-scoped knowledge question answered from ingested documents with inspectable evidence. Acceptance should demonstrate that:

1. The server establishes the user and organization from authenticated membership.
2. Document processing produces usable embeddings and handles reprocessing consistently.
3. Retrieval cannot return another organization's chunks.
4. One request reaches the existing KnowledgeAgent/RAG services and returns an answer plus evidence, including an honest insufficient-context response.

This is a proposed priority derived from integration gaps, not evidence of an assigned sprint. See [Task.md](Task.md).

## Future direction

Extend the proven knowledge flow with useful read-only company tools, agent selection, evidence evaluation, then durable approvals, actual actions, and independent verification. Keep orchestration separate from Equaliator quality assessment. Add specialist agents when their data and tools exist. Persistent workflows, browser automation, event-triggered investigations, and richer UI are later increments; MongoDB, MCP, and distributed infrastructure are options rather than prerequisites.
