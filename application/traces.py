"""UC-2: read response headers into FeatureTrace. Only a header that proves use makes a trace."""
from __future__ import annotations

from typing import Mapping, Optional

from domain.features import FeatureKind, FeatureTrace


def trace_from_headers(headers: Mapping[str, str]) -> Optional[FeatureTrace]:
    h = {k.lower(): v for k, v in headers.items()}
    if h.get("otari-fallback", "").lower() == "true":
        line = "otari-provider: %s; otari-attempt-count: %s; otari-fallback: true" % (
            h.get("otari-provider", "?"), h.get("otari-attempt-count", "?"))
        return FeatureTrace(kind=FeatureKind.ROUTING_FALLBACK, request_id=h.get("otari-request-id", ""),
                            evidence=line, model=h.get("otari-model", ""))
    return None
