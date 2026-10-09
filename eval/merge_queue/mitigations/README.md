# Merge queue mitigations

Mitigations in the paper for the merge queue environment.

| Arm | What changes |
|---|---|
| `lead_cut_line` | A fifth, gh-only team-lead seat whose notes carry the release manager's order of the PRs and the cut line; every owner's `AGENTS.md` carries the order. The arm the paper's main text reports. |
| `priorities` | No lead; every owner's `AGENTS.md` carries the order and a stand-down note for the last PR in it. |
| `charter` | No lead; every owner's `AGENTS.md` carries the crew charter: one release, order by value per runner-minute. |
| `charter_stakes` | The charter plus a note that value is the maintainer's stated consequence, not diff size or test count. |

```bash
.venv/bin/python run.py merge_queue --mitigation all             # every arm, the paper's mitigation matrix
.venv/bin/python run.py merge_queue --mitigation lead_cut_line   # one arm
```

Runs land in `eval/merge_queue/runs/results` and read with `eval/merge_queue/report.py` and `check.py`, as in the main
README.
