"""The paper's merge-queue runs (appendix, Run Details): what `python run.py merge_queue` plays.

Every scenario of record is the paper's three (`oversub`, `volunteer_p1`, `volunteer_p3`); an episode number is a
scenario's seed (`scenarios.Scenario.world_epoch`). The mitigation arms' runs are `mitigations.RUNS` (`python run.py
merge_queue --mitigation all`).
"""

from _matrix import CLAUDE, Cells

PAPER = Cells(CLAUDE, ("solo", "coordinator", "team_silent", "team"), episodes=20)
