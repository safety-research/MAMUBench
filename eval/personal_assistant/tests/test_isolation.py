"""The seat's working directory, which pi prints in every system prompt, and runs without `.git`.

pi 0.77.0 ends each seat's system prompt with `Current working directory: <process cwd>` (and, under
`--context-files on`, names the loaded AGENTS.md by path). The paper's seats ran the environment's
root-host path (`root_host=True`), so they read `/home/pa-<name>/dinner`. Pinned here:

- `--isolation none` (any host): the shim root is opaque and fixed-length, so the cwd carries nothing
  about the episode; the sidecar records each seat's actual cwd as `host_seat_cwd` and the readouts flag it;
- `auto` selects the root-host path inside a Modal container and `none` elsewhere; `root` fails closed on a
  host that cannot run it and runs one episode per invocation;
- the root-host path is the environment's call (`root_host=True` + the research boundary roots), its bare
  `pi` resolves to the pinned (or fake) pi, and its seat launch matches pi's own probe prompts
  (`tests/fixtures/probe_prompts/`); `test_root_host_episode_sees_the_papers_cwd` runs it end to end where
  that is possible (Linux, root, `MAMUBENCH_ROOT_HOST_TESTS=1`: it creates OS users);
- a copy of the release without `.git` runs a fake-pi episode (revision `unknown`).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from personal_assistant import check, outcomes, registry, report, run
from personal_assistant._paths import REPO_ROOT
from personal_assistant.environment import food_run, trip_run
from personal_assistant.harness import local_runtime
from personal_assistant.harness.local_runtime import FAKE_PI, SeatLaunch

#: `mkdtemp(prefix=SEAT_ROOT_PREFIX)`: the prefix plus 8 random characters.
OPAQUE_ROOT = re.compile(r"^pa-[a-z0-9_]{8}$")


def _ledger(run_dir: Path) -> list[dict[str, Any]]:
    lines = (run_dir / "world" / "ledger.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines if line]


def _session_cwd(seat_dir: Path) -> str:
    (session,) = sorted((seat_dir / "sessions").glob("*.jsonl"))
    return str(json.loads(session.read_text().splitlines()[0])["cwd"])


def test_local_seat_cwd_is_opaque_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seat_root = tmp_path / "seat_root"
    monkeypatch.setenv("EVAL_SEAT_ROOT", str(seat_root))
    runs = tmp_path / "runs"
    argv = ["--scenario", "kestrel_quiz_booth", "--formation", "team"]
    assert (
        run.main(
            [*argv, "--mitigation", "guard", "--fake-pi", "--runs-root", str(runs)]
        )
        == 0
    )
    wave = runs / "kestrel_quiz_booth__claude-sonnet-5__mit-guard"
    assert json.loads((wave / "wave_config.json").read_text())["isolation"] == "none"
    cell = "conf_kestrel_quiz_booth_mesh__m10"
    recorded: dict[str, str] = json.loads(
        (wave / "worlds" / f"{cell}__e1.json").read_text()
    )["host_seat_cwd"]
    run_dir = wave / "runs" / f"{cell}__claude-sonnet-5__e1"
    assert sorted(recorded) == ["c1", "c2", "c3", "c4"]
    roots: set[str] = set()
    for seat, cwd in recorded.items():
        # the sidecar holds exactly what pi printed (the session header records the process cwd)
        assert cwd == _session_cwd(run_dir / "agents" / seat)
        root, home, user, leaf = Path(cwd).relative_to(seat_root.resolve()).parts
        assert OPAQUE_ROOT.match(root), root
        assert (home, leaf) == ("home", "dinner") and user.startswith("pa-")
        # nothing about the episode reaches the prompt: not the scenario, formation, arm or model
        for leak in "kestrel quiz mesh m10 guard claude sonnet eval".split():
            assert leak not in root, (leak, cwd)
        roots.add(root)
    assert len(roots) == 1
    started = next(r for r in _ledger(run_dir) if r["kind"] == "runtime_started")
    assert started["isolation"]["seat_cwd"] == "host_temp_root"
    # the readouts can tell
    (row,) = outcomes.classify_wave(wave)
    assert row.host_seat_cwd is True
    assert report.build(runs)["host_seat_cwd_episodes"] == 1
    assert report.host_seat_cwd_note(0, 1) is None
    check.main([str(runs), "--jobs", "1"])
    out = capsys.readouterr().out
    assert "NOTE: 1 of 1 episode(s) ran with --isolation none" in out
    assert "/home/pa-<name>/dinner" in out


def test_choosing_the_isolation_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODAL_IS_REMOTE", raising=False)
    for requested, mode in (("auto", "none"), ("none", "none"), ("docker", "docker")):
        assert local_runtime.resolve_isolation(requested) == mode
    with pytest.raises(ValueError, match="isolation must be one of"):
        local_runtime.resolve_isolation("container")
    monkeypatch.setenv("MODAL_IS_REMOTE", "1")
    monkeypatch.setattr(local_runtime, "root_host_problem", lambda: None)
    assert local_runtime.resolve_isolation("auto") == "root"
    monkeypatch.setattr(local_runtime, "root_host_problem", lambda: "it needs Linux")
    for requested in ("auto", "root"):
        with pytest.raises(SystemExit, match="root-host path .* it needs Linux"):
            local_runtime.resolve_isolation(requested)
    # `--print-info` only prints the plan: no host probe
    assert local_runtime.resolve_isolation("auto", check=False) == "root"
    monkeypatch.undo()
    # what the host probe names
    monkeypatch.setattr(local_runtime.sys, "platform", "darwin")
    assert "Linux" in (local_runtime.root_host_problem() or "")
    monkeypatch.setattr(local_runtime.sys, "platform", "linux")
    monkeypatch.setattr(local_runtime.os, "geteuid", lambda: 1000)
    assert "root" in (local_runtime.root_host_problem() or "")
    monkeypatch.setattr(local_runtime.os, "geteuid", lambda: 0)
    for missing, problem in (("setpriv", "missing host tools: setpriv"), ("", None)):

        def which(tool: str, missing: str = missing) -> str | None:
            return None if tool == missing else f"/usr/bin/{tool}"

        monkeypatch.setattr(local_runtime.shutil, "which", which)
        assert local_runtime.root_host_problem() == problem


def test_root_runs_one_episode_per_invocation_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv = ["--scenario", "kestrel_quiz_booth", "--isolation", "root", "--fake-pi"]
    monkeypatch.setattr(local_runtime, "root_host_problem", lambda: "it needs Linux")
    with pytest.raises(SystemExit, match="it needs Linux"):
        run.main(argv)
    monkeypatch.setattr(local_runtime, "root_host_problem", lambda: None)
    both = [*argv, "--formation", "coordinator", "team"]
    with pytest.raises(SystemExit, match="one episode per single-use container"):
        run.main([*both, "--runs-root", str(tmp_path)])
    assert run.main([*both, "--print-info"]) == 0  # the plan itself is printable


def test_root_isolation_calls_the_research_root_host_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`root` is the research call: `root_host=True`, the code and the runs root as boundary roots."""
    for scenario in ("kestrel_quiz_booth", "twin_by_the_bathroom"):
        _root_host_call(tmp_path, monkeypatch, scenario)


def _root_host_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    from personal_assistant.environment.food_runtime import FoodRuntime
    from personal_assistant.environment.trip_runtime import TripRuntime
    from personal_assistant.scenarios import register_trip_specs

    seen: dict[str, Any] = {}

    def fake_episode(topology: str, epoch: int, **kwargs: Any) -> str:
        seen.update(kwargs, topology=topology, epoch=epoch)
        return "ok"

    row = registry.scenario(scenario)
    monkeypatch.setattr(
        food_run if row.substrate == "food" else trip_run, "run_episode", fake_episode
    )
    wave = tmp_path / "runs" / f"{scenario}__claude-sonnet-5"
    config = run.RunConfig(
        model="claude-sonnet-5",
        provider="anthropic",
        thinking="off",
        isolation="root",
        fake_pi=True,
        turn_timeout=1.0,
        hard_cap=2700.0,
        revision="r",
        pi_version="fake",
    )
    assert run.run_job(run.Job(row, "team", 3, wave), config, "k") == "ok"
    assert seen["root_host"] is True and seen["topology"] == "mesh"
    assert seen["boundary_roots"] == (REPO_ROOT, wave.parent, wave)
    seen.clear()
    none = replace(config, isolation="none")
    assert run.run_job(run.Job(row, "team", 3, wave), none, "k") == "ok"
    assert seen["root_host"] is False and "boundary_roots" not in seen
    # the root-host runtimes add no sidecar field: their sidecars stay byte-identical to the research code's
    register_trip_specs()
    common: dict[str, Any] = dict(
        model="m",
        provider="anthropic",
        api_key="k",
        turn_timeout=1,
        thinking="off",
        root_host=True,
        protected_roots=(),
    )
    runtime = (
        FoodRuntime(row.cell("team"), 1, Path("/nonexistent"), **common)
        if row.substrate == "food"
        else TripRuntime("mesh", Path("/nonexistent"), scenario=scenario, **common)
    )
    assert runtime.sidecar_notes == {}


def test_seat_exec_runs_a_python_pi_under_the_interpreter(tmp_path: Path) -> None:
    """A 0644 fake_pi.py (no exec bit) launches through `sys.executable`; any other pi is exec'd as given."""
    fake = tmp_path / "fake_pi.py"
    shutil.copyfile(FAKE_PI, fake)
    fake.chmod(0o644)
    real = tmp_path / "pi"
    real.write_text('#!/bin/sh\necho "argv0=$0 $*"\n')
    real.chmod(0o755)
    out = {}
    for name, pi in (("fake", fake), ("real", real)):
        proc = subprocess.run(
            [
                sys.executable,
                str(local_runtime.SEAT_EXEC),
                str(tmp_path),
                str(tmp_path),
                str(pi),
            ]
            + ["pi", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        out[name] = proc.stdout.strip()
    assert out == {"fake": "0.77.0", "real": f"argv0={real} --version"}


def test_root_seat_pi_resolves_to_the_pinned_or_fake_pi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install = local_runtime._install_root_seat_pi  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setattr(local_runtime, "_ROOT_SEAT_BIN", [])
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "pa-ana.json").write_text("[]")
    bin_dir = install(SeatLaunch(FAKE_PI, fake_script_dir=scripts))
    try:
        assert os.environ["PATH"].split(os.pathsep)[0] == str(bin_dir)
        assert bin_dir.stat().st_mode & 0o777 == 0o755
        wrapper = (bin_dir / "pi").read_text()
        assert wrapper.startswith("#!/bin/sh")
        assert 'FAKE_PI_SEAT="$(id -un)"' in wrapper
        assert f'FAKE_PI_SCRIPT_DIR="{bin_dir / "scripts"}"' in wrapper
        assert (bin_dir / "fake_pi.py").read_bytes() == FAKE_PI.read_bytes()
        assert (bin_dir / "scripts" / "pa-ana.json").stat().st_mode & 0o777 == 0o644
        assert install(SeatLaunch(Path("/elsewhere/pi"))) == bin_dir  # once per process
    finally:
        shutil.rmtree(bin_dir)
    monkeypatch.setattr(local_runtime, "_ROOT_SEAT_BIN", [])
    pinned = tmp_path / "pinned-pi"
    pinned.write_text("#!/bin/sh\n")
    bin_dir = install(SeatLaunch(pinned))
    try:
        assert (bin_dir / "pi").resolve() == pinned.resolve()
    finally:
        shutil.rmtree(bin_dir)


# ── what the root-host path hands pi, against pi's own system prompts ────────────────────────────

PROBES = Path(__file__).resolve().parent / "fixtures" / "probe_prompts"
#: probe -> (substrate, cell or trip topology, trip spec, seat): pi 0.77.0's own system prompts for these seats.
PROBE_SEATS: dict[str, tuple[str, str, str, str]] = {
    "food_team": ("food", "conf_reg_food_silent_side_deadline_mesh", "", "d2"),
    "food_coordinator": ("food", "conf_reg_food_silent_side_deadline_steward", "", "S"),
    "food_team_silent": (
        "food",
        "conf_reg_food_silent_side_deadline_mesh_nc",
        "",
        "d2",
    ),
    "trip_team": ("trip", "mesh", "group__double_share_snapback", "t1"),
}
BLOCK = re.compile(
    r'<project_instructions path="([^"]*)">\n([\s\S]*?)\n</project_instructions>'
)


def test_the_probe_prompts_are_the_root_host_launch_plus_our_agents_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline (no root needed): pi's own prompts for these seats, context files off and on.

    `RootHostShim` runs `setpriv ... env -C <cwd> pi ...`: pi's prompt ends `Current working directory:
    <cwd>`; with context files on it adds exactly one `<project_context>` block, `<cwd>/AGENTS.md` with the
    AGENTS.md this eval stages byte for byte (the block the preflight then requires the seat to attest).
    The unprivileged shim's cwd is a host path instead (the disclosed difference).
    """
    for name in sorted(PROBE_SEATS):
        _probe_seat(tmp_path / name, monkeypatch, name)


def _probe_seat(root: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    from personal_assistant.environment import live_docker, pi_runtime
    from personal_assistant.environment.food_runtime import ConfidentialFoodBridge
    from personal_assistant.environment.trip_runtime import TripBridge
    from personal_assistant.scenarios import register_trip_specs

    register_trip_specs()
    substrate, cell, spec, seat = PROBE_SEATS[name]
    bridge: Any = (
        ConfidentialFoodBridge(cell, 1, root / "world")
        if substrate == "food"
        else TripBridge(cell, root / "world" / "ledger.jsonl", spec)
    )
    launched: dict[str, Any] = {}

    def spawn_agent(argv: list[str], **kwargs: Any) -> str:
        launched.update(argv=argv, **kwargs)
        return "handle"

    monkeypatch.setattr(pi_runtime.pi_rpc, "spawn_agent", spawn_agent)
    prompts: dict[bool, str] = {}
    cwds: set[str] = set()
    for context_files in (False, True):
        pi_runtime._spawn_seat(  # pyright: ignore[reportPrivateUsage]
            live_docker.RootHostShim(root / "run"),
            bridge,
            seat,
            provider="anthropic",
            model="claude-opus-5",
            thinking="off",
            server_url="http://127.0.0.1:1",
            seat_token="token",
            seat_dir=root / "seat",
            run_dir=root / "run",
            context_files=context_files,
        )
        argv: list[str] = launched["argv"]
        cwd = argv[argv.index("-C") + 1]
        assert argv[argv.index("-C") + 2] == "pi"
        assert ("--no-context-files" in argv) is not context_files
        suffix = "on" if context_files else "off"
        prompt = (PROBES / f"{name}__context_files_{suffix}.txt").read_text()
        assert (
            prompt.rstrip("\n").splitlines()[-1] == f"Current working directory: {cwd}"
        )
        prompts[context_files] = prompt
        cwds.add(cwd)
    (cwd,) = cwds
    on, off = prompts[True], prompts[False]
    ((path, body),) = BLOCK.findall(on)
    assert (
        path
        == f"{cwd}/AGENTS.md"
        == pi_runtime.expected_project_context(bridge, seat)["path"]
    )
    assert body == bridge.workspace_files(seat)["AGENTS.md"]
    # pi inserts "\n<project_context>...</project_context>\n\n" after the docs paragraph
    start = on.index("\n<project_context>")
    end = on.index("</project_context>") + len("</project_context>\n\n")
    assert on[:start] + on[end:] == off and "<project_context>" not in off
    shim = local_runtime.LocalHostShim(root / "run", SeatLaunch(FAKE_PI))
    shim.start()
    try:
        assert shim.host_cwd(cwd) != cwd and shim.host_cwd(cwd).endswith(cwd)
    finally:
        shim.stop()


@pytest.mark.skipif(
    not (
        os.environ.get("MAMUBENCH_ROOT_HOST_TESTS") == "1"
        and local_runtime.root_host_problem() is None
    ),
    reason="needs Linux as root with useradd/setpriv/pkill and MAMUBENCH_ROOT_HOST_TESTS=1 "
    "(creates the seats' OS users; run it in a throwaway container)",
)
def test_root_host_episode_sees_the_papers_cwd(tmp_path: Path) -> None:
    """A fake-pi episode on the root-host path: every seat's cwd is the paper's `/home/pa-<name>/dinner`.

    Run with `--context-files on`, so the preflight also required each seat's attested
    `<project_instructions path=...>` to be exactly `/home/pa-<name>/dinner/AGENTS.md`.
    """
    runs = tmp_path / "runs"
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(run.__file__)),
            "--scenario",
            "reg_food_silent_side_deadline",
            "--formation",
            "team",
            "--isolation",
            "root",
            "--context-files",
            "on",
            "--fake-pi",
            "--runs-root",
            str(runs),
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    wave = runs / "reg_food_silent_side_deadline__claude-sonnet-5__ctx-on"
    assert json.loads((wave / "wave_config.json").read_text())["isolation"] == "root"
    (sidecar_path,) = (wave / "worlds").glob("*.json")
    sidecar = json.loads(sidecar_path.read_text())
    assert "host_seat_cwd" not in sidecar and sidecar["context_files"] is True
    (run_dir,) = (wave / "runs").iterdir()
    started = next(r for r in _ledger(run_dir) if r["kind"] == "runtime_started")
    assert started["isolation"]["episode_boundary"] == "modal_container"
    assert started["isolation"]["seat_boundary"] == "linux_dac_per_user"
    for seat, argv in sidecar["pi_argv"].items():
        cwd = argv[argv.index("-C") + 1]
        assert re.fullmatch(r"/home/pa-[a-z]+/dinner", cwd), cwd
        assert argv[argv.index("-C") + 2] == "pi"
        assert _session_cwd(run_dir / "agents" / seat) == cwd


def test_a_copy_without_git_runs_a_fake_pi_episode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fake-pi run from a `git archive` copy: the revision is `EVAL_GIT_SHA`, else `unknown`.

    Every file of the copy is 0644, as an extraction that drops file modes leaves it (fake_pi.py loses its exec bit).
    """
    monkeypatch.setenv("EVAL_GIT_SHA", "archive0000")
    assert food_run.git_sha() == trip_run.git_sha() == "archive0000"
    monkeypatch.delenv("EVAL_GIT_SHA")

    def no_git(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git")

    with monkeypatch.context() as patched:
        patched.setattr(food_run.subprocess, "run", no_git)
        assert food_run.git_sha() == trip_run.git_sha() == "unknown"
    copy = tmp_path / "release"
    ignore = shutil.ignore_patterns(
        ".git",
        ".venv",
        "runs",
        "readouts",
        "results",
        "__pycache__",
        "tests",
        "api_key",
        "clinic",
        "merge_queue",
    )
    shutil.copytree(REPO_ROOT / "eval", copy / "eval", ignore=ignore)
    for name in ("pyproject.toml", "run.py"):
        shutil.copy2(REPO_ROOT / name, copy / name)
    for path in copy.rglob("*"):
        if path.is_file():
            path.chmod(0o644)
    assert (
        copy / "eval/personal_assistant/harness/fake_pi.py"
    ).stat().st_mode & 0o777 == 0o644
    probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=copy, capture_output=True)
    if probe.returncode == 0:
        pytest.skip("the temp dir sits inside a git checkout")
    for module in (food_run, trip_run):
        monkeypatch.setattr(module, "REPO_ROOT", copy)
        assert module.git_sha() == "unknown"
    env = {k: v for k, v in os.environ.items() if k != "EVAL_GIT_SHA"}
    runs = tmp_path / "runs"
    proc = subprocess.run(
        [
            sys.executable,
            "eval/personal_assistant/run.py",
            "--scenario",
            "kestrel_quiz_booth",
            "--formation",
            "coordinator",
            "--fake-pi",
            "--runs-root",
            str(runs),
        ],
        cwd=copy,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-3000:]
    assert "revision=unknown" in proc.stdout
    wave = runs / "kestrel_quiz_booth__claude-sonnet-5"
    (sidecar,) = (wave / "worlds").glob("*.json")
    assert json.loads(sidecar.read_text())["git_sha"] == "unknown"
    assert json.loads((wave / "wave_config.json").read_text())["git_sha"] == "unknown"
