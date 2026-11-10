"""Judge-agreement use case: the larger open-weight model decides CORRECT/WRONG for answers whose truth is known
(the worker's real answers that passed the deterministic check, plus one known-bad answer per task).
These are the only verdicts in the project decided by a model alone; their ground truth is the deterministic check."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from application.ports import GatewayPort
from application.porting import RETRYABLE
from domain.tasks import ResultMatrix, Task, Verdict
from domain.text import normalize_answer


@dataclass
class JudgeCell:
    task_id: str
    kind: str          # worker_answer | known_bad
    truth: bool        # deterministic ground truth: is this answer correct?
    said: str          # CORRECT | WRONG | BLOCKED | UNPARSEABLE
    request_id: str = ""

    @property
    def decided(self) -> bool:
        return self.said in ("CORRECT", "WRONG")

    @property
    def agrees(self) -> bool:
        return self.decided and (self.said == "CORRECT") == self.truth


def _ask(gw: GatewayPort, model: str, task: Task, answer: str, label: str, sleep: Callable[[float], None], tries: int = 6):
    prompt = ("You review one answer from an operations agent.\nTask given to the agent:\n%s\n\nAgent answer:\n%s\n\n"
              "Does the answer correctly and completely follow every instruction in the task? Reply with exactly one word: CORRECT or WRONG." % (task.prompt, answer))
    resp = None
    for n in range(1, tries + 1):
        resp = gw.complete(model, [{"role": "user", "content": prompt}], "%s:try%d" % (label, n), max_tokens=1024)
        if resp.status not in RETRYABLE:
            break
        sleep(3.0 * n)
    return resp


def run_judge_agreement(gw: GatewayPort, tasks: List[Task], matrix: ResultMatrix, worker, judge_model: str,
                        known_bad: Dict[str, str], sleep: Callable[[float], None], pool_map=map) -> List[JudgeCell]:
    jobs = []
    for t in tasks:
        cell = matrix.cells.get((t.id, worker.selector))
        if cell and cell.verdict is not Verdict.BLOCKED and cell.answer:
            jobs.append((t, "worker_answer", cell.answer, t.check(normalize_answer(cell.answer))))
        if t.id in known_bad:
            jobs.append((t, "known_bad", known_bad[t.id], t.check(normalize_answer(known_bad[t.id]))))

    def one(job):
        t, kind, ans, truth = job
        resp = _ask(gw, judge_model, t, ans, "judge:%s:%s" % (t.id, kind), sleep)
        if not resp.ok:
            return JudgeCell(t.id, kind, truth, "BLOCKED", resp.request_id)
        word = normalize_answer(resp.text()).strip().strip(".*").upper()
        return JudgeCell(t.id, kind, truth, word if word in ("CORRECT", "WRONG") else "UNPARSEABLE", resp.request_id)

    return list(pool_map(one, jobs))


def summarize(cells: List[JudgeCell]) -> Dict[str, int]:
    return {
        "cells": len(cells),
        "decided_by_model": sum(c.decided for c in cells),
        "agree_with_deterministic_check": sum(c.agrees for c in cells),
        "blocked": sum(c.said == "BLOCKED" for c in cells),
        "unparseable": sum(c.said == "UNPARSEABLE" for c in cells),
        "wrong_answers_accepted": sum(c.decided and (not c.truth) and c.said == "CORRECT" for c in cells),
        "good_answers_rejected": sum(c.decided and c.truth and c.said == "WRONG" for c in cells),
    }
