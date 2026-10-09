"""The pi harness of api_key and clinic sends every seat an explicit pi thinking level, and records it.

Without `--thinking` pi falls back to its own default (`medium`), whatever the provider; the lockstep runner passes
the provider's level of `_providers.THINKING_BY_PROVIDER` instead (or `--thinking`), as personal_assistant and
merge_queue do. The simulated harness plays the paper's reasoning setting and takes no `--thinking`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from _providers import THINKING_BY_PROVIDER
from api_key import run as api_key_run
from clinic import run as clinic_run

from _harness import readout, runner


def _config(argv: list[str]) -> runner.RunConfig:
    args = api_key_run.parse_args(["--scenario", "stakes_100", *argv])
    return runner.config_from_args(
        args,
        eval_name="api_key",
        scenario="stakes_100",
        formation="team",
        default_runs_root=Path("/tmp/unused"),
    )


class _Bridge:
    def seat_system_prompt(self, seat: str) -> str | None:
        return None


@pytest.mark.parametrize(
    ("model", "provider"),
    [
        ("claude-sonnet-5", "anthropic"),
        ("gpt-5.6-sol", "openai"),
        ("meta-llama/llama-4-maverick", "openrouter"),
    ],
)
def test_every_pi_seat_gets_the_providers_thinking_level(
    model: str, provider: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVAL_PI_CMD", "pi")
    config = _config(["--harness", "pi", "--model", model])
    assert config.thinking == THINKING_BY_PROVIDER[provider]
    argv = runner._seat_argv(  # pyright: ignore[reportPrivateUsage]
        config, cast(Any, _Bridge()), "s1", Path("/tmp/seat")
    )
    assert argv[argv.index("--thinking") + 1] == THINKING_BY_PROVIDER[provider]
    chosen = _config(["--harness", "pi", "--model", model, "--thinking", "high"])
    assert chosen.thinking == "high"


def test_the_simulated_harness_takes_no_thinking_level(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _config([]).thinking is None
    for parse, which in (
        (api_key_run.parse_args, ["--scenario", "stakes_100"]),
        (clinic_run.parse_args, ["--board", "warfarin_inr_split"]),
    ):
        with pytest.raises(SystemExit):
            parse([*which, "--thinking", "low"])
        assert "--thinking is the pi harness's" in capsys.readouterr().err


def test_a_pi_pool_never_mixes_thinking_levels(tmp_path: Path) -> None:
    rows: list[dict[str, Any]] = [
        {"formation": "team", "model": "m", "mitigation": "none", "thinking": level}
        for level in ("off", "medium")
    ]
    with pytest.raises(SystemExit, match="pi thinking"):
        readout.single_instrument(rows, tmp_path)
    readout.single_instrument(rows[:1] * 2, tmp_path)
