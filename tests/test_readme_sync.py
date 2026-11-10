"""README tables must equal what the renderer builds from the committed result files (document/number drift = failure)."""
import os
import re

import pytest

from infrastructure import render
from infrastructure.config import DEFAULT_MODELS, parse_models

ROOT = os.path.dirname(os.path.dirname(__file__))
NEEDED = ["README.md", "results/matrix.json", "logs/features.jsonl", "logs/http.jsonl"]


def block(text, name):
    m = re.search(r"<!-- AUTOGEN:%s:start -->\n(.*?)\n<!-- AUTOGEN:%s:end -->" % (name, name), text, re.S)
    return m.group(1)


@pytest.mark.skipif(not all(os.path.exists(os.path.join(ROOT, p)) for p in NEEDED), reason="result files not generated yet")
def test_readme_blocks_equal_rendered_results():
    os.chdir(ROOT)
    text = open("README.md").read()
    mx = render.load_matrix("results/matrix.json", parse_models(DEFAULT_MODELS))
    assert block(text, "matrix") == mx.to_markdown()
    assert block(text, "features") == render.features_markdown("logs/features.jsonl")
    assert block(text, "providers") == render.provider_stats_markdown("logs/http.jsonl")
    assert block(text, "judge") == render.judge_markdown("results/judge.json")


def test_readme_has_no_internal_traces():
    text = open(os.path.join(ROOT, "README.md")).read()
    for bad in ("[[", "projects/", "메인", "Jarvis", "TODO", "TBD"):
        assert bad not in text, bad
