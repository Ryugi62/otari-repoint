"""The judge model's verdicts are compared with the deterministic ground truth; blocked calls are not counted as decisions."""
from application.judging import run_judge_agreement, summarize
from application.ports import GatewayResponse
from domain.tasks import Cell, ModelRef, ResultMatrix, Task, Verdict

W, J = ModelRef("p", "w", "worker"), "p:judge"
T = Task("t1", "format", "say 42", lambda a: a == "42")


class Gw:
    def __init__(self, reply):
        self.reply = reply

    def complete(self, model, messages, label, **kw):
        r = self.reply(messages[0]["content"])
        return r if isinstance(r, GatewayResponse) else GatewayResponse(200, {}, {"choices": [{"message": {"content": r}}]}, "rid")

    def usage_rows(self, rid):
        return []


def mx():
    m = ResultMatrix([T], [W])
    m.put("t1", W, Cell(Verdict.PASS, "42"))
    return m


def test_perfect_judge_agrees_on_good_and_bad():
    gw = Gw(lambda p: "CORRECT" if "Agent answer:\n42" in p else "WRONG")
    cells = run_judge_agreement(gw, [T], mx(), W, J, {"t1": "41"}, lambda s: None)
    assert summarize(cells)["agree_with_deterministic_check"] == 2 and summarize(cells)["decided_by_model"] == 2


def test_judge_that_accepts_wrong_answer_is_counted():
    cells = run_judge_agreement(Gw(lambda p: "CORRECT"), [T], mx(), W, J, {"t1": "41"}, lambda s: None)
    s = summarize(cells)
    assert s["wrong_answers_accepted"] == 1 and s["agree_with_deterministic_check"] == 1


def test_blocked_and_unparseable_are_not_decisions():
    cells = run_judge_agreement(Gw(lambda p: GatewayResponse(502, {}, {})), [T], mx(), W, J, {"t1": "41"}, lambda s: None)
    assert summarize(cells)["blocked"] == 2 and summarize(cells)["decided_by_model"] == 0
    cells = run_judge_agreement(Gw(lambda p: "maybe"), [T], mx(), W, J, {}, lambda s: None)
    assert summarize(cells)["unparseable"] == 1
