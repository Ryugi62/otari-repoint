"""Tasks, models, verdicts, and the task x model result matrix. Pure domain: no I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Tuple


class Verdict(Enum):
    PASS = "pass"
    FAIL = "fail"        # the model answered and the deterministic check rejected it
    BLOCKED = "blocked"  # no answer to judge: gateway/upstream error after retries (not a model-quality result)


@dataclass(frozen=True)
class ModelRef:
    provider: str
    model: str
    role: str  # worker | judge | baseline

    @property
    def selector(self) -> str:
        return "%s:%s" % (self.provider, self.model) if self.provider else self.model  # bare hosted catalog id has no provider part


@dataclass(frozen=True)
class Task:
    id: str
    kind: str                       # rule family: format | evidence | forbidden | injection | ...
    prompt: str
    check: Callable[[str], bool]    # deterministic checker over the normalized answer text
    system: str = ""


@dataclass
class Cell:
    verdict: Verdict
    answer: str = ""
    note: str = ""
    request_id: str = ""


@dataclass
class ResultMatrix:
    tasks: List[Task]
    models: List[ModelRef]
    cells: Dict[Tuple[str, str], Cell] = field(default_factory=dict)

    def put(self, task_id: str, model: ModelRef, cell: Cell) -> None:
        self.cells[(task_id, model.selector)] = cell

    def get(self, task_id: str, model: ModelRef) -> Cell:
        return self.cells[(task_id, model.selector)]

    def pass_rate(self, model: ModelRef) -> Tuple[int, int]:
        got = [self.get(t.id, model) for t in self.tasks if (t.id, model.selector) in self.cells]
        return sum(c.verdict is Verdict.PASS for c in got), len(got)

    def broken(self) -> List[Tuple[str, ModelRef, Cell]]:
        """Cells that are not PASS, for the 'where it breaks' list."""
        out = []
        for t in self.tasks:
            for m in self.models:
                c = self.cells.get((t.id, m.selector))
                if c and c.verdict is not Verdict.PASS:
                    out.append((t.id, m, c))
        return out

    def to_markdown(self) -> str:
        head = "| task | rule family | " + " | ".join("%s (%s)" % (m.model, m.role) for m in self.models) + " |"
        sep = "|---|---|" + "---|" * len(self.models)
        rows = [head, sep]
        for t in self.tasks:
            cells = []
            for m in self.models:
                c = self.cells.get((t.id, m.selector))
                cells.append(c.verdict.value if c else "-")
            rows.append("| %s | %s | %s |" % (t.id, t.kind, " | ".join(cells)))
        tot = []
        for m in self.models:
            p, n = self.pass_rate(m)
            tot.append("%d/%d" % (p, n))
        rows.append("| **pass** | | " + " | ".join(tot) + " |")
        return "\n".join(rows)
