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
