"""GatewayPort over HTTP (stdlib only). The same code talks to a self-hosted Otari or hosted Otari.ai:
only base_url and api_key differ. Every request/response pair is written to the log sink with secrets redacted."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from application.ports import GatewayResponse

SECRET_HEADERS = {"authorization", "otari-key", "x-api-key", "x-otari-key"}


class OtariHttp:
    def __init__(self, base_url: str, api_key: str, log: Callable[[dict], str], master_key: Optional[str] = None,
                 api_prefix: str = "/api/v1", timeout: float = 240.0):
        self.base = base_url.rstrip("/")
        self.prefix = api_prefix
        self.key = api_key
        self.master = master_key
        self.log = log
        self.timeout = timeout

    def _call(self, method: str, path: str, label: str, body: Optional[dict], key: str,
              extra_headers: Optional[Dict[str, str]] = None) -> GatewayResponse:
        url = self.base + self.prefix + path
        req_headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        req_headers.update(extra_headers or {})
        data = json.dumps(body).encode() if body is not None else None
        t0 = time.time()
        status, headers, raw, err = 0, {}, b"", ""
        try:
            req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                status, headers, raw = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            status, headers, raw = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
        except Exception as e:  # connection refused, timeout
            err = "%s: %s" % (type(e).__name__, e)
        try:
            parsed: Any = json.loads(raw.decode() or "null")
        except ValueError:
            parsed = raw.decode(errors="replace")
        rid = headers.get("otari-request-id", "")
        ref = self.log({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "label": label, "elapsed_ms": int((time.time() - t0) * 1000),
            "request": {"method": method, "url": url, "headers": {k: ("Bearer ***" if k.lower() in SECRET_HEADERS else v) for k, v in req_headers.items()}, "body": body},
            "response": {"status": status, "headers": headers, "body": parsed, "error": err},
        })
        return GatewayResponse(status, headers, parsed, rid, ref, err)

    def complete(self, model: str, messages: List[Dict[str, str]], label: str, *, tools: Optional[List[dict]] = None,
                 guardrails: Optional[List[dict]] = None, max_tokens: Optional[int] = None,
                 api_key: Optional[str] = None, extra: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None) -> GatewayResponse:
        body: Dict[str, Any] = {"model": model, "messages": messages, "temperature": 0}
        if max_tokens:
            body["max_tokens"] = max_tokens
        if tools:
            body["tools"] = tools
        if guardrails:
            body["guardrails"] = guardrails
        body.update(extra or {})  # top-level request fields such as mcp_server_ids or user
        return self._call("POST", "/chat/completions", label, body, api_key or self.key, headers)

    def usage_rows(self, request_id: str) -> List[dict]:
        """Operator view (master key) gives per-meter rows; with only an API key the settlement record is returned."""
        if self.master:
            r = self._call("GET", "/usage?limit=100", "usage:list", None, self.master)
            rows = r.body if isinstance(r.body, list) else []
            return [dict(row, _log_ref=r.log_ref) for row in rows if row.get("request_group_id") == request_id]
        r = self._call("GET", "/usage/requests/%s" % request_id, "usage:settlement", None, self.key)
        return [dict(r.body, _log_ref=r.log_ref)] if r.ok and isinstance(r.body, dict) else []
