"""`--context-files on`: the paper's supplementary AGENTS.md-in-context rerun.

Default off is the paper's main instrument: every pi seat runs with `--no-context-files`, so the AGENTS.md the
runtime writes into each seat's cwd never reaches the model. On omits exactly that flag; pi loads the file as
one `<project_context>` block (pi's own probe prompts: `test_isolation.py`), the hub extension attests it (path
+ sha256), and the preflight fails closed unless each seat carries exactly its staged AGENTS.md. Pinned here:
the argv, the preflight, an offline episode, resume and readout separation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from _harness import pi_rpc

from personal_assistant import check, outcomes, report, run
from personal_assistant.environment import food_run, pi_runtime
from personal_assistant.tests.conftest import run_fake


def test_on_is_off_minus_the_one_flag() -> None:
    def argv(**kwargs: Any) -> list[str]:
        return pi_rpc.rpc_argv(
            provider="anthropic", model="m", session_dir=Path("/s"), **kwargs
        )

    off, on = argv(), argv(context_files=True)
    assert "--no-context-files" in off and argv(context_files=False) == off
    assert [a for a in off if a != "--no-context-files"] == on
    assert pi_runtime.context_files_flag(" ON ") is True
    assert pi_runtime.context_files_flag("off") is False
    with pytest.raises(ValueError):
        pi_runtime.context_files_flag("yes")
    assert run.parse_args(["--all"]).context_files == "off"


class _Server:
    def __init__(self, attestations: dict[str, dict[str, object]]) -> None:
        self._attestations = attestations

    def tool_attestations(self) -> dict[str, dict[str, object]]:
        return self._attestations


class _Bridge:
    ids = ("s1",)
    usernames = {"s1": "pa-x"}

    def tools_manifest(self) -> list[dict[str, Any]]:
        return [{"name": "dd_menu"}]

    def workspace_files(self, seat: str) -> dict[str, str]:
        return {"AGENTS.md": "# runbook\n"}

    def seat_cwd(self, seat: str) -> str:
        return "/home/pa-x/dinner"


def _preflight(blocks: object | None, *, on: bool, map_path: Any = None) -> int:
    attestation: dict[str, object] = {
        "active_tools": ["dd_menu"],
        "all_tools": ["dd_menu"],
        "thinking": "off",
    }
    if blocks is not None:
        attestation["project_context"] = blocks
    return pi_runtime._preflight_tool_surfaces(  # pyright: ignore[reportPrivateUsage]
        _Server({"s1": attestation}),  # type: ignore[arg-type]
        _Bridge(),  # type: ignore[arg-type]
        timeout=0.1,
        expected_context_files=on,
        map_path=map_path,
    )


def test_preflight_requires_exactly_the_staged_agents_md() -> None:
    staged = {
        "path": "/home/pa-x/dinner/AGENTS.md",
        "sha256": hashlib.sha256(b"# runbook\n").hexdigest(),
    }
    assert _preflight([staged], on=True) == 1
    assert _preflight([], on=False) == 1
    assert (
        _preflight(None, on=False) == 1
    )  # an older extension attests nothing: off only
    for bad in (None, [], [staged, staged], [{**staged, "sha256": "0" * 64}]):
        with pytest.raises(RuntimeError, match="context-files preflight failed"):
            _preflight(bad, on=True)
    with pytest.raises(RuntimeError, match="context_files=off"):
        _preflight([staged], on=False)
    # the unprivileged local runtime maps the in-fiction cwd under the run dir
    mapped = {**staged, "path": "/runs/x/home/pa-x/dinner/AGENTS.md"}

    def under_run_dir(path: str) -> Path:
        return Path("/runs/x" + path)

    assert _preflight([mapped], on=True, map_path=under_run_dir) == 1


def test_an_on_episode_launches_without_the_flag_and_records_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs = tmp_path / "runs"
    kestrel = "kestrel_quiz_booth"
    on = ("--context-files", "on")
    assert (
        run_fake(
            runs,
            scenario=kestrel,
            formations=("coordinator", "team"),
            scripts=None,
            extra=on,
        )
        == 0
    )
    wave = runs / run.wave_name(kestrel, "claude-sonnet-5", context_files=True)
    assert wave.name == f"{kestrel}__claude-sonnet-5__ctx-on"
    assert json.loads((wave / "wave_config.json").read_text())["context_files"] is True
    record = outcomes.load_sidecar(wave / "worlds" / f"conf_{kestrel}_mesh__e1.json")
    assert record["context_files"] is True
    assert set(record["pi_argv"]) == {"c1", "c2", "c3", "c4"}
    for argv in record["pi_argv"].values():
        assert "--no-context-files" not in argv and "--no-skills" in argv
    ledger = (
        wave
        / "runs"
        / f"conf_{kestrel}_mesh__claude-sonnet-5__e1"
        / "world"
        / "ledger.jsonl"
    )
    started = next(
        row
        for row in map(json.loads, ledger.read_text().splitlines())
        if row["kind"] == "runtime_started"
    )
    assert started["context_files"] is True
    assert started["isolation"]["tool_surface_preflight"] == "passed"
    assert all(r.context_files for r in outcomes.classify_wave(wave))
    # an off episode in the same runs root: the readout refuses to pool the two launches
    assert run_fake(runs, scenario=kestrel, formations=("team",), scripts=None) == 0
    with pytest.raises(SystemExit, match="mixes --context-files on and off"):
        report.collect(runs)
    # read alone, the on-run is checked against the context-files reference by default
    capsys.readouterr()
    check.main([str(wave)])
    assert capsys.readouterr().out.startswith("instrument: context_files")


def test_resume_refuses_a_sidecar_of_the_other_launch(tmp_path: Path) -> None:
    validate = food_run._validate_completion_sidecar  # pyright: ignore[reportPrivateUsage]
    base = {
        "cell": "c",
        "epoch": 1,
        "model": "m",
        "thinking": "off",
        "git_sha": "g",
        "ending": "committed",
    }
    common: dict[str, Any] = {
        "cell": "c",
        "epoch": 1,
        "model": "m",
        "thinking": "off",
        "revision": "g",
    }
    off, on, arm = tmp_path / "off.json", tmp_path / "on.json", tmp_path / "arm.json"
    off.write_text(json.dumps(base))
    on.write_text(json.dumps({**base, "context_files": True}))
    arm.write_text(json.dumps({**base, "mitigation": "guard"}))
    validate(off, **common)
    validate(on, **common, context_files=True)
    validate(arm, **common, mitigation="guard")
    # a control never resumes an arm's or the other launch's sidecar, nor the reverse
    refused: tuple[tuple[Path, dict[str, Any], str], ...] = (
        (on, {}, "context_files"),
        (off, {"context_files": True}, "context_files"),
        (arm, {}, "mitigation"),
    )
    for path, kwargs, field in refused:
        with pytest.raises(RuntimeError, match=field):
            validate(path, **common, **kwargs)
