# Personal assistant mitigations

Mitigations in the paper for the personal assistant environment.

| Arm | What changes |
|---|---|
| `guard` | Checkout is refused while the confirming agent has messages the platform accepted but has not yet delivered to it. |
| `full_stack` | The guard, plus line notes in cart and draft views, plus an owner acknowledgement that checkout waits for. |

```bash
.venv/bin/python run.py personal_assistant --mitigation all   # both arms and the control (over failed runs)
.venv/bin/python eval/personal_assistant/mitigations/report.py eval/personal_assistant/runs/mitigations
```

On Modal, pull the `mitigations` root first (`.venv/bin/python -m modal run eval/modal_app.py::pull --eval
personal_assistant --runs-name mitigations`).
