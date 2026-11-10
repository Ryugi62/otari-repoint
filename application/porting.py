"""UC-1: run every task against every model, changing only the model string. Retries are logged, never hidden."""
from __future__ import annotations

from typing import Callable, List

from application.ports import GatewayPort, GatewayResponse
from domain.tasks import Cell, ModelRef, ResultMatrix, Task, Verdict
from domain.text import has_thought_leak, normalize_answer

RETRYABLE = {0, 429, 500, 502, 503, 504}


def ask(gateway: GatewayPort, model: str, task: Task, sleep: Callable[[float], None], tries: int = 6,
        max_tokens: int = 1024) -> GatewayResponse:
    messages = ([{"role": "system", "content": task.system}] if task.system else []) + [{"role": "user", "content": task.prompt}]
    resp = None
    for n in range(1, tries + 1):
        resp = gateway.complete(model, messages, label="matrix:%s:%s:try%d" % (task.id, model, n), max_tokens=max_tokens)
        if resp.status not in RETRYABLE:
            return resp
        sleep(3.0 * n)
    return resp


def judge(task: Task, resp: GatewayResponse) -> Cell:
    if not resp.ok:
        return Cell(Verdict.BLOCKED, note="HTTP %s %s" % (resp.status, resp.error or str(resp.body)[:120]), request_id=resp.request_id)
    raw = resp.text()
    ans = normalize_answer(raw)
    note = "thought-tag leaked into content" if has_thought_leak(raw) else ""
    ok = bool(ans) and task.check(ans)
    return Cell(Verdict.PASS if ok else Verdict.FAIL, answer=ans[:300], note=note, request_id=resp.request_id)


def run_matrix(gateway: GatewayPort, tasks: List[Task], models: List[ModelRef], sleep: Callable[[float], None],
               pool_map=map) -> ResultMatrix:
    """pool_map lets the composition root supply a thread pool; tests pass the builtin map."""
    matrix = ResultMatrix(tasks=tasks, models=models)
    jobs = [(t, m) for t in tasks for m in models]

    def one(job):
        t, m = job
        return t, m, judge(t, ask(gateway, m.selector, t, sleep))

    for t, m, cell in pool_map(one, jobs):
        matrix.put(t.id, m, cell)
    return matrix
