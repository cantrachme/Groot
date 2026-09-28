"""Deterministic support checks, not semantic truth or source authentication."""

import math
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agents.result import AgentResult


def valid_confidence(value: object) -> bool:
    return type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)


def statements(value: str) -> tuple[str, ...]:
    return tuple(
        normalized
        for part in re.split(r"(?<=[.!?])\s+|\n+", value)
        if (normalized := " ".join(part.casefold().split()).rstrip(".!?"))
    )


def evidence_items(result: "AgentResult") -> tuple[Any, ...]:
    return tuple(
        item
        for item in result.evidence
        if (
            isinstance(item, str)
            and item.strip()
            or isinstance(item, dict)
            and any(
                isinstance(item.get(key), str) and item[key].strip()
                for key in ("text", "source", "url")
            )
        )
    )


def evidence_texts(result: "AgentResult") -> tuple[str, ...]:
    return tuple(
        item["text"]
        for item in evidence_items(result)
        if isinstance(item, dict)
        and isinstance(item.get("text"), str)
        and item["text"].strip()
    )


def citations(result: "AgentResult") -> tuple[Any, ...]:
    value = result.data.get("citations", ()) if isinstance(result.data, dict) else ()
    return tuple(value) if isinstance(value, (tuple, list)) else ()


def support_findings(result: "AgentResult") -> tuple[str, ...]:
    if not result.success:
        return ()
    findings = []
    if not statements(result.summary):
        findings.append("No summary was supplied.")
    items = evidence_items(result)
    if not items:
        findings.append("No usable evidence supports this result.")
    texts = evidence_texts(result)
    if texts:
        supported = {statement for value in texts for statement in statements(value)}
        if any(claim not in supported for claim in statements(result.summary)):
            findings.append("Summary text is not verified by the supplied evidence.")
    references = []
    for item in items:
        if isinstance(item, str):
            references.append(item)
        else:
            references.extend(
                item.get(key) for key in ("document_chunk_id", "source", "url")
            )
    raw = result.data.get("citations", ()) if isinstance(result.data, dict) else ()
    if not isinstance(raw, (tuple, list)) or any(
        type(citation) not in (str, int)
        or not any(
            type(citation) is type(ref) and citation == ref for ref in references
        )
        for citation in citations(result)
    ):
        findings.append("Citations do not match the supplied evidence.")
    return tuple(findings)
