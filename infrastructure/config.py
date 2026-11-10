"""Environment-driven settings. Switching to hosted Otari.ai means changing OTARI_BASE_URL and OTARI_API_KEY only."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple, Tuple

from domain.tasks import ModelRef


@dataclass
class Settings:
    base_url: str
    api_key: str
    master_key: Optional[str]
    capped_key: Optional[str]
    api_prefix: str
    workers: int
    models: List[ModelRef]
    policy: str
    guardrail_url: Optional[str] = None
    mcp_server_id: Optional[str] = None
    service_key: Optional[str] = None
    end_users: Tuple[str, str] = ("agent-low", "agent-high")
    end_user_budgets: Tuple[Optional[str], Optional[str]] = (None, None)
    mcp_server_id: Optional[str] = None
    service_key: Optional[str] = None
    end_users: Tuple[str, str] = ("agent-low", "agent-high")
    end_user_budgets: Tuple[Optional[str], Optional[str]] = (None, None)


DEFAULT_MODELS = "gemma_small:gemma-4-26b-a4b-it:worker,gemma_large:gemma-4-31b-it:judge,baseline:gemini-3.5-flash-lite:baseline"


def parse_models(spec: str) -> List[ModelRef]:
    """'provider:model:role,...' (exactly worker, judge, baseline in that order). Hosted model ids replace the defaults here."""
    out = []
    for item in spec.split(","):
        head, role = item.strip().rsplit(":", 1)
        provider, model = head.split(":", 1) if ":" in head else ("", head)
        out.append(ModelRef(provider, model, role))
    if [m.role for m in out] != ["worker", "judge", "baseline"]:
        raise ValueError("REPOINT_MODELS needs roles worker,judge,baseline in order")
    return out


def load() -> Settings:
    env = os.environ
    models = parse_models(env.get("REPOINT_MODELS", DEFAULT_MODELS))
    return Settings(
        base_url=env.get("OTARI_BASE_URL", "http://127.0.0.1:8000"),
        api_key=env["OTARI_API_KEY"],
        master_key=env.get("OTARI_MASTER_KEY") or None,
        capped_key=env.get("OTARI_CAPPED_KEY") or None,
        api_prefix=env.get("OTARI_API_PREFIX", "/api/v1"),
        workers=int(env.get("REPOINT_WORKERS", "4")),
        models=models,
        policy=env.get("REPOINT_POLICY", "fb"),
        guardrail_url=env.get("REPOINT_GUARDRAIL_URL") or None,
        mcp_server_id=env.get("REPOINT_MCP_SERVER_ID") or None,
        service_key=env.get("OTARI_SERVICE_KEY") or None,
        end_users=_pair(env.get("REPOINT_END_USERS"), ("agent-low", "agent-high")),
        end_user_budgets=_pair(env.get("REPOINT_END_USER_BUDGETS"), (None, None)),
    )


def _pair(raw, default):
    if not raw:
        return default
    a, b = [x.strip() for x in raw.split(",")]
    return (a, b)


def save_run_models(path: str, models: List[ModelRef]) -> None:
    """Remember which models a run used so `replay` renders the tables of that run, not of the defaults."""
    with open(path, "w") as f:
        json.dump([[m.provider, m.model, m.role] for m in models], f)


def load_run_models(path: str) -> List[ModelRef]:
    if not os.path.exists(path):
        return parse_models(DEFAULT_MODELS)
    return [ModelRef(p, m, r) for p, m, r in json.load(open(path))]
