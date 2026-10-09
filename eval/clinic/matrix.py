"""The paper's clinic runs (appendix, Run Details): what `python run.py clinic` plays.

The Qwen3.8-max coordinator plays its episodes of record (its low-reasoning mornings, `expected/
episodes_of_record.csv.gz`). The mitigation arms' runs are `mitigations.RUNS` (`python run.py clinic --mitigation
all`).
"""

from _matrix import MODELS, Cells

PAPER = Cells(
    MODELS,
    ("coordinator", "team", "team_silent"),
    episodes=20,
    per_formation={"team_silent": 5},
    of_record=frozenset({("qwen/qwen3.8-max", "coordinator")}),
)
