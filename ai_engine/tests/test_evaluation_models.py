import unittest

from ai_engine.app.evaluation import (
    EvaluationResult,
    MetricScore,
)


class MetricScoreTests(unittest.TestCase):

    def test_stores_metric_name_and_score(self):
        metric = MetricScore(
            name="groundedness",
            score=0.9,
        )

        self.assertEqual(
            metric.name,
            "groundedness",
        )
        self.assertEqual(
            metric.score,
            0.9,
        )

    def test_allows_missing_score(self):
        metric = MetricScore(
            name="cost",
            score=None,
        )

        self.assertIsNone(metric.score)

    def test_stores_metric_details(self):
        metric = MetricScore(
            name="tool_selection",
            score=1.0,
            details={
                "selected_tools": 2,
            },
        )

        self.assertEqual(
            metric.details,
            {
                "selected_tools": 2,
            },
        )


class EvaluationResultTests(unittest.TestCase):

    def test_stores_evaluation_result(self):
        metric = MetricScore(
            name="correctness",
            score=1.0,
        )

        result = EvaluationResult(
            evaluator_name="agent_evaluator",
            passed=True,
            metrics=(metric,),
            summary="Agent evaluation passed.",
        )

        self.assertEqual(
            result.evaluator_name,
            "agent_evaluator",
        )
        self.assertTrue(result.passed)
        self.assertEqual(
            result.metrics,
            (metric,),
        )
        self.assertEqual(
            result.summary,
            "Agent evaluation passed.",
        )

    def test_defaults_findings_to_empty_tuple(self):
        result = EvaluationResult(
            evaluator_name="agent_evaluator",
            passed=True,
            metrics=(),
            summary="No findings.",
        )

        self.assertEqual(
            result.findings,
            (),
        )

    def test_stores_findings(self):
        result = EvaluationResult(
            evaluator_name="trajectory_evaluator",
            passed=False,
            metrics=(),
            summary="Trajectory evaluation failed.",
            findings=(
                "Unnecessary tool call detected.",
            ),
        )

        self.assertEqual(
            result.findings,
            (
                "Unnecessary tool call detected.",
            ),
        )

    def test_defaults_metadata_to_empty_dictionary(self):
        result = EvaluationResult(
            evaluator_name="rag_evaluator",
            passed=True,
            metrics=(),
            summary="RAG evaluation passed.",
        )

        self.assertEqual(
            result.metadata,
            {},
        )

    def test_stores_metadata(self):
        result = EvaluationResult(
            evaluator_name="rag_evaluator",
            passed=True,
            metrics=(),
            summary="RAG evaluation passed.",
            metadata={
                "documents_retrieved": 5,
            },
        )

        self.assertEqual(
            result.metadata,
            {
                "documents_retrieved": 5,
            },
        )


class EvaluationPublicAPITests(unittest.TestCase):

    def test_public_api_exports_evaluation_types(self):
        from ai_engine.app.evaluation import (
            EvaluationResult,
            MetricScore,
        )

        self.assertIsNotNone(EvaluationResult)
        self.assertIsNotNone(MetricScore)


if __name__ == "__main__":
    unittest.main()
