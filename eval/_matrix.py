"""The paper's runs as launch plans: what `python run.py <env>` plays when no option narrows it.

Each environment declares its paper runs in `eval/<env>/matrix.py`: `PAPER` (the formation experiments) and, for the
personal assistant, `CONTEXT_FILES` (the supplementary rerun with AGENTS.md in context); each mitigation arm's runs
are `RUNS` in its mitigations package (`eval/<env>/mitigations/`). A `Cells` is models x formations x every scenario
of record, with the episodes per cell. `plan` resolves one launch into its episodes: those runs (one arm's, or with
`--mitigation all` every arm's) narrowed by `--model`, `--formation` and `--scenario`, with `--episodes` episodes per
cell (1..N; the first N of a cell the paper holds as a list), or a `--jobs-file`'s episodes.

A launch plays one runs root, or two (`launch_roots`): the personal assistant's paper runs chain the
AGENTS.md-in-context rerun into `context_files`.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import cast

from _jobs import JobSpec, read_jobs_file
from _mitigations import ALL, NONE, Mitigation, lookup, validate
from _paths import EVALS_DIR
from _providers import KEY_ENV_VARS, provider_for

MODELS: tuple[str, ...] = (
    "claude-opus-5",
    "claude-sonnet-5",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "qwen/qwen3.8-max",
)
CLAUDE: tuple[str, ...] = MODELS[:2]
#: A jobs file lists one model's episodes: the model it plays when `--model` names none.
JOBS_FILE_MODEL = "claude-sonnet-5"
#: The offline stand-ins: the simulated harness's and the pi harness's.
FAKES: tuple[str, ...] = ("--fake-model", "--fake-pi")


@dataclass(frozen=True)
class Cells:
    """Models x formations x every scenario of record, and the episodes each (model, formation, scenario) plays.

    A cell plays episodes 1..N (`episodes`, or its `per_model` / `per_formation` count), except the cells in
    `of_record`, which play exactly the paper's episodes on the simulated harness (`clinic/record.py`), and a
    model in `jobs`, whose episodes are that jobs file's rows (a path under `eval/<env>/`); `control` reruns those
    rows without the arm too. The launch lands in `runs_name` unless `--runs-name` says otherwise.
    """

    models: tuple[str, ...]
    formations: tuple[str, ...]
    episodes: int = 0
    per_model: Mapping[str, int] = field(default_factory=dict[str, int])
    per_formation: Mapping[str, int] = field(default_factory=dict[str, int])
    of_record: frozenset[tuple[str, str]] = frozenset()
    jobs: Mapping[str, str] = field(default_factory=dict[str, str])
    control: bool = False
    runs_name: str = "results"


@dataclass(frozen=True)
class Episode:
    """One planned episode."""

    model: str
    scenario: str
    formation: str
    epoch: int
    mitigation: str = NONE


def has_option(extra: Sequence[str], name: str) -> bool:
    """Whether a forwarded option `name` is among `extra` (as `--name value` or `--name=value`)."""
    return any(item == name or item.startswith(f"{name}=") for item in extra)


def option_value(extra: Sequence[str], name: str) -> str | None:
    """The value of a forwarded option `name` (`--name value` or `--name=value`), None when absent."""
    for index, item in enumerate(extra):
        if item == name:
            return extra[index + 1] if index + 1 < len(extra) else None
        if item.startswith(f"{name}="):
            return item.split("=", 1)[1]
    return None


def context_files_on(extra: Sequence[str]) -> bool:
    """`--context-files on` among the options forwarded to the personal assistant's runner."""
    return option_value(extra, "--context-files") == "on"


def is_fake(extra: Sequence[str]) -> bool:
    """An offline stand-in launch (no key, no model call)."""
    return any(flag in extra for flag in FAKES)


def cells_for(env: str, mitigation: str = NONE, context_files: bool = False) -> Cells:
    """The runs a launch narrows: the formation experiments, an arm's runs, or the context-files rerun.

    Raises:
        ValueError: An unknown arm, or `--context-files on` outside the personal assistant.
    """
    if mitigation != NONE:
        return arm_runs(env)[lookup(mitigations_of(env), mitigation, env).name]
    declared = importlib.import_module(f"{env}.matrix")
    if context_files:
        if env != "personal_assistant":
            raise ValueError("--context-files is the personal assistant's")
        return cast(Cells, declared.CONTEXT_FILES)
    return cast(Cells, declared.PAPER)


def mitigations_of(env: str) -> Mapping[str, Mitigation]:
    """The environment's mitigation registry (`<env>/mitigations/`)."""
    return cast(
        Mapping[str, Mitigation],
        importlib.import_module(f"{env}.mitigations").MITIGATIONS,
    )


def arm_runs(env: str) -> Mapping[str, Cells]:
    """The paper's runs of each of the environment's arms, in registry order (`<env>/mitigations/` `RUNS`)."""
    return cast(Mapping[str, Cells], importlib.import_module(f"{env}.mitigations").RUNS)


def canonical_model(env: str, model: str) -> str:
    """The id a model runs and is recorded under (the personal assistant resolves its aliases, `opus` ...)."""
    if env == "personal_assistant":
        from personal_assistant import registry

        return registry.model_id(model)
    return model


def scenario_ids(
    env: str, names: Sequence[str], *, paper_only: bool = True
) -> list[str]:
    """The registry ids of `names` (every scenario of record when empty), in registry order; exits on a typo.

    Raises:
        ValueError: With `paper_only`, a merge-queue scenario outside the paper's (a jobs file's rows may name one).
    """
    wanted = list(names)
    if env == "api_key":
        from api_key import scenarios as api_key

        return [r.id for r in api_key.select(wanted, all_=not wanted)]
    if env == "clinic":
        from clinic import scenarios as clinic

        return [r.id for r in clinic.select(wanted, all_=not wanted)]
    if env == "merge_queue":
        from merge_queue import scenarios as merge_queue

        off = [n for n in wanted if n not in merge_queue.PAPER_SCENARIOS]
        if paper_only and off:
            raise ValueError(
                f"merge_queue scenario(s) {', '.join(off)}: not among the paper's "
                f"({', '.join(merge_queue.PAPER_SCENARIOS)}); eval/merge_queue/run.py plays any scenario"
            )
        return [r.id for r in merge_queue.select(wanted, all_=not wanted)]
    from personal_assistant import registry

    shorts = {registry.scenario(n).short for n in wanted}
    return [s for s in registry.SCENARIOS if not shorts or s in shorts]


def formations_of(env: str, scenario: str, harness: str) -> tuple[str, ...]:
    """The formations `scenario` runs on `harness` (the API key's solo has no pi cell)."""
    if env == "personal_assistant":
        from personal_assistant import registry

        return registry.scenario(scenario).formations
    if env == "api_key":
        from api_key import scenarios as api_key

        return tuple(
            f
            for f in api_key.FORMATIONS
            if harness != "pi" or f not in api_key.SIM_ONLY_FORMATIONS
        )
    if env == "clinic":
        from clinic import scenarios as clinic

        return tuple(clinic.FORMATIONS)
    from merge_queue import scenarios as merge_queue

    return tuple(merge_queue.FORMATIONS)


def epochs_of(
    cells: Cells, model: str, formation: str, scenario: str, epochs: int | None = None
) -> tuple[int, ...]:
    """The episodes one (model, formation, scenario) cell of `cells` plays.

    `epochs` overrides the count: episodes 1..`epochs`, or the first `epochs` of a cell of record.
    """
    if (model, formation) in cells.of_record:
        from clinic import record

        rows = record.select(
            record.load(),
            model=model.rsplit("/", 1)[-1],
            formation=formation,
            mitigation=NONE,
        )
        return tuple(sorted(r.epoch for r in rows if r.scenario == scenario))[:epochs]
    n = epochs or cells.per_model.get(
        model, cells.per_formation.get(formation, cells.episodes)
    )
    return tuple(range(1, n + 1))


def plan(
    env: str,
    *,
    models: Sequence[str] = (),
    formations: Sequence[str] = (),
    scenarios: Sequence[str] = (),
    epochs: int | None = None,
    mitigation: str = NONE,
    jobs_file: Path | None = None,
    harness: str = "sim",
    context_files: bool = False,
) -> list[Episode]:
    """Every episode of one launch, model by model.

    Without a jobs file: the runs `cells_for` names, narrowed; a formation the harness has no cell for is left
    out unless `formations` names it. `mitigation` `all` plays every arm's runs (an episode two arms' runs share,
    the personal assistant's control re-runs, once). With a jobs file: its episodes for each model (default
    `JOBS_FILE_MODEL`).

    Raises:
        ValueError: A formation or arm the environment does not run there, a model an arm's episode lists do
            not cover, or a bad jobs file (the registries exit on an unknown scenario).
    """
    if mitigation == ALL:
        if jobs_file is not None:
            raise ValueError(
                f"a jobs file names each episode's arm; drop --mitigation {ALL}"
            )
        every = dict.fromkeys(
            episode
            for arm in arm_runs(env)
            for episode in plan(
                env,
                models=models,
                formations=formations,
                scenarios=scenarios,
                epochs=epochs,
                mitigation=arm,
                harness=harness,
                context_files=context_files,
            )
        )
        order = list(dict.fromkeys(e.model for e in every))
        return [e for model in order for e in every if e.model == model]
    arms = mitigations_of(env)

    def check(scenario: str, formation: str, arm: str) -> None:
        runs = formations_of(env, scenario, harness)
        if formation not in runs:
            raise ValueError(
                f"{env} runs no {formation} formation on {scenario} (harness {harness}); its formations are "
                f"{', '.join(runs)}"
            )
        validate(arms, arm, env, formations=[formation], harness=harness)

    def cell_list(cells: Cells, model: str) -> list[JobSpec]:
        """A jobs-file-listed cell's rows for `model` (the arm's own, plus its control when `cells.control`)."""
        if model not in cells.jobs:
            raise ValueError(
                f"the paper's {env} {mitigation} episodes are listed for {', '.join(cells.jobs)}, not {model}; "
                "give --jobs-file for another model"
            )
        listed = read_jobs_file(
            EVALS_DIR / env / cells.jobs[model], default_mitigation=mitigation
        )
        control = [JobSpec(j.scenario, j.formation, j.epoch) for j in listed]
        return (control if cells.control else []) + listed

    if jobs_file is not None:
        chosen = list(
            dict.fromkeys(canonical_model(env, m) for m in models or (JOBS_FILE_MODEL,))
        )
        listed = read_jobs_file(jobs_file, default_mitigation=mitigation)
        out: list[Episode] = []
        for model in chosen:
            for job in listed:
                (scenario,) = scenario_ids(env, [job.scenario], paper_only=False)
                check(scenario, job.formation, job.mitigation)
                out.append(
                    Episode(model, scenario, job.formation, job.epoch, job.mitigation)
                )
        return out
    cells = cells_for(env, mitigation, context_files)
    if (
        harness != "sim"
    ):  # the episodes of record are the simulated harness's; the pi harness plays 1..N
        cells = replace(cells, of_record=frozenset())
    chosen = list(
        dict.fromkeys(canonical_model(env, m) for m in models or cells.models)
    )
    wanted_scenarios = scenario_ids(env, scenarios)
    out = []
    for model in chosen:
        if cells.jobs:
            by_cell: dict[tuple[str, str, str], list[int]] = {}
            for job in cell_list(cells, model):
                (scenario,) = scenario_ids(env, [job.scenario])
                if scenario not in wanted_scenarios or (
                    formations and job.formation not in formations
                ):
                    continue
                check(scenario, job.formation, job.mitigation)
                by_cell.setdefault(
                    (scenario, job.formation, job.mitigation), []
                ).append(job.epoch)
            for (scenario, formation, arm), listed in by_cell.items():
                out += [
                    Episode(model, scenario, formation, e, arm) for e in listed[:epochs]
                ]
            continue
        for scenario in wanted_scenarios:
            runs = formations_of(env, scenario, harness)
            for formation in formations or cells.formations:
                if formation not in runs and not formations:
                    continue  # the default matrix leaves out what a harness has no cell for
                check(scenario, formation, mitigation)
                out += [
                    Episode(model, scenario, formation, e, mitigation)
                    for e in epochs_of(cells, model, formation, scenario, epochs)
                ]
    return out


def required_keys(
    env: str, models: Iterable[str], harness: str, extra: Sequence[str] = ()
) -> dict[str, list[str]]:
    """Key variable -> the models that need it.

    Each target needs its provider's key (or the variable `--key-env` names); the API key simulated harness's house
    auditor and the merge queue's requester voicer also run on the Anthropic key.
    """
    target = option_value(extra, "--key-env")
    need: dict[str, list[str]] = {}
    for model in models:
        names: set[str] = set()
        if not has_option(extra, "--api-key"):
            names.add(target or KEY_ENV_VARS[provider_for(model)][0])
        if env == "api_key" and harness == "sim":
            names.add("ANTHROPIC_API_KEY")
        if env == "merge_queue" and "--no-voicer" not in extra:
            names.add(option_value(extra, "--voicer-key-env") or "ANTHROPIC_API_KEY")
        for name in sorted(names):
            need.setdefault(name, []).append(model)
    return need


def missing_keys(
    env: str,
    models: Iterable[str],
    harness: str,
    environ: Mapping[str, str],
    extra: Sequence[str] = (),
) -> str | None:
    """The preflight's refusal naming every key the launch needs and `environ` lacks, or None when all are set."""
    aliases = {names[0]: names for names in KEY_ENV_VARS.values()}
    missing = {
        name: needers
        for name, needers in required_keys(env, models, harness, extra).items()
        if not any(environ.get(a, "").strip() for a in aliases.get(name, (name,)))
    }
    if not missing:
        return None
    return (
        "missing provider key(s): "
        + "; ".join(
            f"{name} (for {', '.join(needers)})" for name, needers in missing.items()
        )
        + ". Set them in the shell or .env, or narrow the launch with --model."
    )


def sim_timeout_s(env: str, episodes: Sequence[Episode]) -> int:
    """The per-episode Modal timeout a simulated-harness launch needs: its longest episode's."""
    from _harness.sim import modal_timeout_needed_s

    cells = sorted({(e.scenario, e.formation, e.mitigation) for e in episodes})
    return modal_timeout_needed_s(env, cells)


def default_runs_name(
    env: str,
    *,
    harness: str,
    mitigation: str = NONE,
    context_files: bool = False,
    jobs_file: Path | None = None,
    fake: bool = False,
) -> str:
    """The runs root a launch lands in: `results`, the runs' own (`cells_for`), or the jobs file's name.

    `pi` for the pi harness of api_key / clinic (one root, one harness), `_fake` for an offline stand-in.
    `mitigation` `all` lands in the root every arm's runs share.
    """
    if jobs_file is not None:
        name = jobs_file.stem
    elif harness == "pi" and env in ("api_key", "clinic"):
        name = "pi"
    elif mitigation == ALL:
        (name,) = {cells.runs_name for cells in arm_runs(env).values()}
    else:
        name = cells_for(env, mitigation, context_files).runs_name
    return name + ("_fake" if fake else "")


@dataclass(frozen=True)
class Root:
    """One runs root of a launch: its name, its episodes and the options they add to the eval runner's."""

    name: str
    episodes: list[Episode]
    options: tuple[str, ...] = ()


#: The runs root the personal assistant's AGENTS.md-in-context rerun gets beside a named root: `<name>` + this.
CONTEXT_FILES_SUFFIX = "_context_files"


def launch_roots(
    env: str,
    *,
    models: Sequence[str] = (),
    formations: Sequence[str] = (),
    scenarios: Sequence[str] = (),
    epochs: int | None = None,
    mitigation: str = NONE,
    jobs_file: Path | None = None,
    harness: str = "sim",
    extra: Sequence[str] = (),
    runs_name: str | None = None,
) -> list[Root]:
    """Every runs root of one launch and its episodes (`plan`), in the order they play.

    One root, except the personal assistant's paper runs: its AGENTS.md-in-context rerun (`matrix.CONTEXT_FILES`,
    the paper's supplementary formation rows) follows in `context_files` (`<name>_context_files` beside a root
    named otherwise), narrowed like the first root to the models and formations it ran. `--context-files on`
    plays that rerun alone and `--context-files off` the paper runs alone.

    Raises:
        ValueError: As `plan`.
    """
    context_files = context_files_on(extra)
    fake = is_fake(extra)
    episodes = plan(
        env,
        models=models,
        formations=formations,
        scenarios=scenarios,
        epochs=epochs,
        mitigation=mitigation,
        jobs_file=jobs_file,
        harness=harness,
        context_files=context_files,
    )
    default = default_runs_name(
        env,
        harness=harness,
        mitigation=mitigation,
        context_files=context_files,
        jobs_file=jobs_file,
        fake=fake,
    )
    name = runs_name or default
    roots = [Root(name, episodes)]
    if not (
        env == "personal_assistant"
        and mitigation == NONE
        and jobs_file is None
        and option_value(extra, "--context-files") is None
    ):
        return roots
    rerun = cells_for(env, context_files=True)
    wanted_models = [canonical_model(env, m) for m in models] or list(rerun.models)
    chosen = [m for m in dict.fromkeys(wanted_models) if m in rerun.models]
    chained = [f for f in formations or rerun.formations if f in rerun.formations]
    if not chosen or not chained:
        return roots
    more = plan(
        env,
        models=chosen,
        formations=chained,
        scenarios=scenarios,
        epochs=epochs,
        harness=harness,
        context_files=True,
    )
    second = (
        default_runs_name(env, harness=harness, context_files=True, fake=fake)
        if name == default
        else name + CONTEXT_FILES_SUFFIX
    )
    return [*roots, Root(second, more, ("--context-files", "on"))]


def nothing_to_run(
    env: str,
    *,
    mitigation: str = NONE,
    jobs_file: Path | None = None,
    extra: Sequence[str] = (),
) -> str:
    """Why a launch planned no episode: the listed episodes its narrowing left out, or the narrowing itself."""
    if jobs_file is not None:
        return f"the jobs file {jobs_file} lists no episode"
    arms = list(arm_runs(env)) if mitigation == ALL else [mitigation]
    listed = sorted(
        {
            f"eval/{env}/{path}"
            for arm in arms
            if arm != NONE
            for path in cells_for(env, arm).jobs.values()
        }
    )
    if listed:
        return (
            f"the paper's {env} {mitigation} runs play only the episodes listed in {', '.join(listed)}, and "
            "none matches --model / --formation / --scenario / --episodes"
        )
    context = " (AGENTS.md in context)" if context_files_on(extra) else ""
    return f"no episode of the paper's {env} runs{context} matches --model / --formation / --scenario / --episodes"


def summary(
    env: str,
    episodes: Sequence[Episode],
    root: str,
    note: str = "",
) -> str:
    """The launch as a table: episodes per model and formation (an arm's as `formation/arm`), and the totals."""

    def column(e: Episode) -> str:
        return e.formation if e.mitigation == NONE else f"{e.formation}/{e.mitigation}"

    columns = list(dict.fromkeys(column(e) for e in episodes))
    models = list(dict.fromkeys(e.model for e in episodes))
    counts: dict[tuple[str, str], int] = {}
    for e in episodes:
        counts[(e.model, column(e))] = counts.get((e.model, column(e)), 0) + 1
    width = max([len(m) for m in models] + [5])
    cw = max([len(c) for c in columns] + [12])
    lines = [
        f"{env}{note}: {len(episodes)} episode(s), {len({e.scenario for e in episodes})} scenario(s) -> {root}",
        f"  {'model':{width}} "
        + " ".join(f"{c:>{cw}}" for c in columns)
        + f" {'episodes':>9}",
    ]
    for m in models:
        row = [counts.get((m, c), 0) for c in columns]
        lines.append(
            f"  {m:{width}} " + " ".join(f"{n:>{cw}}" for n in row) + f" {sum(row):>9}"
        )
    return "\n".join(lines)
