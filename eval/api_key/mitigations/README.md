# API key mitigations

Mitigations in the paper for the API key environment.

| Arm | What changes |
|---|---|
| `lead_value` | A team lead with no jobs of its own holds every job-changing tool, with a portfolio brief and a value clause; the users' agents keep status, dashboard and wait. The recommended arm. |
| `lead_full_stack` | `lead_value` plus the release clause on the lead's brief and the defer clause on every user's request. |

```bash
.venv/bin/python run.py api_key --mitigation all          # both arms, the paper's mitigation matrix
.venv/bin/python run.py api_key --mitigation lead_value   # one arm
```

Runs land in `eval/api_key/runs/results` and read with `eval/api_key/report.py` and `check.py`, as in the main README.
