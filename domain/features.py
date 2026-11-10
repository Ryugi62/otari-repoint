"""FeatureKind (the eight Otari capabilities listed by the rubric; the score counts at most six) and FeatureTrace (proof a feature was used)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

POINTS_PER_FEATURE = 10
FEATURE_SCORE_CAP = 60


class FeatureKind(Enum):
    ROUTING_FALLBACK = "routing_fallback"
    WEB_FETCH = "web_fetch"
    CODE_EXECUTION = "code_execution"
    BUDGET = "budget"
    MULTI_MODEL_ROLES = "multi_model_roles"
    GUARDRAILS = "guardrails"
    MCP = "mcp_integrations"
    PER_USER_BUDGET = "per_user_budgets"


@dataclass(frozen=True)
class FeatureTrace:
    kind: FeatureKind
    request_id: str
    evidence: str = ""  # one line quoted from the response headers/body/usage record
    model: str = ""     # which model served the request


def feature_score(traces: Iterable[FeatureTrace]) -> int:
    """Rubric axis 60: 10 points per distinct feature that has a trace with a request id (enabled != used)."""
    used = {t.kind for t in traces if t.request_id}
    return min(len(used) * POINTS_PER_FEATURE, FEATURE_SCORE_CAP)
