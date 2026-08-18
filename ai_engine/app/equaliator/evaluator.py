from .models import (
    AgentAssessment,
    EqualiatorResult,
)
from ai_engine.app.agents.result import AgentResult


class Equaliator:
    """Evaluates and compares results from multiple agents."""

    def evaluate(
        self,
        results: tuple[AgentResult, ...],
    ) -> EqualiatorResult:
        assessments = tuple(
            self._assess_result(result)
            for result in results
        )

        agreement = self._determine_agreement(results)
        evidence_quality = self._determine_evidence_quality(
            assessments,
        )

        contradictions = self._detect_contradictions(
            results,
        )

        unsupported_claims = tuple(
            result.agent_name
            for result in results
            if result.success
            and not result.evidence
        )

        missing_information = tuple(
            result.agent_name
            for result in results
            if not result.success
        )

        additional_agent_needed = bool(
            missing_information
            or contradictions
        )

        investigation_complete = (
            bool(results)
            and not additional_agent_needed
        )

        confidence = self._calculate_confidence(
            assessments,
        )

        return EqualiatorResult(
            assessments=assessments,
            agreement=agreement,
            evidence_quality=evidence_quality,
            contradictions=contradictions,
            unsupported_claims=unsupported_claims,
            missing_information=missing_information,
            additional_agent_needed=additional_agent_needed,
            investigation_complete=investigation_complete,
            confidence=confidence,
            results=results,
        )

    def _assess_result(
        self,
        result: AgentResult,
    ) -> AgentAssessment:
        return AgentAssessment(
            agent_name=result.agent_name,
            success=result.success,
            confidence=result.confidence,
            evidence_count=len(result.evidence),
            has_errors=bool(result.errors),
        )

    def _determine_agreement(
        self,
        results: tuple[AgentResult, ...],
    ) -> str:
        successful_results = tuple(
            result
            for result in results
            if result.success
        )

        if not successful_results:
            return "NO_RESULTS"

        if len(successful_results) == 1:
            return "INSUFFICIENT"

        summaries = {
            result.summary.strip().lower()
            for result in successful_results
        }

        if len(summaries) == 1:
            return "HIGH"

        return "PARTIAL"

    def _determine_evidence_quality(
        self,
        assessments: tuple[AgentAssessment, ...],
    ) -> str:
        if not assessments:
            return "NONE"

        total_evidence = sum(
            assessment.evidence_count
            for assessment in assessments
        )

        if total_evidence == 0:
            return "NONE"

        successful_agents = sum(
            assessment.success
            for assessment in assessments
        )

        if successful_agents == len(assessments):
            return "HIGH"

        return "PARTIAL"

    def _detect_contradictions(
        self,
        results: tuple[AgentResult, ...],
    ) -> tuple[str, ...]:
        successful_results = tuple(
            result
            for result in results
            if result.success
        )

        if len(successful_results) < 2:
            return ()

        return ()

    def _calculate_confidence(
        self,
        assessments: tuple[AgentAssessment, ...],
    ) -> float | None:
        confidence_values = tuple(
            assessment.confidence
            for assessment in assessments
            if assessment.success
            and assessment.confidence is not None
        )

        if not confidence_values:
            return None

        return sum(confidence_values) / len(
            confidence_values
        )
