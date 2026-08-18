from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MetricScore:
    """A single named evaluation metric."""

    name: str
    score: float | None
    details: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(frozen=True)
class EvaluationResult:
    """Structured result produced by an evaluator."""

    evaluator_name: str
    passed: bool
    metrics: tuple[MetricScore, ...]
    summary: str
    findings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )
