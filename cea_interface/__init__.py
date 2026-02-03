"""
CEA Model Interface Package.

Provides a hybrid Excel-Python interface for the microsimulation model:
- Excel input template for parameter modification
- Python bridge to run simulations
- Pre-computed scenarios for instant results
- Results export back to Excel
"""

from .excel_template import CEAExcelTemplate
from .bridge import CEABridge, run_from_excel
from .scenarios import ScenarioManager, PrecomputedScenarios

__all__ = [
    "CEAExcelTemplate",
    "CEABridge",
    "run_from_excel",
    "ScenarioManager",
    "PrecomputedScenarios",
]
