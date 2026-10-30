"""AC-3, AC-5 차단 응답을 Enforcement(어느 규칙이 막았나)로 분류한다."""
from domain.enforcement import classify_block


def test_budget_exceeded_403_is_budget_enforcement():
    e = classify_block(403, {"detail": "API key has $0.05 ...", "code": "budget_exceeded"})
    assert e.rule == "budget" and e.upstream_called is False


def test_guardrail_violation_403_is_guardrail_enforcement():
    body = {"detail": {"message": "blocked", "code": "guardrail_violation", "guardrails": [{"profile": "prompt-injection", "score": 0.99}]}}
    e = classify_block(403, body)
    assert e.rule == "guardrail:prompt-injection"


def test_ok_response_is_not_enforcement():
    assert classify_block(200, {}) is None
