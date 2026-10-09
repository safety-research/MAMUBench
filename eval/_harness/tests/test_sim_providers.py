"""Target bindings on the simulated harness: every provider bound exactly as the paper's runs bound it.

The api_key runs pre-bind the target through `_eval_runner.target_model` under `TARGET_REASONING` (Claude none,
GPT medium, Qwen minimal); the clinic runs bind every role through `_multiagent_pi.build_roles` under `TARGET_THINKING` (Claude 0, GPT
medium, Qwen low). Either way the house auditor and judge stay on the Anthropic key and a non-Anthropic target
reads its own provider key, never the Anthropic one. No network: models are constructed, never called.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from _eval_runner import keyed_roles
from _multiagent_pi.roles import ADAPTIVE_THINKING_MAX_TOKENS
from api_key import cells as api_cells
from clinic import cells as clinic_cells
from inspect_ai.model import Model

from _harness import sim
from _harness.runner import RunConfig

TARGET_KEY = "sk-target-test"
HOUSE_KEY = "sk-ant-house-test"


def _config(eval_name: str, model: str, provider: str, **kw: Any) -> RunConfig:
    return RunConfig(
        eval=eval_name,
        scenario="x",
        formation="team",
        model=model,
        provider=provider,
        runs_root=Path("/tmp/unused"),
        harness="sim",
        **kw,
    )


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    for name in (
        "KEYS",
        "TARGET_REASONING",
        "TARGET_THINKING",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "OPEN_ROUTER_KEY",
        "GPT_FAST",
        "OPUS_NO_FAST",
        sim.KEY_ENV,
        sim.HOUSE_KEY_ENV,
    ):
        monkeypatch.delenv(name, raising=False)
    yield monkeypatch


def _bound(
    config: RunConfig, recipe: sim.SimRecipe
) -> tuple[dict[str, str], dict[str, str | Model]]:
    """`(role env, keyed roles)` exactly as `_play` binds them (inside the episode's env)."""
    keys = sim.SimKeys(
        TARGET_KEY, HOUSE_KEY if config.provider != "anthropic" else TARGET_KEY
    )
    env = {
        "MAX_CONNECTIONS": str(recipe.max_connections),
        "PETRI_GENERATE_TIMEOUT": str(recipe.generate_timeout_s),
        **sim._role_env(  # pyright: ignore[reportPrivateUsage]
            config, recipe, keys, sim.target_effort(config, recipe)
        ),
    }
    with sim._environ(env):  # pyright: ignore[reportPrivateUsage]
        roles = sim._roles(config, recipe, keys)  # pyright: ignore[reportPrivateUsage]
        keyed = keyed_roles(roles)
    return env, keyed


def _model(roles: dict[str, str | Model], role: str) -> Model:
    model = roles[role]
    assert isinstance(model, Model)
    return model


def _api_key_of(model: Model) -> str | None:
    return cast(str | None, getattr(model.api, "api_key", None))


@pytest.mark.parametrize(
    ("model", "provider", "effort", "key_var"),
    [
        ("gpt-5.6-sol", "openai", "medium", "OPENAI_API_KEY"),
        ("gpt-5.6-terra", "openai", "medium", "OPENAI_API_KEY"),
        ("qwen/qwen3.8-max", "openrouter", "minimal", "OPENROUTER_API_KEY"),
    ],
)
def test_api_key_binds_a_non_anthropic_target_on_its_own_key(
    clean_env: pytest.MonkeyPatch,
    model: str,
    provider: str,
    effort: str,
    key_var: str,
) -> None:
    recipe = api_cells.build_sim_recipe("stakes_100", "team")
    env, roles = _bound(_config("api_key", model, provider), recipe)
    # as the paper's runs keyed them: only the house roles are keyed; the target is absent from KEYS
    assert env["KEYS"] == f"auditor:{sim.HOUSE_KEY_ENV},judge:{sim.HOUSE_KEY_ENV}"
    assert "target" not in env["KEYS"] and "*" not in env["KEYS"]
    assert env[key_var] == TARGET_KEY and env[sim.HOUSE_KEY_ENV] == HOUSE_KEY
    assert sim.KEY_ENV not in env and env["TARGET_REASONING"] == effort
    target = _model(roles, "target")
    assert target.config.reasoning_effort == effort
    assert target.config.max_tokens == ADAPTIVE_THINKING_MAX_TOKENS == 32000
    assert target.config.timeout == 900 and target.config.max_connections == 12
    assert _api_key_of(target) == TARGET_KEY
    assert f"{provider}/{target.api.model_name}" == f"{provider}/{model}"
    for house in ("auditor", "judge"):
        assert _api_key_of(_model(roles, house)) == HOUSE_KEY


def test_api_key_anthropic_target_shares_the_key_and_sends_no_thinking(
    clean_env: pytest.MonkeyPatch,
) -> None:
    recipe = api_cells.build_sim_recipe("stakes_100", "coordinator")
    env, roles = _bound(_config("api_key", "claude-opus-5", "anthropic"), recipe)
    assert env["KEYS"] == f"*:{sim.KEY_ENV}" and env[sim.KEY_ENV] == TARGET_KEY
    assert "OPENAI_API_KEY" not in env and env["TARGET_REASONING"] == "none"
    target = _model(roles, "target")
    assert target.config.reasoning_effort == "none"
    assert _api_key_of(target) == TARGET_KEY
    # `none` reaches the Anthropic provider as NO thinking parameter (thinking not requested)
    request = cast(Any, target.api).completion_config(target.config)[0]
    assert "thinking" not in request and request["model"] == "claude-opus-5"
    for house in ("auditor", "judge"):
        assert _api_key_of(_model(roles, house)) == TARGET_KEY


@pytest.mark.parametrize(
    ("model", "provider", "thinking", "service_tier"),
    [
        ("gpt-5.6-sol", "openai", "medium", "priority"),
        ("gpt-5.6-terra", "openai", "medium", "priority"),
        ("qwen/qwen3.8-max", "openrouter", "low", None),
    ],
)
def test_clinic_binds_a_non_anthropic_target_through_build_roles(
    clean_env: pytest.MonkeyPatch,
    model: str,
    provider: str,
    thinking: str,
    service_tier: str | None,
) -> None:
    recipe = clinic_cells.build_sim_recipe("warfarin_inr_plain", "team")
    config = _config("clinic", model, provider)
    env, roles = _bound(config, recipe)
    assert env["KEYS"] == f"auditor:{sim.HOUSE_KEY_ENV},judge:{sim.HOUSE_KEY_ENV}"
    assert env["TARGET_THINKING"] == thinking
    assert (env["GPT_FAST"], env["OPUS_NO_FAST"]) == ("1", "0")
    target = _model(roles, "target")
    assert target.config.reasoning_effort == thinking
    assert target.config.max_tokens == ADAPTIVE_THINKING_MAX_TOKENS
    assert target.config.max_connections == 8 and target.config.timeout == 3600
    assert getattr(target.api, "service_tier", None) == service_tier
    assert _api_key_of(target) == TARGET_KEY
    for house in ("auditor", "judge"):
        assert _api_key_of(_model(roles, house)) == HOUSE_KEY
    assert sim.target_serving(config, recipe) == (service_tier or "standard")


@pytest.mark.parametrize(
    ("formation", "timeout"),
    [("team", 3600), ("team_silent", 3600), ("coordinator", 900)],
)
def test_clinic_teams_bind_the_one_hour_generate_timeout(
    clean_env: pytest.MonkeyPatch, formation: str, timeout: int
) -> None:
    recipe = clinic_cells.build_sim_recipe("warfarin_inr_plain", formation)
    assert recipe.instrument == ("hero" if formation == "coordinator" else "standard")
    _, roles = _bound(_config("clinic", "claude-sonnet-5", "anthropic"), recipe)
    target = _model(roles, "target")
    assert target.config.timeout == timeout and target.config.reasoning_effort is None


def test_clinic_opus_target_sends_the_fast_mode_beta_without_thinking(
    clean_env: pytest.MonkeyPatch,
) -> None:
    recipe = clinic_cells.build_sim_recipe("warfarin_inr_plain", "coordinator")
    config = _config("clinic", "claude-opus-5", "anthropic")
    env, roles = _bound(config, recipe)
    assert env["KEYS"] == f"*:{sim.KEY_ENV}" and env["TARGET_THINKING"] == "0"
    target = _model(roles, "target")
    assert target.config.reasoning_effort is None
    assert getattr(target.api, "betas", None) == ["fast-mode-2026-02-01"]
    assert _api_key_of(target) == TARGET_KEY
    assert sim.target_serving(config, recipe) == "fast"


def test_house_key_resolution(clean_env: pytest.MonkeyPatch) -> None:
    api = api_cells.build_sim_recipe("stakes_100", "team")
    clinic = clinic_cells.build_sim_recipe("warfarin_inr_plain", "team")
    gpt = _config("api_key", "gpt-5.6-sol", "openai")
    claude = _config("api_key", "claude-opus-5", "anthropic")
    assert sim.resolve_keys(claude, api, TARGET_KEY) == sim.SimKeys(
        TARGET_KEY, TARGET_KEY
    )
    # the escalation auditor generates live: a GPT target needs the Anthropic key too
    with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY"):
        sim.resolve_keys(gpt, api, TARGET_KEY)
    # clinic's auditor=none never calls the house roles: a placeholder is safe there
    assert sim.resolve_keys(gpt, clinic, TARGET_KEY).house == sim.UNUSED_HOUSE_KEY
    clean_env.setenv("ANTHROPIC_API_KEY", HOUSE_KEY)
    assert sim.resolve_keys(gpt, api, TARGET_KEY) == sim.SimKeys(TARGET_KEY, HOUSE_KEY)
    fake = replace(gpt, fake_model=True)
    assert sim.resolve_keys(fake, api, "x").target == "fake-not-used"


def test_the_reasoning_setting_is_always_the_papers_for_the_provider() -> None:
    """No override: the target's dial is the paper's per-provider value, and the record says so."""
    api = api_cells.build_sim_recipe("stakes_100", "team")
    clinic = clinic_cells.build_sim_recipe("warfarin_inr_plain", "team")
    for model, provider, api_effort, clinic_effort in (
        ("claude-opus-5", "anthropic", "none", "0"),
        ("gpt-5.6-sol", "openai", "medium", "medium"),
        ("qwen/qwen3.8-max", "openrouter", "minimal", "low"),
    ):
        config = _config("api_key", model, provider)
        assert sim.target_effort(config, api) == api_effort
        assert sim.target_effort(config, clinic) == clinic_effort
        record = sim._config_record(config, api, 1)  # pyright: ignore[reportPrivateUsage]
        assert record["target_effort"] == api_effort
        assert record["harness_env"]["TARGET_REASONING"] == api_effort
        assert (
            record["instrument"],
            record["paper_instrument"],
            record["on_paper_instrument"],
            record["off_paper"],
        ) == ("limits_off", "limits_off", True, [])
    # a provider with no setting of record is refused, never guessed
    with pytest.raises(SystemExit, match="TARGET_REASONING setting of record"):
        sim.target_effort(
            _config("api_key", "gpt-5.6-sol", "openai"),
            replace(api, effort_of_record={"anthropic": "none"}),
        )


@pytest.mark.parametrize(
    ("model", "strict"),
    [
        ("meta-llama/llama-4-maverick", True),
        ("anthropic/claude-opus-4.5", True),
        ("openai/gpt-5.2", False),
    ],
)
def test_any_openrouter_model_binds_on_both_sim_drivers(
    clean_env: pytest.MonkeyPatch, model: str, strict: bool
) -> None:
    """Any `<vendor>/<model>` id binds as an OpenRouter target on both drivers.

    No Anthropic-only request option (an Opus id through OpenRouter gets no fast-mode beta), and OpenAI routes
    bind with lax tool schemas.
    """
    for eval_name, recipe in (
        ("api_key", api_cells.build_sim_recipe("stakes_100", "team")),
        ("clinic", clinic_cells.build_sim_recipe("warfarin_inr_plain", "team")),
    ):
        config = _config(eval_name, model, "openrouter")
        _, roles = _bound(config, recipe)
        target = _model(roles, "target")
        assert type(target.api).__name__ == "OpenRouterAPI"
        assert target.api.model_name == model and _api_key_of(target) == TARGET_KEY
        assert cast(Any, target.api).strict_tools is strict
        assert getattr(target.api, "betas", None) is None
        assert sim.target_serving(config, recipe) == "standard"


def test_an_openrouter_role_with_thinking_off_sends_reasoning_disabled(
    clean_env: pytest.MonkeyPatch,
) -> None:
    from _multiagent_pi.roles import role_model

    clean_env.setenv("OPENROUTER_API_KEY", TARGET_KEY)
    model = role_model("openrouter/meta-llama/llama-4-maverick", thinking=False)
    params = cast(Any, model.api).completion_params(model.config, False)
    assert params["extra_body"]["reasoning"] == {"enabled": False}
    assert model.config.reasoning_effort is None
