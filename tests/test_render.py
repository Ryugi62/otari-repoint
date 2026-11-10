"""README tables are generated from result files, so a document can never disagree with the measured numbers."""
import json

import pytest

from infrastructure import render


def test_replace_block_swaps_only_the_marked_region():
    t = "a\n<!-- AUTOGEN:x:start -->\nold\n<!-- AUTOGEN:x:end -->\nz"
    assert render.replace_block(t, "x", "new") == "a\n<!-- AUTOGEN:x:start -->\nnew\n<!-- AUTOGEN:x:end -->\nz"


def test_missing_marker_is_an_error_not_a_silent_skip():
    with pytest.raises(ValueError):
        render.replace_block("nothing", "x", "new")


def test_feature_without_trace_is_shown_as_not_demonstrated(tmp_path):
    p = tmp_path / "f.jsonl"
    p.write_text(json.dumps({"feature": "web_fetch", "request_id": "r1", "model": "m", "evidence": "e"}) + "\n")
    md = render.features_markdown(str(p))
    assert "`r1`" in md and md.count("not demonstrated") == 7
