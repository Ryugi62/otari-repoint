"""AC-2 기능 점수(축 60): 흔적이 있는 기능만 10점씩, 상한 60. enabled != used."""
from domain.features import FeatureKind, FeatureTrace, feature_score


def traces(*kinds):
    return [FeatureTrace(kind=k, request_id=f"r-{k.value}") for k in kinds]


def test_four_used_features_score_40():
    t = traces(FeatureKind.ROUTING_FALLBACK, FeatureKind.WEB_FETCH, FeatureKind.CODE_EXECUTION, FeatureKind.BUDGET)
    assert feature_score(t) == 40


def test_six_used_features_score_60_and_duplicates_do_not_add():
    t = traces(*FeatureKind) + traces(FeatureKind.BUDGET)
    assert feature_score(t) == 60


def test_trace_without_request_id_does_not_count():
    assert feature_score([FeatureTrace(kind=FeatureKind.GUARDRAILS, request_id="")]) == 0


def test_rubric_lists_eight_features_and_any_six_used_score_60_with_cap():
    assert len(list(FeatureKind)) == 8 and {"mcp_integrations", "per_user_budgets"} <= {k.value for k in FeatureKind}
    four = traces(FeatureKind.ROUTING_FALLBACK, FeatureKind.BUDGET, FeatureKind.MULTI_MODEL_ROLES, FeatureKind.GUARDRAILS)
    assert feature_score(four) == 40
    assert feature_score(four + traces(FeatureKind.MCP, FeatureKind.PER_USER_BUDGET)) == 60
    assert feature_score(traces(*FeatureKind)) == 60
