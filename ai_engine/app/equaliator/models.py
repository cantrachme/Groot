from dataclasses import dataclass

from ai_engine.app.agents.result import AgentResult


@dataclass(frozen=True)
class AgentAssessment:
    """Assessment of an individual agent result."""

    agent_name: str
    success: bool
    confidence: float | None
    evidence_count: int
    has_errors: bool


@dataclass(frozen=True)
class EqualiatorResult:
    """Structured evaluation of multiple agent results."""

    assessments: tuple[AgentAssessment, ...]
    agreement: str
    evidence_quality: str
    contradictions: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    missing_information: tuple[str, ...]
    additional_agent_needed: bool
    investigation_complete: bool
    confidence: float | None
    results: tuple[AgentResult, ...]
