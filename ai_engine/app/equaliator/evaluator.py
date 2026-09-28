import re
from itertools import combinations

from ai_engine.app.agents.result import AgentResult

from ..evaluation.support import (
    evidence_items,
    statements,
    support_findings,
    valid_confidence,
)
from .models import (
    AgentAssessment,
    EqualiatorResult,
)


class Equaliator:
    """Evaluates and compares results from multiple agents."""

    def evaluate(
        self,
        results: tuple[AgentResult, ...],
    ) -> EqualiatorResult:
        assessments = tuple(self._assess_result(result) for result in results)

        agreement = self._determine_agreement(results)
        evidence_quality = self._determine_evidence_quality(
            assessments,
        )

        contradictions = self._detect_contradictions(
            results,
        )

        unsupported_claims = tuple(
            result.agent_name for result in results if support_findings(result)
        )

        missing_information = tuple(
            result.agent_name
            for result in results
            if not result.success
            or result.errors
            or (
                result.confidence is not None
                and not valid_confidence(result.confidence)
            )
        )

        additional_agent_needed = bool(
            missing_information or contradictions or unsupported_claims
        )

        investigation_complete = bool(results) and not additional_agent_needed

        confidence = self._calculate_confidence(
            assessments,
        )

        return EqualiatorResult(
            assessments=assessments,
            agreement="CONFLICT" if contradictions else agreement,
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
            confidence=result.confidence
            if valid_confidence(result.confidence)
            else None,
            evidence_count=len(evidence_items(result)),
            has_errors=bool(result.errors),
        )

    def _determine_agreement(
        self,
        results: tuple[AgentResult, ...],
    ) -> str:
        successful_results = tuple(
            result for result in results if result.success and not result.errors
        )

        if not successful_results:
            return "NO_RESULTS"

        if len(successful_results) == 1:
            return "INSUFFICIENT"

        summaries = {
            " ".join(result.summary.casefold().split()) for result in successful_results
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

        total_evidence = sum(assessment.evidence_count for assessment in assessments)

        if total_evidence == 0:
            return "NONE"

        successful_agents = sum(assessment.success for assessment in assessments)

        if successful_agents == len(assessments) and all(
            item.evidence_count and not item.has_errors for item in assessments
        ):
            return "HIGH"

        return "PARTIAL"

    def _detect_contradictions(
        self,
        results: tuple[AgentResult, ...],
    ) -> tuple[str, ...]:
        successful_results = tuple(
            result for result in results if result.success and not result.errors
        )

        # Only detect the same explicit clause with opposite "not" polarity.
        # Different wording, numerical claims and implication are not inferred.
        clauses = []
        for result in successful_results:
            for statement in statements(result.summary):
                match = re.fullmatch(
                    r"(.+?) (is|are|was|were|has|have|had|can|will|does|do|did) (not )?(.+)",
                    statement,
                )
                if match and not match[4].startswith("only "):
                    clauses.append(
                        (
                            result.agent_name,
                            match[1],
                            match[2],
                            match[4],
                            bool(match[3]),
                        )
                    )
        return tuple(
            dict.fromkeys(
                f"{left[0]} and {right[0]} report opposite polarity for the same statement."
                for left, right in combinations(clauses, 2)
                if left[1:4] == right[1:4] and left[4] != right[4]
            )
        )

    def _calculate_confidence(
        self,
        assessments: tuple[AgentAssessment, ...],
    ) -> float | None:
        confidence_values = tuple(
            assessment.confidence
            for assessment in assessments
            if assessment.success
            and not assessment.has_errors
            and assessment.confidence is not None
        )

        if not confidence_values:
            return None

        return sum(confidence_values) / len(confidence_values)
