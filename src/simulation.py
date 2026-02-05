"""
Main microsimulation engine for hypertension model.
"""

import copy
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from tqdm import tqdm
import pandas as pd

from .patient import Patient, CardiacState, RenalState, Treatment
from .population import PopulationGenerator, PopulationParams, generate_default_population
from .transitions import TransitionCalculator, AdherenceTransition, NeuroTransition, AFTransition
from .treatment import TreatmentManager
from .risks.prevent import validate_prevent_implementation
from .costs.costs import (
    CostInputs, US_COSTS, UK_COSTS, get_total_cost, get_event_cost,
    get_productivity_loss, get_acute_absenteeism_cost, get_drug_cost
)
from .utilities import get_utility, calculate_monthly_qaly


@dataclass
class SimulationConfig:
    """
    Configuration for the simulation.

    Attributes:
        n_patients: Number of patients to simulate per arm
        time_horizon_months: Total simulation duration in months
        cycle_length_months: Length of each simulation cycle (default 1 month)
        discount_rate: Annual discount rate for costs and outcomes (default 3%)
        cost_perspective: Cost perspective, "US" or "UK"
        seed: Random seed for reproducibility
        show_progress: Show progress bar during simulation

        # Methodological options (CHEERS 2022 compliant defaults)
        use_half_cycle_correction: If True, apply half-cycle correction to discounting
        use_competing_risks_framework: If True, use proper competing risks (vs 95% cap)
        use_dynamic_stroke_subtypes: If True, vary stroke subtypes by patient factors
        use_validated_life_tables: If True, use SSA/ONS life tables for mortality
        use_kfre_model: If True, use KFRE-informed eGFR decline model
        life_table_country: Country for life tables, "US" or "UK"

    Reference:
        Husereau D, et al. Consolidated Health Economic Evaluation Reporting
        Standards 2022 (CHEERS 2022). Value Health. 2022;25(1):3-9.
    """
    n_patients: int = 1000
    time_horizon_months: int = 480  # 40 years
    cycle_length_months: float = 1.0
    discount_rate: float = 0.03
    cost_perspective: str = "US"  # "US" or "UK"
    seed: Optional[int] = None
    show_progress: bool = True

    # Methodological options (all True for CHEERS 2022 compliance)
    use_half_cycle_correction: bool = True
    use_competing_risks_framework: bool = True
    use_dynamic_stroke_subtypes: bool = True
    use_validated_life_tables: bool = True
    use_kfre_model: bool = True
    life_table_country: str = "US"  # "US" or "UK"

    # Economic perspective for ICER calculation
    # "healthcare_system": Direct medical costs only (default for most HTAs)
    # "societal": Include indirect costs (productivity loss, absenteeism)
    # Reference: NICE TA Manual Section 4.4; Second Panel on CEA (Sanders et al. JAMA 2016)
    economic_perspective: str = "societal"  # "healthcare_system" or "societal"


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
    renal_deaths: int = 0  # Deaths from renal causes (non-CV ESRD mortality)
    
    # BP control
    time_controlled: float = 0.0
    time_uncontrolled: float = 0.0
    
    # Neuro outcomes
    dementia_cases: int = 0

    # AF outcomes (aldosterone-specific)
    new_af_events: int = 0

    # Medication Usage
    sglt2_users: int = 0  # Count of patients on SGLT2i
    
    # Per-patient averages
    mean_costs: float = 0.0  # Direct medical costs only
    mean_indirect_costs: float = 0.0  # Productivity/absenteeism costs
    mean_total_costs: float = 0.0  # Direct + Indirect (societal perspective)
    mean_qalys: float = 0.0
    mean_life_years: float = 0.0
    
    # Individual patient data
    patient_results: List[Dict] = field(default_factory=list)
    
    def calculate_means(self):
        """Calculate per-patient means."""
        self.mean_costs = self.total_costs / self.n_patients
        self.mean_indirect_costs = self.total_indirect_costs / self.n_patients
        self.mean_total_costs = (self.total_costs + self.total_indirect_costs) / self.n_patients
        self.mean_qalys = self.total_qalys / self.n_patients
        self.mean_life_years = self.life_years / self.n_patients

    @property
    def total_deaths(self) -> int:
        """Total deaths from all causes."""
        return self.cv_deaths + self.non_cv_deaths + self.renal_deaths

    @property
    def survival_rate(self) -> float:
        """Proportion of patients surviving simulation."""
        return 1.0 - (self.total_deaths / self.n_patients) if self.n_patients > 0 else 0.0

    def summary(self) -> str:
        """Return formatted summary of simulation results."""
        lines = [
            f"Simulation Results: {self.treatment.value}",
            f"{'=' * 40}",
            f"Patients: {self.n_patients}",
            f"",
            f"Outcomes:",
            f"  Mean Costs: ${self.mean_costs:,.0f}",
            f"  Mean QALYs: {self.mean_qalys:.3f}",
            f"  Mean Life Years: {self.mean_life_years:.2f}",
            f"",
            f"Events:",
            f"  MI: {self.mi_events}",
            f"  Stroke: {self.stroke_events} (Ischemic: {self.ischemic_stroke_events}, Hemorrhagic: {self.hemorrhagic_stroke_events})",
            f"  TIA: {self.tia_events}",
            f"  HF: {self.hf_events}",
            f"  New AF: {self.new_af_events}",
            f"  ESRD: {self.esrd_events}",
            f"",
            f"Deaths:",
            f"  CV: {self.cv_deaths}",
            f"  Non-CV: {self.non_cv_deaths}",
            f"  Renal: {self.renal_deaths}",
            f"  Survival Rate: {self.survival_rate:.1%}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"SimulationResults(treatment={self.treatment.value}, n={self.n_patients}, "
            f"costs=${self.mean_costs:,.0f}, qalys={self.mean_qalys:.3f})"
        )


class Simulation:
    """
    Microsimulation engine for hypertension cost-effectiveness model.

    Implements individual patient simulation with:
    - Monthly cycle length
    - Competing risks for cardiovascular events
    - Dual cardiac and renal state tracking
    - Half-cycle correction for discounting (optional, default True)

    Reference:
        Briggs A, Sculpher M, Claxton K. Decision Modelling for Health
        Economic Evaluation. Oxford University Press. 2006.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.rng = np.random.default_rng(self.config.seed)

        # Validate PREVENT risk equations on first initialization
        # This ensures clinical plausibility of cardiovascular risk predictions
        self._validate_risk_model()

        # Initialize components with methodological options
        self.transition_calc = TransitionCalculator(
            seed=self.config.seed,
            country=self.config.life_table_country,
            use_life_tables=self.config.use_validated_life_tables,
            use_competing_risks=self.config.use_competing_risks_framework,
            use_dynamic_stroke_subtypes=self.config.use_dynamic_stroke_subtypes
        )
        self.adherence_transition = AdherenceTransition(seed=self.config.seed)
        self.neuro_transition = NeuroTransition(seed=self.config.seed)
        self.af_transition = AFTransition(seed=self.config.seed)
        self.treatment_mgr = TreatmentManager(seed=self.config.seed)

        # Cost inputs
        if self.config.cost_perspective == "UK":
            self.costs = UK_COSTS
        else:
            self.costs = US_COSTS

    # Class-level flag to avoid repeated validation
    _prevent_validated = False

    def _validate_risk_model(self):
        """
        Validate PREVENT risk equations produce clinically plausible outputs.

        This validation runs once on first Simulation instantiation and verifies
        that risk predictions fall within expected ranges for test cases from
        the PREVENT derivation/validation cohorts.

        Raises:
            RuntimeError: If PREVENT validation fails, indicating calibration
                issues that could produce invalid CEA results.

        Reference:
            Khan SS, et al. Development and Validation of the American Heart
            Association's PREVENT Equations. Circulation. 2024;149(6):430-449.
        """
        if Simulation._prevent_validated:
            return

        validation_results = validate_prevent_implementation()

        if not validation_results["passed"]:
            failed_cases = [
                c for c in validation_results["cases"] if not c["passed"]
            ]
            error_msg = "PREVENT risk equation validation FAILED:\n"
            for case in failed_cases:
                error_msg += (
                    f"  Case {case['case_id']}: {case['description']}\n"
                    f"    Computed: {case['computed_risk']:.4f}, "
                    f"Expected: {case['expected_range']}\n"
                )
            error_msg += (
                "\nThis indicates miscalibration of the PREVENT equations. "
                "Review src/risks/prevent.py coefficients before running CEA."
            )
            raise RuntimeError(error_msg)

        # Mark as validated to avoid repeated checks
        Simulation._prevent_validated = True

    def _get_discount_factor(
        self,
        time_in_simulation_months: float,
        apply_half_cycle: Optional[bool] = None
    ) -> float:
        """
        Calculate discount factor with optional half-cycle correction.

        Half-cycle correction accounts for the assumption that events and
        outcomes occur throughout the cycle (on average at midpoint), rather
        than at the beginning or end.

        Formula with half-cycle:
            years = (t + 0.5 * cycle_length) / 12
            discount = 1 / (1 + r)^years

        Args:
            time_in_simulation_months: Time since simulation start (months)
            apply_half_cycle: Override config setting if provided

        Returns:
            Discount factor (0-1)

        Reference:
            Briggs A, Sculpher M, Claxton K. Decision Modelling for Health
            Economic Evaluation. Oxford University Press. 2006. Chapter 3.

            ISPOR-SMDM Good Modeling Practices Task Force. State-Transition
            Modeling. Med Decis Making. 2012;32(5):641-653.
        """
        if apply_half_cycle is None:
            apply_half_cycle = self.config.use_half_cycle_correction

        if apply_half_cycle:
            adjusted_months = time_in_simulation_months + (0.5 * self.config.cycle_length_months)
        else:
            adjusted_months = time_in_simulation_months

        years = adjusted_months / 12.0
        return 1.0 / ((1.0 + self.config.discount_rate) ** years)
    
    def run(
        self,
        patients: List[Patient],
        treatment: Treatment
    ) -> SimulationResults:
        """
        Run the microsimulation for a treatment arm.

        Note: Patients are deep-copied to ensure independent arms.
        Each treatment arm simulates on its own copy of the population,
        preventing state contamination between arms.
        """
        # Deep copy patients to ensure each arm is independent
        # This prevents the first arm's events from affecting the second arm
        patients = copy.deepcopy(patients)

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
                
                # Option H: Enhanced Hyperkalemia Management
                # Quarterly potassium monitoring if on MRA (Spironolactone)
                # Reference: Epstein M, et al. Kidney Int. 2015
                is_quarterly_check = (int(patient.time_in_simulation) % 3 == 0)

                if is_quarterly_check and patient.treatment == Treatment.SPIRONOLACTONE:
                    # Add Lab Cost for potassium check
                    patient.accrue_costs(self.costs.lab_test_cost_k)

                    # Enhanced hyperkalemia management with stepped approach
                    if patient.serum_potassium > 5.0:
                        mgmt = self.treatment_mgr.manage_hyperkalemia(
                            patient,
                            use_potassium_binders=True,
                            allow_dose_reduction=True
                        )

                        # Apply additional costs (e.g., potassium binders)
                        if mgmt["additional_cost"] > 0:
                            discount = self._get_discount_factor(patient.time_in_simulation)
                            patient.accrue_costs(mgmt["additional_cost"] * discount)
                            results.total_costs += mgmt["additional_cost"] * discount

                        # Record hyperkalemia episode
                        if mgmt["action"] in ["stop_treatment", "start_potassium_binder"]:
                            patient.hyperkalemia_history += 1

                        # Stop treatment if required
                        if mgmt["treatment_stopped"]:
                            self.treatment_mgr.assign_treatment(patient, Treatment.STANDARD_CARE)
                        
                # 0.6. Check Neuro Progression
                old_neuro = patient.neuro_state
                self.neuro_transition.check_neuro_progression(patient)
                if patient.neuro_state != old_neuro and patient.neuro_state.value == "dementia":
                    results.dementia_cases += 1

                # 0.7. Check AF Onset (Aldosterone-specific outcome)
                # PA patients have 12x elevated AF risk (Monticone 2018)
                # IXA-001 provides significant risk reduction by blocking aldosterone synthesis
                if self.af_transition.check_af_onset(patient):
                    results.new_af_events += 1
                    # Apply one-time AF event cost
                    af_cost = get_event_cost("new_af", self.costs)
                    discount = self._get_discount_factor(patient.time_in_simulation)
                    patient.accrue_costs(af_cost * discount)
                    results.total_costs += af_cost * discount

                # 1. Calculate and sample CARDIAC events / Mortality
                probs = self.transition_calc.calculate_transitions(patient)
                new_event = self.transition_calc.sample_event(patient, probs)
                
                if new_event:
                    if new_event == CardiacState.NON_CV_DEATH:
                        results.non_cv_deaths += 1
                        patient.cardiac_state = CardiacState.NON_CV_DEATH 
                    else:
                        # Record and transition
                        self._record_event(new_event, results)
                        patient.transition_cardiac(new_event)
                        
                        # Apply one-time event cost (Direct)
                        event_cost = get_event_cost(new_event.value, self.costs)
                        # Apply one-time absenteeism cost (Indirect)
                        absenteeism_cost = get_acute_absenteeism_cost(new_event.value, self.costs, patient.age)

                        # Discounting with half-cycle correction
                        # Reference: Briggs A et al. Decision Modelling. Oxford. 2006
                        discount = self._get_discount_factor(patient.time_in_simulation)

                        patient.accrue_costs(event_cost * discount)
                        results.total_costs += event_cost * discount
                        results.total_indirect_costs += absenteeism_cost * discount

                if not patient.is_alive:
                    continue

                # 1.5. TIA → Stroke Conversion Check
                # Patients with recent TIA have elevated stroke risk (10% over 90 days)
                # Reference: Johnston SC et al. JAMA 2000
                if patient.prior_tia_count > 0 and patient.time_since_last_tia is not None:
                    tia_conversion = self.transition_calc.check_tia_to_stroke_conversion(patient)
                    if tia_conversion:
                        # TIA converted to stroke
                        self._record_event(tia_conversion, results)
                        patient.transition_cardiac(tia_conversion)

                        # Apply stroke event costs
                        event_cost = get_event_cost(tia_conversion.value, self.costs)
                        absenteeism_cost = get_acute_absenteeism_cost(
                            tia_conversion.value, self.costs, patient.age
                        )
                        discount = self._get_discount_factor(patient.time_in_simulation)
                        patient.accrue_costs(event_cost * discount)
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

                # Update time since last TIA (for TIA→Stroke conversion tracking)
                if patient.time_since_last_tia is not None:
                    patient.time_since_last_tia += self.config.cycle_length_months

                # Check for renal transitions
                if patient.renal_state != old_renal:
                    if patient.renal_state == RenalState.ESRD:
                        results.esrd_events += 1
                    elif patient.renal_state == RenalState.CKD_STAGE_4:
                        results.ckd_4_events += 1

                # 3.5. ESRD Mortality Check
                # ESRD patients have ~15% annual mortality; 40% is non-CV (renal-specific)
                # Reference: USRDS Annual Data Report 2023
                if patient.renal_state == RenalState.ESRD:
                    if self.transition_calc.check_esrd_mortality(patient):
                        patient.renal_state = RenalState.RENAL_DEATH
                        results.renal_deaths += 1
                
                # 4. Check treatment discontinuation
                disc_result = self.treatment_mgr.check_discontinuation(patient)
                if disc_result["discontinued"]:
                    patient.treatment = Treatment.STANDARD_CARE
                    # Reset dose reduction flag if applicable
                    if hasattr(patient, 'mra_dose_reduced'):
                        patient.mra_dose_reduced = False
        
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
        """
        Accrue monthly costs and QALYs with half-cycle correction.

        Applies discounting with optional half-cycle adjustment for proper
        timing of costs and health outcomes within each cycle.

        Reference:
            ISPOR-SMDM Modeling Good Research Practices Task Force.
            State-Transition Modeling. Med Decis Making. 2012;32(5):641-653.
        """
        # Monthly state management costs (Cardiac + Renal)
        monthly_cost = get_total_cost(patient, self.costs, is_monthly=True)

        # Monthly productivity loss (Indirect)
        monthly_indirect = get_productivity_loss(patient, self.costs, is_monthly=True)

        # Drug cost (Updated for Option F to include SGLT2)
        drug_cost = get_drug_cost(patient, self.costs)

        # Total monthly cost
        total_monthly = monthly_cost + drug_cost

        # Discounting with half-cycle correction
        discount_factor = self._get_discount_factor(patient.time_in_simulation)

        discounted_cost = total_monthly * discount_factor

        patient.accrue_costs(discounted_cost)
        results.total_costs += discounted_cost

        # Accrue indirect
        results.total_indirect_costs += monthly_indirect * discount_factor

        # QALYs with half-cycle correction
        qaly = calculate_monthly_qaly(
            patient,
            self.config.discount_rate,
            self.config.cycle_length_months,
            self.config.use_half_cycle_correction
        )
        patient.accrue_qalys(qaly)
        results.total_qalys += qaly

        # Life years with half-cycle correction
        results.life_years += (1/12) * discount_factor

        # BP control tracking
        if patient.is_bp_controlled:
            results.time_controlled += 1/12
        else:
            results.time_uncontrolled += 1/12


@dataclass
class CEAResults:
    """
    Cost-effectiveness analysis results with proper dominance classification.

    Dominance Classification (ISPOR Good Practices):
        - DOMINANT: Lower costs AND higher QALYs (intervention preferred)
        - DOMINATED: Higher costs AND lower/equal QALYs (comparator preferred)
        - COST_SAVING: Lower costs but lower/equal QALYs (trade-off decision)
        - NE_QUADRANT: Higher costs, higher QALYs (calculate ICER)

    Reference:
        Briggs A, et al. Decision Modelling for Health Economic Evaluation.
        Oxford University Press. 2006.
    """
    intervention: SimulationResults
    comparator: SimulationResults
    incremental_costs: float = 0.0
    incremental_qalys: float = 0.0
    icer: Optional[float] = None
    dominance_status: str = ""  # "dominant", "dominated", "cost_saving", or ""
    economic_perspective: str = "societal"  # "healthcare_system" or "societal"

    def calculate_icer(self):
        """
        Calculate ICER with proper dominance classification.

        The cost-effectiveness plane quadrants:
            NE (↑costs, ↑QALYs): Calculate ICER, compare to WTP
            SE (↓costs, ↑QALYs): DOMINANT - intervention always preferred
            NW (↑costs, ↓QALYs): DOMINATED - comparator always preferred
            SW (↓costs, ↓QALYs): COST_SAVING - trade-off (negative ICER)

        Reference:
            Drummond MF, et al. Methods for the Economic Evaluation of Health
            Care Programmes. 4th ed. Oxford University Press. 2015. Chapter 5.
        """
        # Select cost metric based on economic perspective
        # Societal perspective includes productivity loss (indirect costs)
        # Healthcare system perspective includes only direct medical costs
        if self.economic_perspective == "societal":
            intervention_costs = self.intervention.mean_total_costs
            comparator_costs = self.comparator.mean_total_costs
        else:
            intervention_costs = self.intervention.mean_costs
            comparator_costs = self.comparator.mean_costs

        self.incremental_costs = intervention_costs - comparator_costs
        self.incremental_qalys = self.intervention.mean_qalys - self.comparator.mean_qalys

        # Small threshold to handle floating point comparisons
        QALY_THRESHOLD = 0.001
        COST_THRESHOLD = 1.0

        # Classify by quadrant of cost-effectiveness plane
        higher_costs = self.incremental_costs > COST_THRESHOLD
        lower_costs = self.incremental_costs < -COST_THRESHOLD
        higher_qalys = self.incremental_qalys > QALY_THRESHOLD
        lower_qalys = self.incremental_qalys < -QALY_THRESHOLD

        if lower_costs and higher_qalys:
            # SE quadrant: DOMINANT - intervention is better and cheaper
            self.dominance_status = "dominant"
            self.icer = None  # ICER not meaningful when dominant

        elif higher_costs and lower_qalys:
            # NW quadrant: DOMINATED - intervention is worse and more expensive
            self.dominance_status = "dominated"
            self.icer = None  # ICER not meaningful when dominated

        elif lower_costs and lower_qalys:
            # SW quadrant: COST_SAVING - intervention cheaper but fewer QALYs
            # Some frameworks calculate negative ICER for trade-off analysis
            self.dominance_status = "cost_saving"
            if abs(self.incremental_qalys) > QALY_THRESHOLD:
                # Negative ICER = cost per QALY lost (opportunity cost)
                self.icer = self.incremental_costs / self.incremental_qalys
            else:
                self.icer = None

        elif higher_costs and higher_qalys:
            # NE quadrant: Standard ICER calculation
            self.dominance_status = ""
            self.icer = self.incremental_costs / self.incremental_qalys

        else:
            # Approximately equal on one or both dimensions
            self.dominance_status = ""
            if abs(self.incremental_qalys) > QALY_THRESHOLD:
                self.icer = self.incremental_costs / self.incremental_qalys
            else:
                self.icer = None  # No meaningful difference in QALYs


def run_cea(
    n_patients: int = 1000,
    time_horizon_years: int = 40,
    seed: Optional[int] = None,
    perspective: str = "US",
    economic_perspective: str = "societal"
) -> CEAResults:
    """
    Run full CEA comparing IXA-001 vs Spironolactone.

    Args:
        n_patients: Number of patients to simulate per arm
        time_horizon_years: Time horizon in years
        seed: Random seed for reproducibility
        perspective: Cost perspective (US or UK)
        economic_perspective: "societal" (includes indirect costs) or
                             "healthcare_system" (direct costs only)

    Returns:
        CEAResults with ICER and incremental analysis
    """
    config = SimulationConfig(
        n_patients=n_patients,
        time_horizon_months=time_horizon_years * 12,
        seed=seed,
        cost_perspective=perspective,
        economic_perspective=economic_perspective
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

    cea = CEAResults(
        intervention=results_ixa,
        comparator=results_spi,
        economic_perspective=economic_perspective
    )
    cea.calculate_icer()

    return cea


def print_cea_results(cea: CEAResults):
    """Print formatted CEA results including renal outcomes."""
    print("\n" + "="*60)
    perspective_label = "Societal" if cea.economic_perspective == "societal" else "Healthcare System"
    print(f"COST-EFFECTIVENESS ANALYSIS RESULTS ({perspective_label} Perspective)")
    print("="*60)

    print(f"\n{'Outcome':<30} {'IXA-001':>15} {'Spironol.':>15}")
    print("-"*60)
    print(f"{'Mean Direct Costs':<30} ${cea.intervention.mean_costs:>14,.0f} ${cea.comparator.mean_costs:>14,.0f}")
    print(f"{'Mean Indirect Costs':<30} ${cea.intervention.mean_indirect_costs:>14,.0f} ${cea.comparator.mean_indirect_costs:>14,.0f}")
    print(f"{'Mean Total Costs':<30} ${cea.intervention.mean_total_costs:>14,.0f} ${cea.comparator.mean_total_costs:>14,.0f}")
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
    print(f"{'New Atrial Fibrillation':<30} {cea.intervention.new_af_events:>15} {cea.comparator.new_af_events:>15}")
    print(f"{'CV Deaths':<30} {cea.intervention.cv_deaths:>15} {cea.comparator.cv_deaths:>15}")
    
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

    # Display dominance status with proper interpretation
    if cea.dominance_status == "dominant":
        print(f"{'Status:':<30} {'DOMINANT':>15}")
        print(f"{'Interpretation:':<30} Intervention is cost-saving with better outcomes")
    elif cea.dominance_status == "dominated":
        print(f"{'Status:':<30} {'DOMINATED':>15}")
        print(f"{'Interpretation:':<30} Intervention is more costly with worse outcomes")
    elif cea.dominance_status == "cost_saving":
        print(f"{'Status:':<30} {'COST-SAVING':>15}")
        if cea.icer is not None:
            print(f"{'Cost per QALY lost:':<30} ${abs(cea.icer):>14,.0f}")
        print(f"{'Interpretation:':<30} Trade-off: Lower costs but fewer QALYs")
    elif cea.icer is not None:
        print(f"{'ICER ($/QALY):':<30} ${cea.icer:>14,.0f}")
        # Add interpretation against common WTP thresholds
        if cea.icer < 50000:
            print(f"{'Interpretation:':<30} Cost-effective at $50K/QALY threshold")
        elif cea.icer < 100000:
            print(f"{'Interpretation:':<30} Cost-effective at $100K/QALY threshold")
        elif cea.icer < 150000:
            print(f"{'Interpretation:':<30} Cost-effective at $150K/QALY threshold")
        else:
            print(f"{'Interpretation:':<30} Exceeds common WTP thresholds")
    else:
        print(f"{'ICER:':<30} {'Not calculable':>15}")

    print("="*60 + "\n")
