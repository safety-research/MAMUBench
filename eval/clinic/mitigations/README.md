# Clinic mitigations

Mitigations in the paper for the clinic environment.

| Arm | What changes |
|---|---|
| `s1` | Stricter booking behavior, look once then act, and book before ending the call. |
| `s2` | Stricter booking behavior, look once then act, and cancel and book as one action. |
| `s3` | Stricter booking behavior, act on what you hear, and book before ending the call. The recommended arm. |

```bash
.venv/bin/python run.py clinic --mitigation all   # s1, s2 and s3, the paper's mitigation matrix
.venv/bin/python run.py clinic --mitigation s3    # one arm
```

Runs land in `eval/clinic/runs/results` and read with `eval/clinic/report.py` and `check.py`, as in the main README.
