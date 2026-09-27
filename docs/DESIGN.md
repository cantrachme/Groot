# GROOT — Design decisions and implementation patterns

Verified: 2026-09-28 against baseline `231e3027fc4299dd94ed75451dc45dccf4b2dbc8` plus uncommitted setup changes. This document describes observed design and its consequences. Python tests and setup checks were run; frontend design remains source-reviewed only.

## System philosophy

GROOT separates company records from AI processing: Django provides the business foundation, while FastAPI coordinates model/tool and retrieval operations. Shared PostgreSQL provides a practical bridge. This keeps AI table ownership small, but direct reads of `core_documentchunk` couple retrieval to Django's schema and database configuration.

The historical product loop is understand → investigate → explain → recommend → approve → act → verify. Today these stages exist at different maturity levels. Building one complete flow through existing components is more useful than adding more agent names.

## Module responsibilities

| Module | Design and current limits |
| --- | --- |
| Django `integrations/` | Connector contract, registry, credential boundary, provider-specific normalization; only GitHub implemented |
| Django `ingestion/` | Coordinates fetching and persistence separately; stable external identities allow repeat ingestion |
| Django `documents/` | Small extractor/normalizer/chunker/persistence services assembled into a pipeline; text and PDF extraction |
| AI `llm/`, `tools/` | Provider-neutral response/tool-call contracts; registry/schema generation separates capabilities from provider APIs |
| AI `services/` | Embedding generation, similarity search, chunk loading, context assembly, answer generation; dependencies can be injected |
| AI `agents/` | Frozen dataclass context/results, named registry, explicit selection, single-node graph, sequential execution |
| AI `equaliator/`, `evaluation/` | Cross-result assessment versus single-result metrics; currently deterministic heuristics |
| AI `permissions/`, `approvals/`, `actions/`, `verification/`, `audit/` | Separate authorization, risk, execution, outcome, and event contracts; not yet an integrated control boundary |

Dataclass freezing is shallow: `state`, result `data`, and metadata may contain mutable objects. `AgentContext` has no conversation ID today and KnowledgeAgent expects a SQLAlchemy session in `state['db']`. Do not assume these objects can already be serialized for resumed workflows.

## Implemented setup design

The setup module keeps each service's existing entry points and database ownership. Django and AI configuration both locate the root `.env` relative to their source files and use the same `POSTGRES_*` names/defaults. Exported values win over dotenv values. This avoids a new cross-service configuration package while making consistency explicit and testable. Celery URLs follow the same override convention with the existing local defaults.

SQLAlchemy assembles and escapes URL components through `URL.create`; the public `DATABASE_URL` remains a string for Alembic. The engine, session factory, Base and migration ownership do not change. Tests exercise special characters in credentials and generate offline migration SQL through the existing Alembic path.

The pgvector checker is an explicit read-only setup command. It returns an enabled version, or explains whether the operator must install the server extension or enable it in the target database. Connection failures return a generic diagnostic without echoing driver parameters. It does not provision infrastructure or change the static HTTP health response.

Root and frontend environment examples are separate because Next.js reads its own project directory. The frontend example contains only the public AI service URL; provider secrets remain on the backend. README documents setup, extension prerequisites, service commands and tests.

Validation: 11 new tests; focused selection 27/27 passed; both existing and fresh Python environments report Django 84/84 and AI 172/173 with the same pre-existing browser failure. Live pgvector check passed at version 0.8.6. External services, full fresh database provisioning and frontend builds remain outside this verification.

## Knowledge design

Document content and ordered chunks remain Django-owned; vectors are AI-owned and identified by chunk ID/model. Query vectors are compared by cosine distance, then context assembly selects available nonblank chunk text and formats chunk IDs/similarity for the LLM. Context assembly has a nominal 12,000-character budget, not a tokenizer-based budget.

This design supports testing each stage independently. Its next integration needs are tenant scoping, a processing-to-embedding handoff, retry/reprocessing semantics, and cleanup of stale vectors. Preserve the existing services when solving these gaps.

`AIService.handle_rag()` currently duplicates answer assembly already available in `RAGService.answer()`, including a duplicate import of `RAGDocumentService`. The historical consolidation was therefore not a complete removal of orchestration duplication.

## Agent and evaluation maturity

- **KnowledgeAgent:** executes RAG with an injected service and session, returning chunk evidence and citations.
- **ResearchAgent:** carries through evidence/citations/comparison/summary supplied in context state; it does not search the web.
- **DataAnalystAgent and OperationsAgent:** return task summaries and capability metadata without querying business data.
- **Coordinator:** runs caller-selected agents sequentially through the supervisor; it neither plans an investigation nor synthesizes a final answer.
- **Equaliator:** exact normalized-summary agreement, evidence counts/presence, failed-agent detection, mean supplied confidence. Contradiction detection is a placeholder; evidence-free successes can still be marked complete.
- **AgentEvaluator:** reports success/confidence/evidence/errors; `passed` mirrors result success, not independently measured correctness.

These outputs are useful contracts but should not be presented as validated reasoning quality. Future evaluation should measure actual task outcomes and evidence support.

## Interface design

The current interface is a dark holographic orb/HUD prototype. `GrootOrb` owns the Three.js scene; `VoiceInput` owns speech/microphone interaction; `HandGestureController` supplies camera-based gesture state; the page coordinates request/response and browser speech synthesis.

Voice transcripts go to the same `/ai` endpoint as a text payload. Gestures drive visual interactions and displayed labels such as confirm/cancel; they do not call the approval/action modules. Status labels such as “SYSTEM ONLINE” are presentation text, not backend readiness telemetry. No investigation timeline, evidence browser, or persisted conversation UI exists.

## Decisions to carry forward

Keep native contracts, registry boundaries, narrow services, and separate evaluation/control responsibilities. Add trustworthy identity, evidence, and actual tool results before expanding automation. Persistent graph state, parallel execution, browser drivers, and additional databases require concrete use cases; none is necessary to replace the foundations already implemented.
