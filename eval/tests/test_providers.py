"""The shared provider/key resolution every eval's CLI goes through."""

from __future__ import annotations

import pytest
from _providers import path_safe_model, provider_for, resolve_api_key


@pytest.mark.parametrize(
    ("model", "explicit", "provider"),
    [
        ("claude-sonnet-5", None, "anthropic"),
        ("gpt-5.6-sol", None, "openai"),
        ("o4-mini", None, "openai"),
        ("qwen/qwen3-235b-a22b", None, "openrouter"),
        ("claude-sonnet-5", "openrouter", "openrouter"),
    ],
)
def test_provider_inference(model: str, explicit: str | None, provider: str) -> None:
    assert provider_for(model, explicit) == provider


def test_unknown_model_and_provider_are_refused() -> None:
    with pytest.raises(SystemExit):
        provider_for("mystery-model")
    with pytest.raises(SystemExit):
        provider_for("claude-sonnet-5", "bedrock")


def test_key_resolution_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("OPEN_ROUTER_KEY", "fallback-key")
    monkeypatch.setenv("MY_KEY", "named-key")
    assert resolve_api_key("openrouter") == "fallback-key"
    assert resolve_api_key("openrouter", "MY_KEY") == "named-key"
    assert resolve_api_key("openrouter", "MY_KEY", "explicit") == "explicit"
    monkeypatch.delenv("OPEN_ROUTER_KEY")
    with pytest.raises(SystemExit):
        resolve_api_key("openrouter")


def test_path_safe_model() -> None:
    assert (
        path_safe_model("anthropic/claude-sonnet-4.5") == "anthropic__claude-sonnet-4.5"
    )
    assert path_safe_model("claude-sonnet-5") == "claude-sonnet-5"
