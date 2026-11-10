"""Enforcement: which operating rule a gateway policy blocked (AC-3, AC-5)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Enforcement:
    rule: str                  # "budget" | "guardrail:<profile>"
    upstream_called: bool      # a pre-flight block never reaches the model
    status: int = 0
    detail: str = ""


def classify_block(status: int, body: Any) -> Optional[Enforcement]:
    """Turn a 402/403 gateway answer into an Enforcement, or None when the request was not blocked by policy."""
    if status not in (402, 403) or not isinstance(body, dict):
        return None
    code = body.get("code")
    detail = body.get("detail")
    if isinstance(detail, dict):
        code = detail.get("code", code)
        if code == "guardrail_violation":
            profiles = [g.get("profile") for g in detail.get("guardrails", []) if isinstance(g, dict)]
            profile = profiles[0] if profiles else "unknown"
            return Enforcement(rule="guardrail:%s" % profile, upstream_called=False, status=status,
                               detail=str(detail.get("message", "")))
    if code == "budget_exceeded":
        return Enforcement(rule="budget", upstream_called=False, status=status,
                           detail=detail if isinstance(detail, str) else "")
    return None
