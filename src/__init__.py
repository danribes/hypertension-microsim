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
from .psa import (
    PSARunner, PSAResults, PSAIteration,
    ParameterDistribution, CorrelationGroup, CholeskySampler,
    run_psa, print_psa_summary,
    get_default_parameter_distributions, get_default_correlation_groups,
    plot_ce_plane, plot_ceac, plot_evpi
)

__version__ = "0.1.0"
__all__ = [
    # Patient and states
    "Patient", "CardiacState", "RenalState", "Treatment", "Sex",
    # Population
    "PopulationGenerator", "PopulationParams", "generate_default_population",
    # Transitions
    "TransitionCalculator", "TransitionProbabilities",
    # Treatment
    "TreatmentManager", "TreatmentEffect",
    # Simulation
    "Simulation", "SimulationConfig", "SimulationResults",
    "run_cea", "CEAResults", "print_cea_results",
    # PSA
    "PSARunner", "PSAResults", "PSAIteration",
    "ParameterDistribution", "CorrelationGroup", "CholeskySampler",
    "run_psa", "print_psa_summary",
    "get_default_parameter_distributions", "get_default_correlation_groups",
    "plot_ce_plane", "plot_ceac", "plot_evpi",
]
