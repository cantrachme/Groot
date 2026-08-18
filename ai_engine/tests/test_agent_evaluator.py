import unittest

from ai_engine.app.agents.result import AgentResult
from ai_engine.app.evaluation.agent_evaluator import (
    AgentEvaluator,
)


class AgentEvaluatorTests(unittest.TestCase):

    def setUp(self):
        self.evaluator = AgentEvaluator()

    def test_evaluates_successful_agent_result(self):
        result = AgentResult(
            success=True,
            agent_name="research_agent",
            summary="Research completed.",
            confidence=0.9,
            evidence=("source_1",),
        )

        evaluation = self.evaluator.evaluate(result)

        self.assertEqual(
            evaluation.evaluator_name,
            "agent_evaluator",
        )

        self.assertTrue(evaluation.passed)

    def test_includes_success_metric(self):
        result = AgentResult(
            success=True,
            agent_name="research_agent",
            summary="Research completed.",
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "success"
        )

        self.assertEqual(metric.score, 1.0)

    def test_failed_agent_result_has_failed_success_metric(self):
        result = AgentResult(
            success=False,
            agent_name="research_agent",
            summary="Research failed.",
            errors=("Database unavailable.",),
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "success"
        )

        self.assertEqual(metric.score, 0.0)

        self.assertFalse(evaluation.passed)

    def test_includes_confidence_metric(self):
        result = AgentResult(
            success=True,
            agent_name="research_agent",
            summary="Research completed.",
            confidence=0.85,
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "confidence"
        )

        self.assertEqual(metric.score, 0.85)

    def test_allows_missing_confidence(self):
        result = AgentResult(
            success=True,
            agent_name="research_agent",
            summary="Research completed.",
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "confidence"
        )

        self.assertIsNone(metric.score)

    def test_includes_evidence_metric(self):
        result = AgentResult(
            success=True,
            agent_name="research_agent",
            summary="Research completed.",
            evidence=(
                "source_1",
                "source_2",
            ),
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "evidence"
        )

        self.assertEqual(metric.score, 1.0)

        self.assertEqual(
            metric.details,
            {
                "evidence_count": 2,
            },
        )

    def test_missing_evidence_has_zero_score(self):
        result = AgentResult(
            success=True,
            agent_name="research_agent",
            summary="Research completed.",
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "evidence"
        )

        self.assertEqual(metric.score, 0.0)

    def test_includes_error_metric(self):
        result = AgentResult(
            success=False,
            agent_name="research_agent",
            summary="Research failed.",
            errors=(
                "Database unavailable.",
            ),
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "errors"
        )

        self.assertEqual(metric.score, 0.0)

        self.assertEqual(
            metric.details,
            {
                "error_count": 1,
            },
        )

    def test_successful_result_without_errors_has_full_error_score(self):
        result = AgentResult(
            success=True,
            agent_name="research_agent",
            summary="Research completed.",
        )

        evaluation = self.evaluator.evaluate(result)

        metric = next(
            metric
            for metric in evaluation.metrics
            if metric.name == "errors"
        )

        self.assertEqual(metric.score, 1.0)

    def test_failed_evaluation_contains_agent_errors_as_findings(self):
        result = AgentResult(
            success=False,
            agent_name="research_agent",
            summary="Research failed.",
            errors=(
                "Database unavailable.",
            ),
        )

        evaluation = self.evaluator.evaluate(result)

        self.assertEqual(
            evaluation.findings,
            (
                "Database unavailable.",
            ),
        )


if __name__ == "__main__":
    unittest.main()


class AgentEvaluatorPublicAPITests(unittest.TestCase):

    def test_public_api_exports_agent_evaluator(self):
        from ai_engine.app.evaluation import AgentEvaluator

        self.assertIsNotNone(AgentEvaluator)
