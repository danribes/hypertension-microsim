"""
Hypertension Microsimulation Model

A patient-level microsimulation for evaluating IXA-001 vs standard of care
in adults with resistant hypertension.
"""

from .patient import Patient, CardiacState, RenalState, Treatment, Sex
from .population import PopulationGenerator, PopulationParams, generate_default_population
from .transitions import TransitionCalculator, TransitionProbabilities
from .treatment import TreatmentManager, TreatmentEffect, TREATMENT_EFFECTS
from .simulation import (
    Simulation, SimulationConfig, SimulationResults, 
    run_cea, CEAResults, print_cea_results
)

__version__ = "0.1.0"
__all__ = [
    "Patient", "CardiacState", "RenalState", "Treatment", "Sex",
    "PopulationGenerator", "PopulationParams",
    "TransitionCalculator", "TransitionProbabilities",
    "TreatmentManager", "TreatmentEffect",
    "Simulation", "SimulationConfig", "SimulationResults",
    "run_cea", "CEAResults", "print_cea_results",
    "generate_default_population"
]
