"""The paper's API key runs (appendix, Run Details): what `python run.py api_key` plays.

The mitigation arms' runs are `mitigations.RUNS` (`python run.py api_key --mitigation all`).
"""

from _matrix import MODELS, Cells

PAPER = Cells(MODELS, ("solo", "coordinator", "team_silent", "team"), episodes=20)
