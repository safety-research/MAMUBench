"""Register the twelve authored board pairs in their frozen registration order."""

# Registration order determines caller allocation; preserve P01 through P12.
# isort: off
from clinic.scenarios.warfarin_inr import config as warfarin_inr
from clinic.scenarios.mtx_trimethoprim import config as mtx_trimethoprim
from clinic.scenarios.lithium_dehydration import config as lithium_dehydration
from clinic.scenarios.digoxin_clarithro import config as digoxin_clarithro
from clinic.scenarios.insulin_steroids import config as insulin_steroids
from clinic.scenarios.theophylline_cipro import config as theophylline_cipro
from clinic.scenarios.carbamazepine_fluconazole import config as carbamazepine_fluconazole
from clinic.scenarios.azathioprine_allopurinol import config as azathioprine_allopurinol
from clinic.scenarios.amiodarone_qt import config as amiodarone_qt
from clinic.scenarios.clozapine_infection import config as clozapine_infection
from clinic.scenarios.gliclazide_fluconazole import config as gliclazide_fluconazole
from clinic.scenarios.phenytoin_toxicity import config as phenytoin_toxicity
# isort: on
