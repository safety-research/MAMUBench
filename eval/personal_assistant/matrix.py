"""The paper's personal-assistant runs (appendix, Run Details): what `python run.py personal_assistant` plays.

`--context-files on` is the supplementary rerun with AGENTS.md in context. The mitigation arms' runs are
`mitigations.RUNS` (`python run.py personal_assistant --mitigation all`: the paper's draw of previously failed team
episodes under every arm and the control, into one runs root that `mitigations/report.py` reads).
"""

from _matrix import CLAUDE, MODELS, Cells

PAPER = Cells(
    MODELS[:4],
    ("coordinator", "team", "team_silent"),
    episodes=100,
    per_model={"gpt-5.6-sol": 50, "gpt-5.6-terra": 50},
)
CONTEXT_FILES = Cells(
    CLAUDE, ("team", "team_silent"), episodes=100, runs_name="context_files"
)
