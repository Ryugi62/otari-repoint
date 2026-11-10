"""Turn result files into the markdown that README embeds, so documents cannot drift from measured results."""
from __future__ import annotations

import json
import re
from typing import List

from domain.catalog import build_tasks
from domain.features import FeatureKind
from domain.tasks import Cell, ModelRef, ResultMatrix, Verdict

FEATURE_LABEL = {
    "routing_fallback": "Model routing and fallbacks",
    "web_fetch": "Web fetch",
    "code_execution": "Code execution",
    "budget": "Budgets and spending limits",
    "multi_model_roles": "Multiple models, distinct roles",
    "guardrails": "Guardrails",
}


CALL = {
    "routing_fallback": 'model="fb" (policy: retired model, then gemma-4-26b, then gemma-4-31b)',
    "web_fetch": 'tools=[{"type":"otari_web_fetch"}]',
    "code_execution": 'tools=[{"type":"otari_code_execution"}]',
    "budget": "API key with a $0.0006 ceiling, repeated until blocked",
    "multi_model_roles": "worker call, then judge call, different providers",
    "guardrails": 'guardrails=[{"profile":"prompt-injection","mode":"block"}]',
}


def load_matrix(path: str, models: List[ModelRef]) -> ResultMatrix:
    raw = json.load(open(path))
    mx = ResultMatrix(tasks=build_tasks(), models=models)
    for key, c in raw.items():
        tid, sel = key.split("|", 1)
        mx.cells[(tid, sel)] = Cell(Verdict(c["verdict"]), c.get("answer", ""), c.get("note", ""), c.get("request_id", ""))
    return mx


def features_markdown(features_path: str) -> str:
    rows = ["| # | Otari feature | Call | Model | Request id | Evidence line (full record in `logs/http.jsonl`) |", "|---|---|---|---|---|---|"]
    order = [k.value for k in FeatureKind]
    recs = {}
    for line in open(features_path):
        r = json.loads(line)
        recs[r["feature"]] = r
    for i, k in enumerate(order, 1):
        r = recs.get(k)
        if not r:
            rows.append("| %d | %s | %s | - | - | **not demonstrated in this run** |" % (i, FEATURE_LABEL[k], CALL[k]))
            continue
        ev = r["evidence"].replace("|", "\\|")
        rows.append("| %d | %s | %s | %s | `%s` | `%s` |" % (i, FEATURE_LABEL[k], CALL[k].replace("|", "\\|"), r["model"], r["request_id"], ev))
    return "\n".join(rows)


def replace_block(text: str, name: str, body: str) -> str:
    pat = re.compile(r"(<!-- AUTOGEN:%s:start -->\n).*?(\n<!-- AUTOGEN:%s:end -->)" % (name, name), re.S)
    if not pat.search(text):
        raise ValueError("marker block %s missing" % name)
    return pat.sub(lambda m: m.group(1) + body + m.group(2), text)


def provider_stats_markdown(http_path: str) -> str:
    """Upstream reliability seen at the gateway: for each provider, calls answered 200 vs failed with a 5xx (from otari-provider / otari-error-provider headers)."""
    ok, bad = {}, {}
    for line in open(http_path):
        r = json.loads(line)
        h, st = r["response"]["headers"], r["response"]["status"]
        if st == 200 and h.get("otari-provider"):
            ok[h["otari-provider"]] = ok.get(h["otari-provider"], 0) + 1
        elif st >= 500 and h.get("otari-error-provider"):
            bad[h["otari-error-provider"]] = bad.get(h["otari-error-provider"], 0) + 1
    rows = ["| provider (as named in the gateway config) | HTTP 200 | HTTP 5xx from upstream |", "|---|---|---|"]
    for p in sorted(set(ok) | set(bad)):
        rows.append("| %s | %d | %d |" % (p, ok.get(p, 0), bad.get(p, 0)))
    return "\n".join(rows)


def judge_markdown(path: str) -> str:
    import os
    if not os.path.exists(path):
        return "**Not measured in the committed run**: `python3 -m infrastructure.cli judge` (part of `run-all`) was interrupted when the local container runtime stopped; no model-decided verdicts exist yet, so this snapshot has zero."
    d = json.load(open(path))
    s = d["summary"]
    rows = ["| measure | count |", "|---|---|",
            "| answers shown to the judge model (%d real worker answers that passed the check + %d known-bad answers, one per task) | %d |" % (
                sum(1 for c in d["cells"] if c["kind"] == "worker_answer"), sum(1 for c in d["cells"] if c["kind"] == "known_bad"), s["cells"]),
            "| verdicts decided by the model alone (`%s`) | %d |" % (d["judge"], s["decided_by_model"]),
            "| of those, agreeing with the deterministic check | %d |" % s["agree_with_deterministic_check"],
            "| known-bad answers the judge accepted as CORRECT | %d |" % s["wrong_answers_accepted"],
            "| good answers the judge rejected as WRONG | %d |" % s["good_answers_rejected"],
            "| not decided: blocked by gateway/upstream errors after 6 tries | %d |" % s["blocked"],
            "| not decided: unparseable reply | %d |" % s["unparseable"]]
    return "\n".join(rows)
