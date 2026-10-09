"""Every environment's stats in one table: each environment's own report.py on the roots its default command writes.

    python analysis/stats.py                        # eval/<env>/runs/results (+ the personal assistant's
                                                    # context_files); a missing root is skipped
    python analysis/stats.py --roots clinic=DIR     # another root for an env (repeatable; a second root named
                                                    # like an earlier one is labelled NAME-2)
    python analysis/stats.py --plot                 # also stats.png (matplotlib: `uv sync --group plot`)

Each root goes through `eval/<env>/report.py ROOT --out-dir <out>/<env>/<root>` (the readout README.md's "Running"
points to: episodes, per-scenario tables, scores and formation contrasts). This script computes nothing itself: it
concatenates what the reports wrote into `<out>/stats.csv` (every root's scores.csv) and
`<out>/contrasts.csv` (every contrasts.csv), each with a `root` column after `env`, and writes `<out>/stats.md`,
the headline per env x model x formation (and mitigation arm) with its 95% interval: each report's pooled row over
every scenario it covers (`POOLED (k scenarios...)`), or its per-scenario rows where it pools none.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
#: the runs roots `python run.py <env>` writes, in the order the reports read them
DEFAULT_ROOTS = {
    "api_key": ["results"],
    "clinic": ["results"],
    "personal_assistant": ["results", "context_files"],
    "merge_queue": ["results"],
}
FORMATIONS = ["solo", "coordinator", "team_silent", "team"]
Row = dict[str, str]
#: a CSV's header and rows
Table = tuple[list[str], list[Row]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--roots", action="append", default=[], metavar="ENV=DIR")
    parser.add_argument("--out-dir", type=Path, default=REPO / "analysis" / "out")
    parser.add_argument("--plot", action="store_true", help="also stats.png")
    return parser.parse_args(argv)


def roots_by_env(overrides: list[str]) -> dict[str, list[Path]]:
    roots = {
        env: [REPO / "eval" / env / "runs" / name for name in names]
        for env, names in DEFAULT_ROOTS.items()
    }
    given: dict[str, list[Path]] = {}
    for item in overrides:
        env, sep, path = item.partition("=")
        if not sep or env not in DEFAULT_ROOTS:
            sys.exit(
                f"--roots {item}: expected ENV=DIR, ENV one of {list(DEFAULT_ROOTS)}"
            )
        given.setdefault(env, []).append(Path(path).resolve())
    return roots | given


def show(path: Path) -> str:
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def read_csv(path: Path) -> Table:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def missing_note(env: str, root: Path) -> str:
    """The skip note, naming the other roots beside a default one (an offline stand-in run writes `results_fake`)."""
    runs = REPO / "eval" / env / "runs"
    others = []
    if root.parent == runs and runs.is_dir():
        others = sorted(
            p.name
            for p in runs.iterdir()
            if p.is_dir() and p != root and not p.name.startswith(".")
        )
    note = f"{env}: no runs at {show(root)}; skipped"
    if others:
        note += (
            f" ({show(runs)} holds {', '.join(others)}: --roots {env}=DIR reads one)"
        )
    return note


def report(env: str, root: Path, label: str, out: Path) -> tuple[Table, Table] | None:
    """Run the env's report.py on one root; its (scores, contrasts) tables, each with `root` = label after `env`."""
    if not root.is_dir() or not any(root.iterdir()):
        print(missing_note(env, root))
        return None
    cmd = [sys.executable, str(REPO / "eval" / env / "report.py"), str(root)]
    cmd += ["--out-dir", str(out)]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        last = (proc.stderr.strip() or proc.stdout.strip()).splitlines()[-1:]
        print(
            f"{env}: report.py failed on {show(root)} (exit {proc.returncode}): {' '.join(last)}"
        )
        return None
    # env, root, then the report's own columns
    scores, contrasts = (
        (
            list(dict.fromkeys(["env", "root", *head])),
            [{"env": r["env"], "root": label, **r} for r in rows],
        )
        for head, rows in (read_csv(out / n) for n in ("scores.csv", "contrasts.csv"))
    )
    print(
        f"{env}: {show(root)} -> {show(out)} ({len(scores[1])} score rows, {len(contrasts[1])} contrast rows)"
    )
    return scores, contrasts


def write_csv(path: Path, rows: list[Row], header: list[str]) -> None:
    """The rows under the union of their columns; with no rows, the first report's header."""
    fields = list(dict.fromkeys(k for row in rows for k in row)) or header
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(rows)


def headline(scores: list[Row]) -> list[Row]:
    """Each (env, root)'s pooled rows over every scenario, or its per-scenario rows where it pools none."""
    out: list[Row] = []
    for key in dict.fromkeys((r["env"], r["root"]) for r in scores):
        rows = [r for r in scores if (r["env"], r["root"]) == key]
        pooled = [r for r in rows if r["scenario"].startswith("POOLED (")]
        out += pooled or rows
    return out


def interval(row: Row) -> str:
    try:
        return f"{float(row['score']):.3f} [{float(row['ci_lo']):.3f}, {float(row['ci_hi']):.3f}]"
    except ValueError:
        return row["score"] or "-"


def write_md(path: Path, rows: list[Row]) -> None:
    cols = ["env", "root", "scenario", "model", "formation", "mitigation", "n"]
    lines = [
        "# MAMUBench stats",
        "",
        "Headline per environment, model and formation: each report's score with its 95% interval (`ci_method` in",
        "stats.csv says which). Per-scenario rows, the paper references and the formation contrasts: stats.csv,",
        "contrasts.csv, and each report's own results.md under this directory.",
        "",
        "| " + " | ".join(cols) + " | score [95% CI] |",
        "|" + "---|" * (len(cols) + 1),
    ]
    lines += [
        "| " + " | ".join(r.get(c, "") for c in cols) + f" | {interval(r)} |"
        for r in rows
    ]
    path.write_text("\n".join(lines) + "\n")


def plot(path: Path, rows: list[Row]) -> None:
    """One panel per env: the headline per formation, one bar per model, 95% intervals as error bars."""
    # the optional `plot` group: imported untyped, so the strict check passes on a clone without it
    matplotlib: Any = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt: Any = importlib.import_module("matplotlib.pyplot")

    first_root = {r["env"]: r["root"] for r in reversed(rows)}
    keep = [r for r in rows if r["root"] == first_root[r["env"]]]
    keep = [
        r for r in keep if r["mitigation"] == "none" and r["scenario"][:8] == "POOLED ("
    ]
    envs = list(dict.fromkeys(r["env"] for r in keep))
    if not envs:
        print("plot: no pooled rows to plot; skipped")
        return
    fig, axes = plt.subplots(1, len(envs), figsize=(4 * len(envs), 3.2), squeeze=False)
    for ax, env in zip(axes[0], envs, strict=True):
        cells = [r for r in keep if r["env"] == env]
        forms = [f for f in FORMATIONS if any(r["formation"] == f for r in cells)]
        models = list(dict.fromkeys(r["model"] for r in cells))
        width = 0.8 / len(models)
        for i, model in enumerate(models):
            by_form = {
                r["formation"]: r for r in cells if r["model"] == model and r["score"]
            }
            xs: list[float] = []
            ys: list[float] = []
            err: tuple[list[float], list[float]] = ([], [])
            for x, form in enumerate(forms):
                if r := by_form.get(form):
                    score = float(r["score"])
                    xs.append(x + (i - (len(models) - 1) / 2) * width)
                    ys.append(score)
                    err[0].append(score - float(r["ci_lo"] or score))
                    err[1].append(float(r["ci_hi"] or score) - score)
            ax.bar(xs, ys, width, yerr=err, capsize=2, label=model)
        ax.set_xticks(range(len(forms)), forms, fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_title(env)
    axes[0][0].set_ylabel("headline score")
    axes[0][-1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"-> {show(path)}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out: Path = args.out_dir.resolve()
    scores: list[Row] = []
    contrasts: list[Row] = []
    headers: list[tuple[list[str], list[str]]] = []
    for env, roots in roots_by_env(args.roots).items():
        labels: set[str] = set()
        for root in dict.fromkeys(roots):  # the same directory twice is read once
            # two roots with one basename (a/results, b/results) get their own label and output dir
            label, n = root.name, 1
            while label in labels:
                n += 1
                label = f"{root.name}-{n}"
            labels.add(label)
            if label != root.name:
                print(
                    f"{env}: {show(root)} shares its name with an earlier root; labelled {label}"
                )
            got = report(env, root, label, out / env / label)
            if got:
                scores += got[0][1]
                contrasts += got[1][1]
                headers.append((got[0][0], got[1][0]))
    if not scores:
        print("no runs found; nothing written")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "stats.csv", scores, headers[0][0])
    write_csv(out / "contrasts.csv", contrasts, headers[0][1])
    write_md(out / "stats.md", headline(scores))
    print(f"-> {show(out)}/stats.csv, contrasts.csv, stats.md")
    if args.plot:
        plot(out / "stats.png", headline(scores))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
