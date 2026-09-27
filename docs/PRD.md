# GROOT — Product requirements and current scope

Verified: 2026-09-28 against baseline `231e3027fc4299dd94ed75451dc45dccf4b2dbc8` plus the uncommitted setup module. Source inspection, focused tests, both Python regression suites, a fresh dependency installation, and a live PostgreSQL/pgvector preflight were completed. Live provider calls and frontend runtime behavior were not tested.

## Purpose and users

GROOT aims to provide operational intelligence for growing startups: connect company information, investigate problems, explain findings, recommend actions, and eventually execute approved actions and verify outcomes. This intent comes from the root README and the supplied KT.

Intended users are startup founders, operations leaders, and functional teams; these are product assumptions, not validated personas. Current access is a developer-facing voice/orb prototype and Django administration, not a finished organization workspace.

## Current capabilities

| Area | Implemented | Product limitation |
| --- | --- | --- |
| Development setup | Declared LangChain/LangGraph dependencies, matching environment-based database settings, provider/Redis/frontend examples, read-only pgvector preflight and setup instructions | Requires operator-provisioned PostgreSQL/pgvector and external services; does not establish a complete knowledge workflow |
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
- Browser operations are tracked state/result stubs, without browser automation. The existing extraction test expects a string while the implementation returns `BrowserResult`; this pre-existing failure remains outside the setup module.
- No persistent conversations, resumable agent workflows, approval inbox, or investigation activity feed was found.

## Near-term product outcome

The recommended next milestone is one authenticated, organization-scoped knowledge question answered from ingested documents with inspectable evidence. Acceptance should demonstrate that:

1. The server establishes the user and organization from authenticated membership.
2. Document processing produces usable embeddings and handles reprocessing consistently.
3. Retrieval cannot return another organization's chunks.
4. One request reaches the existing KnowledgeAgent/RAG services and returns an answer plus evidence, including an honest insufficient-context response.

The first numbered prerequisite in [Task.md](Task.md), **Make setup reproducible**, is complete at its documented scope. The authenticated, organization-scoped knowledge flow remains the next product milestone; none of its acceptance criteria is claimed complete by the setup work.

## Setup verification

The 27 focused tests passed. Full regression results in both the existing and a fresh Python 3.14.4 environment: Django 84/84 passed; AI 172/173 passed, with the same browser extraction failure observed before implementation (baseline AI: 161/162 passed). The configured database passed the read-only check with pgvector 0.8.6. No new test failures were introduced. See [MEMORY.md](MEMORY.md) for commands and limits.

## Future direction

Extend the proven knowledge flow with useful read-only company tools, agent selection, evidence evaluation, then durable approvals, actual actions, and independent verification. Keep orchestration separate from Equaliator quality assessment. Add specialist agents when their data and tools exist. Persistent workflows, browser automation, event-triggered investigations, and richer UI are later increments; MongoDB, MCP, and distributed infrastructure are options rather than prerequisites.
