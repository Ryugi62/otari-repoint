"""Hosted Otari.ai needs only different env values: base url, key, and (if the catalog differs) model ids."""
import pytest

from infrastructure.config import DEFAULT_MODELS, load, parse_models


def test_default_models_are_two_open_weight_plus_one_baseline():
    ms = parse_models(DEFAULT_MODELS)
    assert [m.role for m in ms] == ["worker", "judge", "baseline"] and ms[0].selector == "gemma_small:gemma-4-26b-a4b-it"


def test_hosted_model_ids_can_be_swapped_by_env():
    ms = parse_models("a:x/y:worker,b:z:judge,c:q:baseline")
    assert ms[0].provider == "a" and ms[0].model == "x/y"


def test_wrong_role_order_is_rejected():
    with pytest.raises(ValueError):
        parse_models("a:x:judge,b:y:worker,c:z:baseline")


def test_base_url_and_key_come_from_env(monkeypatch):
    monkeypatch.setenv("OTARI_BASE_URL", "https://hosted.example")
    monkeypatch.setenv("OTARI_API_KEY", "tk-x")
    s = load()
    assert s.base_url == "https://hosted.example" and s.api_key == "tk-x"


def test_hosted_catalog_id_without_provider_prefix_is_a_valid_selector():
    ms = parse_models("gemini:gemma-4-26b-a4b-it:worker,gemini:gemma-4-31b-it:judge,google/gemini-3.5-flash-lite:baseline")
    assert [m.selector for m in ms] == ["gemini:gemma-4-26b-a4b-it", "gemini:gemma-4-31b-it", "google/gemini-3.5-flash-lite"]


def test_guardrail_url_and_run_models_come_from_env_and_file(monkeypatch, tmp_path):
    from infrastructure.config import load_run_models, save_run_models
    monkeypatch.setenv("OTARI_API_KEY", "tk-x")
    monkeypatch.setenv("REPOINT_GUARDRAIL_URL", "https://g.example")
    assert load().guardrail_url == "https://g.example"
    p = str(tmp_path / "models.json")
    ms = parse_models("gemini:a:worker,gemini:b:judge,google/c:baseline")
    save_run_models(p, ms)
    assert load_run_models(p) == ms
    assert load_run_models(str(tmp_path / "none.json")) == parse_models(DEFAULT_MODELS)
