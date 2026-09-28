import math
import subprocess
import sys
import unittest
from dataclasses import replace
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy.orm import Session

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentRegistry,
    AgentResult,
    AgentSelection,
    AgentSupervisor,
    CoordinationResult,
    DataAnalystAgent,
    KnowledgeAgent,
    MultiAgentCoordinator,
    ResearchAgent,
)
from ai_engine.app.equaliator import Equaliator, EqualiatorResult
from ai_engine.app.evaluation import AgentEvaluator, EvaluationResult
from ai_engine.app.llm.response import LLMResponse
from ai_engine.app.services.context_assembly_service import (
    AssembledContext,
    ContextItem,
)
from ai_engine.app.services.rag_service import RAGResponse


class RecordingAgent(Agent):
    description = "Trusted test reader"
    capabilities = ("read",)
    allowed_tools = ()

    def __init__(self, name, result=None, error=None):
        self.name = name
        self.result = result
        self.error = error
        self.contexts = []

    def execute(self, context):
        self.contexts.append(context)
        if self.error:
            raise self.error
        return self.result


def supported(name="first", **changes):
    return replace(
        AgentResult(
            success=True,
            agent_name=name,
            summary="Revenue is declining.",
            confidence=0.8,
            evidence=(
                {
                    "document_chunk_id": 12,
                    "text": "Revenue is declining.",
                    "similarity": 0.9,
                },
            ),
            data={"citations": (12,)},
        ),
        **changes,
    )


class CoordinationQualityTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()
        self.supervisor = AgentSupervisor(self.registry)
        self.coordinator = MultiAgentCoordinator(self.supervisor)
        self.context = AgentContext(
            user_id=7,
            organization_id=11,
            request_id=uuid4(),
            task="Investigate revenue",
            permissions=frozenset({"knowledge.read"}),
            state={"query": "Original request", "nested": {"items": [1, 2]}},
        )

    def run_results(self, *results):
        for result in results:
            self.registry.register(RecordingAgent(result.agent_name, result))
        return self.coordinator.execute(
            AgentSelection(
                tuple(result.agent_name for result in results), "Explicit selection"
            ),
            self.context,
        )

    def test_successful_multi_agent_investigation_reuses_existing_types(self):
        first, second = supported(), supported("second", confidence=1.0)
        result = self.run_results(first, second)
        self.assertIsInstance(result, CoordinationResult)
        self.assertTrue(
            all(isinstance(item, EvaluationResult) for item in result.evaluations)
        )
        self.assertIsInstance(result.quality, EqualiatorResult)
        self.assertEqual(result.results, (first, second))
        self.assertEqual(result.quality.results, result.results)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.quality.agreement, "HIGH")
        self.assertEqual(result.quality.evidence_quality, "HIGH")
        self.assertEqual(result.quality.confidence, 0.9)
        self.assertEqual(
            result.summary,
            "Investigation complete.\nfirst: Revenue is declining.\nsecond: Revenue is declining.",
        )

    def test_selection_order_not_registration_order_controls_every_output(self):
        self.registry.register(RecordingAgent("first", supported("first")))
        self.registry.register(RecordingAgent("second", supported("second")))
        selection = AgentSelection(("second", "first"), "Ordered")
        for _ in range(2):
            result = self.coordinator.execute(selection, self.context)
            self.assertIs(result.selection, selection)
            self.assertEqual(
                [item.agent_name for item in result.results], ["second", "first"]
            )
            self.assertEqual(
                [item.metadata["agent_name"] for item in result.evaluations],
                ["second", "first"],
            )
            self.assertEqual(
                [item.agent_name for item in result.quality.assessments],
                ["second", "first"],
            )

    def test_original_context_request_permissions_and_state_reach_every_agent(self):
        self.run_results(supported("first"), supported("second"))
        for agent in (self.registry.get("first"), self.registry.get("second")):
            self.assertIs(agent.contexts[0], self.context)
            self.assertEqual(
                agent.contexts[0].state,
                {"query": "Original request", "nested": {"items": [1, 2]}},
            )
            self.assertEqual(agent.contexts[0].task, "Investigate revenue")
            self.assertEqual(
                agent.contexts[0].permissions, frozenset({"knowledge.read"})
            )
        self.assertNotIn("results", self.context.state)

    def test_existing_evaluators_are_called_once_with_original_results(self):
        evaluator = Mock(wraps=AgentEvaluator())
        equaliator = Mock(wraps=Equaliator())
        self.coordinator = MultiAgentCoordinator(
            self.supervisor, evaluator=evaluator, equaliator=equaliator
        )
        first, second = supported(), supported("second")
        result = self.run_results(first, second)
        self.assertEqual(
            [call.args[0] for call in evaluator.evaluate.call_args_list],
            [first, second],
        )
        equaliator.evaluate.assert_called_once_with((first, second))
        self.assertEqual(len(result.evaluations), 2)

    def test_confidence_evidence_and_error_metrics_keep_actual_counts(self):
        result = self.run_results(supported())
        metrics = {item.name: item for item in result.evaluations[0].metrics}
        self.assertEqual(
            {name: metric.score for name, metric in metrics.items()},
            {
                "success": 1.0,
                "confidence": 0.8,
                "evidence": 1.0,
                "errors": 1.0,
                "groundedness": 1.0,
            },
        )
        self.assertEqual(metrics["evidence"].details["evidence_count"], 1)
        self.assertEqual(metrics["errors"].details["error_count"], 0)

    def test_partial_failure_preserves_success_and_failure_evidence(self):
        good = supported()
        bad = supported(
            "bad",
            success=False,
            summary="Failed",
            errors=("Unavailable",),
            confidence=None,
        )
        result = self.run_results(good, bad)
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.quality.missing_information, ("bad",))
        self.assertEqual(result.evaluations[1].findings, ("Unavailable",))
        self.assertEqual(result.evidence, good.evidence + bad.evidence)
        self.assertEqual(result.citations, (12, 12))
        self.assertIn("first: Revenue is declining.", result.summary)
        self.assertNotIn("bad: Failed", result.summary)

    def test_exception_becomes_redacted_failure_and_other_agents_still_run(self):
        denied = RecordingAgent("denied", error=PermissionError("secret bearer value"))
        ok = RecordingAgent("ok", supported("ok"))
        self.registry.register(denied)
        self.registry.register(ok)
        result = self.coordinator.execute(
            AgentSelection(("denied", "ok"), "Both"), self.context
        )
        self.assertEqual(result.status, "partial")
        self.assertEqual(
            result.results[0].errors, ("Agent execution failed (PermissionError).",)
        )
        self.assertNotIn("secret bearer value", repr(result))
        self.assertEqual(len(ok.contexts), 1)

    def test_all_failed_agents_produce_failed_investigation(self):
        result = self.run_results(supported(success=False, errors=("failed",)))
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.quality.investigation_complete)
        self.assertNotIn("Revenue is declining", result.summary)
        self.assertIn("No supported conclusion", result.summary)

    def test_empty_selection_is_incomplete(self):
        result = self.run_results()
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.results, ())
        self.assertEqual(result.evaluations, ())
        self.assertEqual(result.quality.agreement, "NO_RESULTS")
        self.assertTrue(
            any("No agents were selected" in value for value in result.limitations)
        )

    def test_unknown_agent_keeps_order_and_does_not_abort_others(self):
        self.registry.register(RecordingAgent("ok", supported("ok")))
        result = self.coordinator.execute(
            AgentSelection(("missing", "ok"), "Both"), self.context
        )
        self.assertEqual(result.status, "partial")
        self.assertEqual(
            [item.agent_name for item in result.results], ["missing", "ok"]
        )
        self.assertIn("AgentNotFoundError", result.results[0].errors[0])

    def test_invalid_result_identity_is_reported_as_failure(self):
        for returned in (None, supported("impersonated")):
            with self.subTest(returned=returned):
                registry = AgentRegistry()
                registry.register(RecordingAgent("selected", returned))
                result = MultiAgentCoordinator(AgentSupervisor(registry)).execute(
                    AgentSelection(("selected",), "One"),
                    self.context,
                )
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.results[0].agent_name, "selected")

    def test_success_flag_with_errors_cannot_complete(self):
        result = self.run_results(supported(errors=("Incomplete retrieval",)))
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.evaluations[0].passed)
        self.assertFalse(result.quality.investigation_complete)
        self.assertIsNone(result.quality.confidence)

    def test_placeholder_success_without_evidence_is_incomplete(self):
        self.registry.register(DataAnalystAgent())
        result = self.coordinator.execute(
            AgentSelection(("data_analyst_agent",), "Explicit"), self.context
        )
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.quality.unsupported_claims, ("data_analyst_agent",))
        self.assertFalse(result.quality.investigation_complete)
        self.assertNotIn("Data analysis completed", result.summary)

    def test_source_references_without_text_cannot_supply_a_conclusion(self):
        result = self.run_results(
            supported(evidence=("report",), data={"citations": ("report",)})
        )
        self.assertEqual(result.status, "incomplete")
        self.assertIsNone(result.evaluations[0].metrics[-1].score)
        self.assertIn("No supported conclusion", result.summary)
        self.assertTrue(
            any("No evidence text" in value for value in result.limitations)
        )

    def test_missing_confidence_is_explicit_and_not_invented(self):
        result = self.run_results(supported(confidence=None))
        self.assertEqual(result.status, "complete")
        self.assertIsNone(result.quality.confidence)
        self.assertTrue(
            any("Confidence was not supplied" in value for value in result.limitations)
        )

    def test_invalid_confidence_never_leaks_into_aggregate_metric(self):
        for confidence in (-0.1, 1.1, 10**1000, math.nan, math.inf, True, "0.8"):
            with self.subTest(confidence=confidence):
                item = supported(confidence=confidence)
                evaluation = AgentEvaluator().evaluate(item)
                quality = Equaliator().evaluate((item,))
                self.assertFalse(evaluation.passed)
                self.assertIsNone(evaluation.metrics[1].score)
                self.assertIsNone(quality.confidence)
                self.assertFalse(quality.investigation_complete)
                self.assertTrue(
                    any("finite number" in finding for finding in evaluation.findings)
                )

    def test_blank_evidence_and_empty_summary_are_not_support(self):
        for evidence in ((), (" ",), ({},), ({"text": ""},), (None,)):
            item = supported(evidence=evidence)
            with self.subTest(evidence=evidence):
                self.assertFalse(AgentEvaluator().evaluate(item).passed)
                self.assertEqual(
                    Equaliator().evaluate((item,)).unsupported_claims, ("first",)
                )
        self.assertFalse(AgentEvaluator().evaluate(supported(summary="...")).passed)

    def test_unrelated_or_partially_supported_claims_are_reported(self):
        for summary in (
            "Profit is growing.",
            "Revenue is declining. Profit is growing.",
        ):
            with self.subTest(summary=summary):
                item = supported(summary=summary)
                evaluation = AgentEvaluator().evaluate(item)
                self.assertFalse(evaluation.passed)
                self.assertEqual(evaluation.metrics[-1].score, 0.0)
                self.assertEqual(
                    Equaliator().evaluate((item,)).unsupported_claims, ("first",)
                )
        # A substring inside a negated/quoted claim must not count as support.
        item = supported(evidence=({"text": "It is false that revenue is declining."},))
        self.assertFalse(AgentEvaluator().evaluate(item).passed)

    def test_citations_must_reference_the_supplied_evidence(self):
        for citations in ((999,), (True,), ("12",), "12", ({"id": 12},)):
            with self.subTest(citations=citations):
                evaluation = AgentEvaluator().evaluate(
                    supported(data={"citations": citations})
                )
                self.assertFalse(evaluation.passed)
                self.assertIn(
                    "Citations do not match the supplied evidence.", evaluation.findings
                )

    def test_normalized_literal_statements_can_be_verified(self):
        result = self.run_results(supported(summary=" REVENUE   is declining! "))
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.evaluations[0].metrics[-1].score, 1.0)

    def test_opposite_polarity_is_a_conflict_and_prevents_conclusion(self):
        first = supported()
        second = supported(
            "second",
            summary="Revenue is not declining.",
            evidence=({"text": "Revenue is not declining."},),
            data={},
        )
        result = self.run_results(first, second)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.quality.agreement, "CONFLICT")
        self.assertEqual(len(result.quality.contradictions), 1)
        self.assertFalse(result.quality.investigation_complete)
        self.assertIn("No supported conclusion", result.summary)
        self.assertNotIn("first: Revenue", result.summary)

    def test_different_topics_are_not_claimed_to_be_contradictions(self):
        other = supported(
            "other",
            summary="Costs are stable.",
            evidence=({"text": "Costs are stable."},),
            data={},
        )
        result = self.run_results(supported(), other)
        self.assertEqual(result.quality.agreement, "PARTIAL")
        self.assertEqual(result.quality.contradictions, ())
        self.assertEqual(result.status, "complete")

    def test_knowledge_agent_evidence_citations_and_original_query_survive(self):
        rag = Mock()
        chunk = ContextItem(
            document_chunk_id=42, text="Revenue is declining.", similarity=0.93
        )
        rag.answer.return_value = RAGResponse(
            query="Original request",
            context=AssembledContext(text=chunk.text, items=(chunk,)),
            response=LLMResponse(text=chunk.text, tool_calls=()),
        )
        self.registry.register(KnowledgeAgent(rag))
        self.registry.register(ResearchAgent())
        with Session() as db:
            context = replace(
                self.context,
                state={
                    **self.context.state,
                    "db": db,
                    "top_k": 3,
                    "summary": "Revenue is declining.",
                    "evidence": ({"source": "report", "text": chunk.text},),
                    "citations": ("report",),
                },
            )
            result = self.coordinator.execute(
                AgentSelection(("knowledge_agent", "research_agent"), "Both"), context
            )
            rag.answer.assert_called_once_with(
                db=db, query="Original request", top_k=3, organization_id=11
            )
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.results[0].data["citations"], (42,))
        self.assertEqual(
            result.evidence[0],
            {"document_chunk_id": 42, "text": chunk.text, "similarity": 0.93},
        )
        self.assertEqual(result.citations, (42, "report"))
        self.assertEqual(result.results[0].metadata["context"], chunk.text)

    def test_knowledge_missing_session_is_failed(self):
        self.registry.register(KnowledgeAgent(Mock()))
        result = self.coordinator.execute(
            AgentSelection(("knowledge_agent",), "Knowledge"), self.context
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("database session", result.results[0].summary)

    def test_knowledge_empty_retrieval_is_incomplete_even_with_success_flag(self):
        rag = Mock()
        rag.answer.return_value = RAGResponse(
            query=self.context.task,
            context=AssembledContext(items=(), text=""),
            response=LLMResponse(
                "There is not enough document context to answer this question.",
                (),
            ),
        )
        self.registry.register(KnowledgeAgent(rag))
        with Session() as db:
            result = self.coordinator.execute(
                AgentSelection(("knowledge_agent",), "Knowledge"),
                replace(self.context, state={"db": db}),
            )
        self.assertTrue(result.results[0].success)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.evidence, ())
        self.assertEqual(result.citations, ())
        self.assertFalse(result.quality.investigation_complete)

    def test_returned_tool_calls_are_preserved_without_dispatch(self):
        call = {"name": "delete_document", "arguments": {"document_id": 12}}
        original = supported(tool_calls=(call,))
        result = self.run_results(original)
        self.assertEqual(result.results[0].tool_calls, (call,))
        self.assertEqual(len(self.registry.get("first").contexts), 1)
        self.assertEqual(result.status, "complete")

    def test_not_only_is_not_an_opposite_polarity_claim(self):
        first = supported(summary="Revenue is only declining.")
        second = supported("second", summary="Revenue is not only declining.")
        quality = Equaliator().evaluate((first, second))
        self.assertEqual(quality.contradictions, ())
        self.assertEqual(quality.agreement, "PARTIAL")

    def test_evidence_quality_requires_evidence_from_every_successful_agent(self):
        quality = Equaliator().evaluate(
            (supported(), supported("missing", evidence=(), data={}))
        )
        self.assertEqual(quality.evidence_quality, "PARTIAL")
        self.assertEqual(quality.unsupported_claims, ("missing",))
        self.assertFalse(quality.investigation_complete)

    def test_public_modules_import_independently(self):
        for module in (
            "ai_engine.app.evaluation",
            "ai_engine.app.equaliator",
            "ai_engine.app.agents",
        ):
            with self.subTest(module=module):
                process = subprocess.run(
                    [sys.executable, "-c", f"import {module}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
