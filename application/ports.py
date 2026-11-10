"""Ports the use cases depend on. Adapters implement them; application code never imports an adapter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class GatewayResponse:
    status: int
    headers: Dict[str, str]          # lower-cased names
    body: Any                        # parsed JSON when possible, else text
    request_id: str = ""
    log_ref: str = ""                # "http.jsonl:<line>" pointer to the full request/response record
    error: str = ""                  # transport-level error (timeout, refused), status 0

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def text(self) -> str:
        try:
            return self.body["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return ""


class GatewayPort(Protocol):
    def complete(self, model: str, messages: List[Dict[str, str]], label: str, *, tools: Optional[List[dict]] = None,
                 guardrails: Optional[List[dict]] = None, max_tokens: Optional[int] = None,
                 api_key: Optional[str] = None, extra: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None) -> GatewayResponse: ...

    def usage_rows(self, request_id: str) -> List[dict]: ...


class SleepPort(Protocol):
    def __call__(self, seconds: float) -> None: ...
