from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from .context import AgentContext
from .result import AgentResult
from .supervisor import AgentSelection, AgentSupervisor

if TYPE_CHECKING:
    from ..equaliator.evaluator import Equaliator
    from ..equaliator.models import EqualiatorResult
    from ..evaluation.agent_evaluator import AgentEvaluator
    from ..evaluation.models import EvaluationResult


@dataclass(frozen=True)
class CoordinationResult:
    """Ordered investigation outputs and their existing quality contracts."""

    selection: AgentSelection
    results: tuple[AgentResult, ...]
    evaluations: tuple[EvaluationResult, ...] = ()
    quality: EqualiatorResult | None = None
    status: Literal["complete", "partial", "failed", "incomplete"] = "incomplete"
    summary: str = ""
    evidence: tuple[Any, ...] = ()
    citations: tuple[Any, ...] = ()
    limitations: tuple[str, ...] = ()


class MultiAgentCoordinator:
    """Run explicitly selected trusted agents; assess and attribute their outputs.

    The caller supplies an authenticated context. This is not an authentication
    endpoint or a sandbox for registered Python agents. Bound read tools still
    authorize each execution; no tool calls or actions are dispatched here.
    """

    def __init__(
        self,
        supervisor: AgentSupervisor,
        *,
        evaluator: AgentEvaluator | None = None,
        equaliator: Equaliator | None = None,
    ) -> None:
        # Local imports preserve independent public imports of agents/evaluators.
        from ..equaliator.evaluator import Equaliator
        from ..evaluation.agent_evaluator import AgentEvaluator

        self.supervisor = supervisor
        self.evaluator = evaluator if evaluator is not None else AgentEvaluator()
        self.equaliator = equaliator if equaliator is not None else Equaliator()

    def execute(
        self,
        selection: AgentSelection,
        context: AgentContext,
    ) -> CoordinationResult:
        from ..evaluation.support import citations, evidence_texts

        results = self.supervisor.execute(selection, context, capture_failures=True)
        evaluations = tuple(self.evaluator.evaluate(result) for result in results)
        quality = self.equaliator.evaluate(results)
        usable = tuple(
            result for result in results if result.success and not result.errors
        )
        if not results:
            status = "incomplete"
        elif not usable:
            status = "failed"
        elif len(usable) != len(results):
            status = "partial"
        elif (
            quality.investigation_complete
            and all(item.passed for item in evaluations)
            and all(evidence_texts(result) for result in results)
        ):
            status = "complete"
        else:
            status = "incomplete"

        limitations = [
            "Quality checks are deterministic heuristics, not independent factual verification.",
            "Agreement compares summary wording; contradiction checks cover explicit opposite not-polarity only.",
        ]
        if not results:
            limitations.append(
                "No agents were selected; no investigation was performed."
            )
        for result, evaluation in zip(results, evaluations, strict=True):
            limitations.extend(
                f"{result.agent_name}: {finding}" for finding in evaluation.findings
            )
            if not result.success and not result.errors:
                limitations.append(f"{result.agent_name}: Agent reported failure.")
            if result.confidence is None:
                limitations.append(f"{result.agent_name}: Confidence was not supplied.")
            if result.success and not evidence_texts(result):
                limitations.append(
                    f"{result.agent_name}: No evidence text was available for claim checking."
                )
        limitations.extend(quality.contradictions)
        summary = f"Investigation {status}."
        # Attribution only: no LLM synthesis, invented facts or action execution.
        if not quality.contradictions:
            summaries = [
                f"{result.agent_name}: {result.summary}"
                for result, evaluation in zip(results, evaluations, strict=True)
                if evaluation.passed and evidence_texts(result)
            ]
            if summaries:
                summary += "\n" + "\n".join(summaries)
        if summary == f"Investigation {status}.":
            summary += " No supported conclusion is available."

        return CoordinationResult(
            selection=selection,
            results=results,
            evaluations=evaluations,
            quality=quality,
            status=status,
            summary=summary,
            evidence=tuple(item for result in results for item in result.evidence),
            citations=tuple(item for result in results for item in citations(result)),
            limitations=tuple(dict.fromkeys(limitations)),
        )
