from ai_engine.app.agents.result import AgentResult

from .models import EvaluationResult, MetricScore


class AgentEvaluator:
    """Evaluates a single agent result."""

    def evaluate(
        self,
        result: AgentResult,
    ) -> EvaluationResult:
        metrics = (
            MetricScore(
                name="success",
                score=1.0 if result.success else 0.0,
            ),
            MetricScore(
                name="confidence",
                score=result.confidence,
            ),
            MetricScore(
                name="evidence",
                score=1.0 if result.evidence else 0.0,
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
        )

        return EvaluationResult(
            evaluator_name="agent_evaluator",
            passed=result.success,
            metrics=metrics,
            summary=(
                f"Evaluation for agent "
                f"'{result.agent_name}'."
            ),
            findings=result.errors,
        )
