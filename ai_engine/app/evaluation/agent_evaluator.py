from ai_engine.app.agents.result import AgentResult

from .models import EvaluationResult, MetricScore
from .support import evidence_items, evidence_texts, support_findings, valid_confidence


class AgentEvaluator:
    """Evaluates a single agent result."""

    def evaluate(
        self,
        result: AgentResult,
    ) -> EvaluationResult:
        support = support_findings(result)
        invalid_confidence = result.confidence is not None and not valid_confidence(
            result.confidence
        )
        findings = result.errors + support
        if invalid_confidence:
            findings += ("Confidence must be a finite number between 0 and 1.",)
        metrics = (
            MetricScore(
                name="success",
                score=1.0 if result.success else 0.0,
            ),
            MetricScore(
                name="confidence",
                score=None if invalid_confidence else result.confidence,
            ),
            MetricScore(
                name="evidence",
                score=1.0 if evidence_items(result) else 0.0,
                details={
                    "evidence_count": len(
                        result.evidence,
                    ),
                },
            ),
            MetricScore(
                name="errors",
                score=1.0 if not result.errors else 0.0,
                details={
                    "error_count": len(
                        result.errors,
                    ),
                },
            ),
            MetricScore(
                name="groundedness",
                score=(0.0 if support else 1.0 if evidence_texts(result) else None)
                if result.success
                else None,
                details={"method": "exact_normalized_statements"},
            ),
        )

        return EvaluationResult(
            evaluator_name="agent_evaluator",
            passed=result.success and not findings,
            metrics=metrics,
            summary=(f"Evaluation for agent '{result.agent_name}'."),
            findings=findings,
            metadata={"agent_name": result.agent_name},
        )
