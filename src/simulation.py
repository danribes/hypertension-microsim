"""
Main microsimulation engine for hypertension model.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from tqdm import tqdm
import pandas as pd

from .patient import Patient, CardiacState, RenalState, Treatment
from .population import PopulationGenerator, PopulationParams, generate_default_population
from .transitions import TransitionCalculator, AdherenceTransition, NeuroTransition
from .treatment import TreatmentManager
from .treatment import TreatmentManager
from .costs.costs import (
    CostInputs, US_COSTS, UK_COSTS, get_total_cost, get_event_cost,
    get_productivity_loss, get_acute_absenteeism_cost, get_drug_cost
)
from .utilities import get_utility, calculate_monthly_qaly


@dataclass
class SimulationConfig:
    """Configuration for the simulation."""
    n_patients: int = 1000
    time_horizon_months: int = 480  # 40 years
    cycle_length_months: float = 1.0
    discount_rate: float = 0.03
    cost_perspective: str = "US"  # "US" or "UK"
    seed: Optional[int] = None
    show_progress: bool = True


@dataclass
class SimulationResults:
    """Container for simulation results."""
    treatment: Treatment
    n_patients: int
    
    # Primary outcomes
    total_costs: float = 0.0
    total_indirect_costs: float = 0.0  # New: Productivity loss
    total_qalys: float = 0.0
    life_years: float = 0.0
    
    # Event counts
    mi_events: int = 0
    stroke_events: int = 0  # Total strokes (ischemic + hemorrhagic)
    ischemic_stroke_events: int = 0
    hemorrhagic_stroke_events: int = 0
    tia_events: int = 0
    hf_events: int = 0
    cv_deaths: int = 0
    non_cv_deaths: int = 0
    
    # Renal outcomes
    esrd_events: int = 0
    ckd_4_events: int = 0
    
    # BP control
    time_controlled: float = 0.0
    time_uncontrolled: float = 0.0
    
    # Neuro outcomes
    dementia_cases: int = 0
    
    # Medication Usage
    sglt2_users: int = 0  # Count of patients on SGLT2i
    
    # Per-patient averages
    mean_costs: float = 0.0
    mean_qalys: float = 0.0
    mean_life_years: float = 0.0
    
    # Individual patient data
    patient_results: List[Dict] = field(default_factory=list)
    
    def calculate_means(self):
        """Calculate per-patient means."""
        self.mean_costs = self.total_costs / self.n_patients
        self.mean_qalys = self.total_qalys / self.n_patients
        self.mean_life_years = self.life_years / self.n_patients


class Simulation:
    """
    Microsimulation engine for hypertension cost-effectiveness model.
    """
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.rng = np.random.default_rng(self.config.seed)
        
        # Initialize components
        self.transition_calc = TransitionCalculator(seed=self.config.seed)
        self.adherence_transition = AdherenceTransition(seed=self.config.seed)
        self.neuro_transition = NeuroTransition(seed=self.config.seed)
        self.treatment_mgr = TreatmentManager(seed=self.config.seed)
        
        # Cost inputs
        if self.config.cost_perspective == "UK":
            self.costs = UK_COSTS
        else:
            self.costs = US_COSTS
    
    def run(
        self,
        patients: List[Patient],
        treatment: Treatment
    ) -> SimulationResults:
        """
        Run the microsimulation for a treatment arm.
        """
        results = SimulationResults(
            treatment=treatment,
            n_patients=len(patients)
        )
        
        # Assign treatment to all patients
        for patient in patients:
            self.treatment_mgr.assign_treatment(patient, treatment)
            if patient.on_sglt2_inhibitor:
                results.sglt2_users += 1
        
        # Run simulation
        n_cycles = int(self.config.time_horizon_months / self.config.cycle_length_months)
        
        iterator = range(n_cycles)
        if self.config.show_progress:
            iterator = tqdm(iterator, desc=f"Simulating {treatment.value}")
        
        for cycle in iterator:
            for patient in patients:
                if not patient.is_alive:
                    continue
                
                # 0.5. Check Adherence Change
                if self.adherence_transition.check_adherence_change(patient):
                    # Recalculate treatment effect if adherence state flips
                    # This scales the base effect by adherence factor (0.3 if non-adherent)
                    self.treatment_mgr.update_effect_for_adherence(patient)
                
                # Option H: Safety Rules (Potassium Check)
                # Check happens quarterly if on MRA (Spironolactone)
                is_quarterly_check = (int(patient.time_in_simulation) % 3 == 0)
                
                if is_quarterly_check and patient.treatment == Treatment.SPIRONOLACTONE:
                    # Add Lab Cost
                    patient.accrue_costs(self.costs.lab_test_cost_k)
                    
                    # Check for Safety Stop
                    if self.treatment_mgr.check_safety_stop_rules(patient):
                        # STOP TREATMENT -> REVERT TO STANDARD CARE
                        self.treatment_mgr.assign_treatment(patient, Treatment.STANDARD_CARE)
                        # Flag as Hyperkalemia Event
                        patient.hyperkalemia_history += 1
                        
                # 0.6. Check Neuro Progression
                old_neuro = patient.neuro_state
                self.neuro_transition.check_neuro_progression(patient)
                if patient.neuro_state != old_neuro and patient.neuro_state.value == "dementia":
                    results.dementia_cases += 1
                
                # 1. Calculate and sample CARDIAC events / Mortality
                probs = self.transition_calc.calculate_transitions(patient)
                new_event = self.transition_calc.sample_event(patient, probs)
                
                if new_event:
                    if new_event == "NON_CV_DEATH":
                        results.non_cv_deaths += 1
                        # We can either add a specific state or just stop simulating
                        # For now, we can set cardiac state to CV_DEATH as a proxy for death,
                        # or better, add a flag. But Patient handles is_alive via state check.
                        # Using "non_cv_death" string as state is hacky but consistent with is_alive check
                        # Actually Patient.is_alive checks:
                        # self.cardiac_state != "non_cv_death"
                        patient.cardiac_state = "non_cv_death" 
                    else:
                        # Record and transition
                        self._record_event(new_event, results)
                        patient.transition_cardiac(new_event)
                        
                        # Apply one-time event cost (Direct)
                        event_cost = get_event_cost(new_event.value, self.costs)
                        # Apply one-time absenteeism cost (Indirect)
                        absenteeism_cost = get_acute_absenteeism_cost(new_event.value, self.costs, patient.age)
                        
                        # Discounting
                        years = patient.time_in_simulation / 12
                        discount = 1 / ((1 + self.config.discount_rate) ** years)
                        
                        patient.accrue_costs(event_cost * discount) # Total costs in patient accumulates direct?
                        # Note: We might want to separate indirect in patient object too, 
                        # but for now we aggregate in results.
                        
                        results.total_costs += event_cost * discount
                        results.total_indirect_costs += absenteeism_cost * discount

                if not patient.is_alive:
                    continue

                # 2. Accrue costs and QALYs (State-based)
                self._accrue_outcomes(patient, results)
                
                # 2.5. Update SBP with dynamic equation (uses stored treatment effect)
                patient.update_sbp(patient._treatment_effect_mmhg, self.rng)
                
                # 3. Advance time (handles Age + Renal Progression)
                old_renal = patient.renal_state
                patient.advance_time(self.config.cycle_length_months)
                
                # Check for renal transitions
                if patient.renal_state != old_renal:
                    if patient.renal_state == RenalState.ESRD:
                        results.esrd_events += 1
                    elif patient.renal_state == RenalState.CKD_STAGE_4:
                        results.ckd_4_events += 1
                
                # 4. Check treatment discontinuation
                if self.treatment_mgr.check_discontinuation(patient):
                    patient.treatment = Treatment.STANDARD_CARE
        
        # Store individual patient results
        for patient in patients:
            results.patient_results.append(patient.to_dict())
        
        results.calculate_means()
        return results
    
    def _record_event(self, state: CardiacState, results: SimulationResults):
        """Record cardiac event in results."""
        if state == CardiacState.ACUTE_MI:
            results.mi_events += 1
        elif state == CardiacState.ACUTE_ISCHEMIC_STROKE:
            results.ischemic_stroke_events += 1
            results.stroke_events += 1  # Also increment total
        elif state == CardiacState.ACUTE_HEMORRHAGIC_STROKE:
            results.hemorrhagic_stroke_events += 1
            results.stroke_events += 1  # Also increment total
        elif state == CardiacState.ACUTE_STROKE:  # Legacy support
            results.stroke_events += 1
        elif state == CardiacState.TIA:
            results.tia_events += 1
        elif state == CardiacState.ACUTE_HF:
            results.hf_events += 1
        elif state == CardiacState.CV_DEATH:
            results.cv_deaths += 1
    
    def _accrue_outcomes(self, patient: Patient, results: SimulationResults):
        """Accrue monthly costs and QALYs."""
        # Monthly state management costs (Cardiac + Renal)
        monthly_cost = get_total_cost(patient, self.costs, is_monthly=True)
        
        # Monthly productivity loss (Indirect)
        monthly_indirect = get_productivity_loss(patient, self.costs, is_monthly=True)
        
        # Drug cost (Updated for Option F to include SGLT2)
        drug_cost = get_drug_cost(patient, self.costs)
        
        # Total monthly cost
        total_monthly = monthly_cost + drug_cost
        
        # Discounting
        years = patient.time_in_simulation / 12
        discount_factor = 1 / ((1 + self.config.discount_rate) ** years)
        
        discounted_cost = total_monthly * discount_factor
        
        patient.accrue_costs(discounted_cost)
        results.total_costs += discounted_cost
        
        # Accrue indirect
        results.total_indirect_costs += monthly_indirect * discount_factor
        
        # QALYs
        qaly = calculate_monthly_qaly(patient, self.config.discount_rate)
        patient.accrue_qalys(qaly)
        results.total_qalys += qaly
        
        # Life years
        results.life_years += (1/12) * discount_factor
        
        # BP control tracking
        if patient.is_bp_controlled:
            results.time_controlled += 1/12
        else:
            results.time_uncontrolled += 1/12


@dataclass
class CEAResults:
    """Cost-effectiveness analysis results."""
    intervention: SimulationResults
    comparator: SimulationResults
    incremental_costs: float = 0.0
    incremental_qalys: float = 0.0
    icer: Optional[float] = None
    
    def calculate_icer(self):
        """Calculate ICER."""
        self.incremental_costs = self.intervention.mean_costs - self.comparator.mean_costs
        self.incremental_qalys = self.intervention.mean_qalys - self.comparator.mean_qalys
        
        if self.incremental_qalys > 0:
            self.icer = self.incremental_costs / self.incremental_qalys
        else:
            self.icer = None  # Dominated or cost-saving


def run_cea(
    n_patients: int = 1000,
    time_horizon_years: int = 40,
    seed: Optional[int] = None,
    perspective: str = "US"
) -> CEAResults:
    """Run full CEA."""
    config = SimulationConfig(
        n_patients=n_patients,
        time_horizon_months=time_horizon_years * 12,
        seed=seed,
        cost_perspective=perspective
    )
    
    sim = Simulation(config)
    
    # Generate identical populations using same seed
    pop_params = PopulationParams(n_patients=n_patients, seed=seed)
    
    # IXA-001 arm
    generator = PopulationGenerator(pop_params)
    patients_ixa = generator.generate()
    results_ixa = sim.run(patients_ixa, Treatment.IXA_001)
    
    # Comparator arm
    generator = PopulationGenerator(pop_params)
    patients_spi = generator.generate()
    results_spi = sim.run(patients_spi, Treatment.SPIRONOLACTONE)
    
    cea = CEAResults(intervention=results_ixa, comparator=results_spi)
    cea.calculate_icer()
    
    return cea


def print_cea_results(cea: CEAResults):
    """Print formatted CEA results including renal outcomes."""
    print("\n" + "="*60)
    print("COST-EFFECTIVENESS ANALYSIS RESULTS (Cardiac & Renal)")
    print("="*60)
    
    print(f"\n{'Outcome':<30} {'IXA-001':>15} {'Spironol.':>15}")
    print("-"*60)
    print(f"{'Mean Costs':<30} ${cea.intervention.mean_costs:>14,.0f} ${cea.comparator.mean_costs:>14,.0f}")
    print(f"{'Mean QALYs':<30} {cea.intervention.mean_qalys:>15.3f} {cea.comparator.mean_qalys:>15.3f}")
    print(f"{'Mean Life Years':<30} {cea.intervention.mean_life_years:>15.2f} {cea.comparator.mean_life_years:>15.2f}")
    
    print("-" * 60)
    print("CARDIAC EVENTS (per 1000)")
    print(f"{'Myocardial Infarction':<30} {cea.intervention.mi_events:>15} {cea.comparator.mi_events:>15}")
    print(f"{'Stroke (Total)':<30} {cea.intervention.stroke_events:>15} {cea.comparator.stroke_events:>15}")
    print(f"{'  - Ischemic Stroke':<30} {cea.intervention.ischemic_stroke_events:>15} {cea.comparator.ischemic_stroke_events:>15}")
    print(f"{'  - Hemorrhagic Stroke':<30} {cea.intervention.hemorrhagic_stroke_events:>15} {cea.comparator.hemorrhagic_stroke_events:>15}")
    print(f"{'TIA (Transient Ischemic)':<30} {cea.intervention.tia_events:>15} {cea.comparator.tia_events:>15}")
    print(f"{'Heart Failure Deaths/Events':<30} {cea.intervention.hf_events:>15} {cea.comparator.hf_events:>15}")
    print(f"{'CV Deaths':<30} {cea.intervention.cv_deaths:>15} {cea.comparator.cv_deaths:>15}")
    
    print("-" * 60)
    print(f"INDIRECT COSTS (Productivity Loss)")
    print(f"{'Mean Indirect Costs':<30} ${cea.intervention.total_indirect_costs/cea.intervention.n_patients:>14,.0f} ${cea.comparator.total_indirect_costs/cea.comparator.n_patients:>14,.0f}")
    
    print("-" * 60)
    print("RENAL EVENTS (per 1000)")
    print(f"{'Progression to CKD 4':<30} {cea.intervention.ckd_4_events:>15} {cea.comparator.ckd_4_events:>15}")
    print(f"{'Progression to ESRD':<30} {cea.intervention.esrd_events:>15} {cea.comparator.esrd_events:>15}")
    
    print("-" * 60)
    print("NEUROLOGICAL OUTCOMES (per 1000 - Model Only)")
    print(f"{'New Dementia Cases':<30} {cea.intervention.dementia_cases:>15} {cea.comparator.dementia_cases:>15}")
    
    print("-" * 60)
    print("MEDICATION UPTAKE")
    sglt2_ixa = f"{cea.intervention.sglt2_users} ({(cea.intervention.sglt2_users/cea.intervention.n_patients)*100:.1f}%)"
    sglt2_spi = f"{cea.comparator.sglt2_users} ({(cea.comparator.sglt2_users/cea.comparator.n_patients)*100:.1f}%)"
    print(f"{'SGLT2i Users':<30} {sglt2_ixa:>15} {sglt2_spi:>15}")
    
    print("\n" + "-"*60)
    print(f"{'Incremental Costs:':<30} ${cea.incremental_costs:>14,.0f}")
    print(f"{'Incremental QALYs:':<30} {cea.incremental_qalys:>15.3f}")
    
    if cea.icer is not None:
        print(f"{'ICER ($/QALY):':<30} ${cea.icer:>14,.0f}")
    else:
        print(f"{'ICER:':<30} {'Dominated/Cost-saving':>15}")
    
    print("="*60 + "\n")
