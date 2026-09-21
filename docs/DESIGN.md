# GROOT — Design decisions and implementation patterns

Reviewed: 2026-09-21. This document describes observed design and its consequences, rather than prescribing a replacement architecture.

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
