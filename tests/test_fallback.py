"""AC-1 응답 헤더로 폴백 흔적을 읽는다."""
from domain.features import FeatureKind
from application.traces import trace_from_headers


def test_fallback_header_true_gives_routing_trace():
    h = {"otari-request-id": "f666", "otari-fallback": "true", "otari-attempt-count": "2", "otari-provider": "stubb"}
    t = trace_from_headers(h)
    assert t.kind is FeatureKind.ROUTING_FALLBACK and t.request_id == "f666"


def test_no_fallback_gives_no_trace():
    assert trace_from_headers({"otari-request-id": "x", "otari-fallback": "false"}) is None
