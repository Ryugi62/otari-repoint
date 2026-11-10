"""UC-1: model string is the only input that changes; infrastructure errors are BLOCKED, not FAIL; retries are bounded."""
from application.ports import GatewayResponse
from application.porting import run_matrix
from domain.tasks import ModelRef, Task, Verdict


class FakeGateway:
    def __init__(self, script):
        self.script, self.calls = script, []

    def complete(self, model, messages, label, **kw):
        self.calls.append((model, messages[-1]["content"]))
        r = self.script(model, len(self.calls))
        return r

    def usage_rows(self, request_id):
        return []


def ok(text):
    return GatewayResponse(200, {}, {"choices": [{"message": {"content": text}}]}, request_id="r")


T = Task("t1", "format", "say 42", lambda a: a == "42")
A, B = ModelRef("p", "a", "worker"), ModelRef("p", "b", "judge")


def test_only_model_string_changes_between_columns():
    gw = FakeGateway(lambda m, n: ok("42"))
    run_matrix(gw, [T], [A, B], sleep=lambda s: None)
    assert {c[1] for c in gw.calls} == {"say 42"} and {c[0] for c in gw.calls} == {"p:a", "p:b"}


def test_wrong_answer_is_fail_and_correct_is_pass():
    gw = FakeGateway(lambda m, n: ok("42" if m == "p:a" else "41"))
    mx = run_matrix(gw, [T], [A, B], sleep=lambda s: None)
    assert mx.get("t1", A).verdict is Verdict.PASS and mx.get("t1", B).verdict is Verdict.FAIL


def test_persistent_500_is_blocked_not_fail_after_bounded_retries():
    gw = FakeGateway(lambda m, n: GatewayResponse(500, {}, {"detail": "x"}))
    mx = run_matrix(gw, [T], [A], sleep=lambda s: None)
    assert mx.get("t1", A).verdict is Verdict.BLOCKED and len(gw.calls) == 6


def test_transient_500_then_ok_passes():
    gw = FakeGateway(lambda m, n: GatewayResponse(503, {}, {}) if n == 1 else ok("42"))
    mx = run_matrix(gw, [T], [A], sleep=lambda s: None)
    assert mx.get("t1", A).verdict is Verdict.PASS


def test_thought_tag_is_stripped_before_check_and_flagged():
    gw = FakeGateway(lambda m, n: ok("<thought>hm</thought>42"))
    c = run_matrix(gw, [T], [A], sleep=lambda s: None).get("t1", A)
    assert c.verdict is Verdict.PASS and "thought" in c.note
