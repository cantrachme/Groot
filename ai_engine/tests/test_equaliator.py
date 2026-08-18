import unittest

from ai_engine.app.agents.result import AgentResult
from ai_engine.app.equaliator.evaluator import Equaliator


class EqualiatorTests(unittest.TestCase):
    def setUp(self):
        self.equaliator = Equaliator()

    def test_assesses_individual_agent_results(self):
        result = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
            confidence=0.9,
            evidence=("revenue_data",),
        )

        evaluation = self.equaliator.evaluate((result,))

        self.assertEqual(
            len(evaluation.assessments),
            1,
        )

        assessment = evaluation.assessments[0]

        self.assertEqual(
            assessment.agent_name,
            "finance_agent",
        )
        self.assertTrue(assessment.success)
        self.assertEqual(
            assessment.confidence,
            0.9,
        )
        self.assertEqual(
            assessment.evidence_count,
            1,
        )
        self.assertFalse(assessment.has_errors)

    def test_detects_high_agreement_for_matching_results(self):
        first = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Enterprise sales declined.",
        )

        second = AgentResult(
            success=True,
            agent_name="sales_agent",
            summary="Enterprise sales declined.",
        )

        evaluation = self.equaliator.evaluate(
            (first, second),
        )

        self.assertEqual(
            evaluation.agreement,
            "HIGH",
        )

    def test_detects_partial_agreement_for_different_results(self):
        first = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Enterprise sales declined.",
        )

        second = AgentResult(
            success=True,
            agent_name="product_agent",
            summary="No product regression detected.",
        )

        evaluation = self.equaliator.evaluate(
            (first, second),
        )

        self.assertEqual(
            evaluation.agreement,
            "PARTIAL",
        )

    def test_single_successful_result_has_insufficient_agreement(self):
        result = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
        )

        evaluation = self.equaliator.evaluate((result,))

        self.assertEqual(
            evaluation.agreement,
            "INSUFFICIENT",
        )

    def test_empty_results_have_no_results_agreement(self):
        evaluation = self.equaliator.evaluate(())

        self.assertEqual(
            evaluation.agreement,
            "NO_RESULTS",
        )

    def test_detects_unsupported_claims_without_evidence(self):
        result = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
        )

        evaluation = self.equaliator.evaluate((result,))

        self.assertEqual(
            evaluation.unsupported_claims,
            ("finance_agent",),
        )

    def test_supported_results_are_not_marked_as_unsupported(self):
        result = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
            evidence=("financial_report",),
        )

        evaluation = self.equaliator.evaluate((result,))

        self.assertEqual(
            evaluation.unsupported_claims,
            (),
        )

    def test_failed_agents_are_reported_as_missing_information(self):
        result = AgentResult(
            success=False,
            agent_name="sales_agent",
            summary="Sales analysis failed.",
            errors=("Database unavailable.",),
        )

        evaluation = self.equaliator.evaluate((result,))

        self.assertEqual(
            evaluation.missing_information,
            ("sales_agent",),
        )

        self.assertTrue(
            evaluation.additional_agent_needed,
        )

        self.assertFalse(
            evaluation.investigation_complete,
        )

    def test_complete_investigation_requires_successful_results(self):
        first = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
            evidence=("financial_report",),
        )

        second = AgentResult(
            success=True,
            agent_name="sales_agent",
            summary="Enterprise pipeline declined.",
            evidence=("pipeline_report",),
        )

        evaluation = self.equaliator.evaluate(
            (first, second),
        )

        self.assertFalse(
            evaluation.additional_agent_needed,
        )

        self.assertTrue(
            evaluation.investigation_complete,
        )

    def test_evidence_quality_is_high_when_all_agents_succeed_with_evidence(self):
        first = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
            evidence=("financial_report",),
        )

        second = AgentResult(
            success=True,
            agent_name="sales_agent",
            summary="Pipeline declined.",
            evidence=("pipeline_report",),
        )

        evaluation = self.equaliator.evaluate(
            (first, second),
        )

        self.assertEqual(
            evaluation.evidence_quality,
            "HIGH",
        )

    def test_evidence_quality_is_none_without_evidence(self):
        result = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
        )

        evaluation = self.equaliator.evaluate((result,))

        self.assertEqual(
            evaluation.evidence_quality,
            "NONE",
        )

    def test_calculates_average_confidence(self):
        first = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
            confidence=0.8,
        )

        second = AgentResult(
            success=True,
            agent_name="sales_agent",
            summary="Pipeline declined.",
            confidence=1.0,
        )

        evaluation = self.equaliator.evaluate(
            (first, second),
        )

        self.assertEqual(
            evaluation.confidence,
            0.9,
        )

    def test_returns_none_confidence_when_agents_have_no_confidence(self):
        result = AgentResult(
            success=True,
            agent_name="finance_agent",
            summary="Revenue declined.",
        )

        evaluation = self.equaliator.evaluate((result,))

        self.assertIsNone(
            evaluation.confidence,
        )


if __name__ == "__main__":
    unittest.main()


class EqualiatorPublicAPITests(unittest.TestCase):
    def test_public_api_exports_equaliator_types(self):
        from ai_engine.app.equaliator import (
            AgentAssessment,
            Equaliator,
            EqualiatorResult,
        )

        self.assertIsNotNone(AgentAssessment)
        self.assertIsNotNone(Equaliator)
        self.assertIsNotNone(EqualiatorResult)
