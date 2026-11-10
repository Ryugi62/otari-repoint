"""The six-feature run keeps a trace only when the evidence is in the response; failures are named, not hidden."""
from application.features import FeatureConfig, run_features
from application.ports import GatewayResponse
from domain.features import FeatureKind


class Fake:
    def __init__(self, cap_after=2):
        self.n_capped = 0
        self.cap_after = cap_after

    def complete(self, model, messages, label, tools=None, guardrails=None, max_tokens=None, api_key=None):
        h = {"otari-request-id": "rid-" + label}
        if label.startswith("feature:routing"):
            h.update({"otari-fallback": "true", "otari-attempt-count": "2", "otari-provider": "b"})
            return GatewayResponse(200, h, {"choices": [{"message": {"content": "PONG"}}]}, "rid", "http.jsonl:1")
        if label.startswith("feature:web_fetch"):
            return GatewayResponse(200, h, {"choices": [{"message": {"content": "Example Domain"}}],
                                            "otari_tool_calls": [{"type": "web_fetch", "status": "completed", "url": "https://example.com/"}]}, "rid-w", "http.jsonl:2")
        if label.startswith("feature:code"):
            return GatewayResponse(200, h, {"choices": [{"message": {"content": "385"}}]}, "rid-c", "http.jsonl:3")
        if label.startswith("feature:budget"):
            self.n_capped += 1
            if self.n_capped > self.cap_after:
                return GatewayResponse(403, h, {"detail": "API key has $0.001 left", "code": "budget_exceeded"}, "rid-b", "http.jsonl:4")
            return GatewayResponse(200, h, {"choices": [{"message": {"content": "PONG"}}]}, "rid-bb", "http.jsonl:4")
        if label.startswith("feature:roles"):
            prov = "gemma_small" if "worker" in label else "gemma_large"
            h.update({"otari-provider": prov, "otari-model": prov})
            return GatewayResponse(200, h, {"choices": [{"message": {"content": "51" if "worker" in label else "CORRECT"}}]}, "rid-" + prov, "http.jsonl:5")
        if label.startswith("feature:guardrails:injection"):
            return GatewayResponse(403, h, {"detail": {"message": "blocked", "code": "guardrail_violation", "guardrails": [{"profile": "prompt-injection", "score": 0.99}]}}, "rid-g", "http.jsonl:6")
        return GatewayResponse(200, {"otari-guardrails": '[{"valid":true}]', **h}, {"choices": [{"message": {"content": "PONG"}}]}, "rid-ok", "http.jsonl:7")

    def usage_rows(self, request_id):
        return [{"billing_meters": {"tools": {"code_execution": {"billed": 1}}}}]


CFG = FeatureConfig("fb", "gemma_small:x", "gemma_large:y", "baseline:z", capped_key="tk-capped")


def test_all_six_features_traced_and_scored_60():
    rep = run_features(Fake(), CFG, sleep=lambda s: None)
    assert {t.kind for t in rep.traces} == set(FeatureKind) and rep.score == 60 and not rep.failures
    assert {e.rule for _, e, _ in rep.enforcements} == {"budget", "guardrail:prompt-injection"}


def test_unused_feature_gets_no_trace_and_a_named_failure():
    class NoCode(Fake):
        def usage_rows(self, request_id):
            return [{"billing_meters": {}}]
    rep = run_features(NoCode(), CFG, sleep=lambda s: None)
    assert FeatureKind.CODE_EXECUTION not in {t.kind for t in rep.traces}
    assert "code_execution" in rep.failures and rep.score == 50


def test_no_capped_key_means_no_budget_trace():
    rep = run_features(Fake(), FeatureConfig("fb", "a:b", "c:d", "e:f", capped_key=None), sleep=lambda s: None)
    assert FeatureKind.BUDGET not in {t.kind for t in rep.traces} and "budget" in rep.failures


def test_same_provider_name_but_different_models_counts_as_distinct_roles():
    class SameProv(Fake):
        def complete(self, model, messages, label, **kw):
            r = super().complete(model, messages, label, **kw)
            if label.startswith("feature:roles"):
                r.headers.update({"otari-provider": "gemini", "otari-model": "m-" + ("w" if "worker" in label else "j")})
            return r
    rep = run_features(SameProv(), CFG, sleep=lambda s: None)
    assert FeatureKind.MULTI_MODEL_ROLES in {t.kind for t in rep.traces}


def test_same_model_twice_is_not_distinct_roles():
    class Same(Fake):
        def complete(self, model, messages, label, **kw):
            r = super().complete(model, messages, label, **kw)
            if label.startswith("feature:roles"):
                r.headers.update({"otari-provider": "gemini", "otari-model": "same"})
            return r
    rep = run_features(Same(), CFG, sleep=lambda s: None)
    assert "multi_model_roles" in rep.failures


def test_guardrail_url_is_sent_with_the_guardrail_entry():
    seen = []

    class Rec(Fake):
        def complete(self, model, messages, label, **kw):
            if kw.get("guardrails"):
                seen.append(kw["guardrails"][0])
            return super().complete(model, messages, label, **kw)
    cfg = FeatureConfig("fb", "gemma_small:x", "gemma_large:y", "baseline:z", capped_key="tk-capped", guardrail_url="https://g.example")
    run_features(Rec(), cfg, sleep=lambda s: None)
    assert seen and all(g.get("url") == "https://g.example" for g in seen)


def test_budget_probe_asks_for_a_long_answer_so_the_ceiling_is_reached_in_few_calls():
    seen = []

    class Rec(Fake):
        def complete(self, model, messages, label, **kw):
            if label.startswith("feature:budget"):
                seen.append((messages[0]["content"], kw.get("max_tokens")))
            return super().complete(model, messages, label, **kw)
    run_features(Rec(), CFG, sleep=lambda s: None)
    assert seen and "150 words" in seen[0][0] and seen[0][1] >= 300
