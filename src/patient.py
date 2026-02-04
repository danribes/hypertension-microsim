"""
Patient class for hypertension microsimulation model.

This module defines the Patient class that tracks individual-level
attributes throughout the simulation, including demographics, clinical
parameters, treatment state, and event history.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from .risk_assessment import BaselineRiskProfile
import numpy as np


class Sex(Enum):
    MALE = "M"
    FEMALE = "F"


class CardiacState(Enum):
    """Cardiac health states."""
    NO_ACUTE_EVENT = "no_acute_event"
    ACUTE_MI = "acute_mi"
    POST_MI = "post_mi"
    # Stroke subtypes (split per Excel model alignment)
    ACUTE_ISCHEMIC_STROKE = "acute_ischemic_stroke"
    ACUTE_HEMORRHAGIC_STROKE = "acute_hemorrhagic_stroke"
    POST_STROKE = "post_stroke"  # Chronic state for both stroke types
    # TIA (Transient Ischemic Attack) - elevated subsequent stroke risk
    TIA = "tia"
    # Legacy stroke states for backward compatibility
    ACUTE_STROKE = "acute_stroke"  # Deprecated: use ACUTE_ISCHEMIC_STROKE
    # Heart failure states
    ACUTE_HF = "acute_hf"        # Acute decompensated HF
    CHRONIC_HF = "chronic_hf"    # Stable HF
    CV_DEATH = "cv_death"


class RenalState(Enum):
    """Renal health states based on CKD stages (KDIGO classification)."""
    CKD_STAGE_1_2 = "ckd_stage_1_2"  # eGFR >= 60
    CKD_STAGE_3A = "ckd_stage_3a"    # eGFR 45-59 (Mild-moderate decrease)
    CKD_STAGE_3B = "ckd_stage_3b"    # eGFR 30-44 (Moderate-severe decrease)
    CKD_STAGE_4 = "ckd_stage_4"      # eGFR 15-29 (Severe decrease)
    ESRD = "esrd"                     # eGFR < 15 / Dialysis
    RENAL_DEATH = "renal_death"       # Death directly from renal failure


class NeuroState(Enum):
    """Neurological/Cognitive health states."""
    NORMAL_COGNITION = "normal_cognition"
    MILD_COGNITIVE_IMPAIRMENT = "mci"
    DEMENTIA = "dementia"


class Treatment(Enum):
    """Treatment options."""
    IXA_001 = "ixa_001"
    SPIRONOLACTONE = "spironolactone"
    STANDARD_CARE = "standard_care"


@dataclass
class Patient:
    """
    Individual patient in the microsimulation.
    
    Tracks all patient-level attributes including concurrent
    cardiac and renal disease states.
    """
    
    # Unique identifier
    patient_id: int
    
    # Demographics
    age: float
    sex: Sex
    
    # Clinical parameters (baseline and current)
    baseline_sbp: float
    baseline_dbp: float
    current_sbp: float
    current_dbp: float
    
    # Renal function
    egfr: float
    uacr: float
    
    # Lipid profile
    total_cholesterol: float
    hdl_cholesterol: float
    
    # Comorbidities and risk factors
    has_diabetes: bool = False
    has_dyslipidemia: bool = False
    is_smoker: bool = False
    bmi: float = 28.0
    
    # Respiratory conditions
    has_copd: bool = False
    copd_severity: Optional[str] = None  # "mild", "moderate", "severe"
    
    # Substance use
    has_substance_use_disorder: bool = False
    substance_type: Optional[str] = None  # "alcohol", "opioids", "stimulants", "poly"
    is_current_alcohol_user: bool = False  # Heavy drinking (>14 drinks/week)
    
    # Mental health
    has_depression: bool = False
    depression_treated: bool = False
    has_anxiety: bool = False
    has_serious_mental_illness: bool = False  # Schizophrenia, bipolar
    
    # Additional CV risk factors
    has_atrial_fibrillation: bool = False
    has_peripheral_artery_disease: bool = False
    
    # Comorbidity burden score
    charlson_score: int = 0  # Calculated at baseline
    
    # Treatment state
    treatment: Treatment = Treatment.STANDARD_CARE
    num_antihypertensives: int = 3
    is_adherent: bool = True
    on_sglt2_inhibitor: bool = False # SGLT2i status (Canagliflozin, Dapagliflozin, etc.)
    
    # Priority 1: Adherence Tracking
    time_since_adherence_change: float = 0.0
    adherence_history: List[bool] = field(default_factory=list)  # Track status changes
    
    # Priority 2: Social Determinants
    sdi_score: float = 50.0  # Social Deprivation Index (0-100, higher is worse)
    
    # Priority 3: Nocturnal Blood Pressure
    nocturnal_sbp: float = 120.0  # mmHg
    nocturnal_dipping_status: str = "normal"  # "normal", "non_dipper", "reverse_dipper"

    # White Coat Hypertension Fields (Priority 4)
    true_mean_sbp: float = field(init=False) # Physiological/Home SBP (used for risk)
    white_coat_effect: float = 0.0 # Error term (Office - True)

    # Option H: Safety Rules (Potassium)
    serum_potassium: float = 4.2  # mmol/L (Normal range 3.5-5.0)
    has_hyperkalemia: bool = False # K+ > 5.5
    hyperkalemia_history: int = 0  # Count of episodes

    # Event history
    prior_mi_count: int = 0
    prior_stroke_count: int = 0
    prior_ischemic_stroke_count: int = 0
    prior_hemorrhagic_stroke_count: int = 0
    prior_tia_count: int = 0
    time_since_last_cv_event: Optional[float] = None
    time_since_last_tia: Optional[float] = None  # TIA → Stroke conversion tracking
    has_heart_failure: bool = False
    
    # Dual-branch state tracking
    cardiac_state: CardiacState = CardiacState.NO_ACUTE_EVENT
    renal_state: RenalState = RenalState.CKD_STAGE_1_2
    neuro_state: NeuroState = NeuroState.NORMAL_COGNITION
    
    # Legacy field for compatibility (optional, usually removed)
    # current_state: HealthState = ... 
    
    # Time tracking
    time_in_cardiac_state: float = 0.0
    time_in_renal_state: float = 0.0
    time_in_neuro_state: float = 0.0
    
    # Cumulative outcomes
    cumulative_costs: float = 0.0
    cumulative_qalys: float = 0.0
    time_in_simulation: float = 0.0
    
    # Event log
    event_history: List[dict] = field(default_factory=list)
    
    # Treatment effect tracking (for dynamic SBP updates)
    _treatment_effect_mmhg: float = 0.0
    _base_treatment_effect: float = 0.0  # Unpenalized effect
    
    # Baseline risk profile (for stratification and subgroup analysis)
    baseline_risk_profile: BaselineRiskProfile = field(default_factory=BaselineRiskProfile)
    
    def __post_init__(self):
        """Initialize current BP from baseline if not set."""
        if self.current_sbp == 0:
            self.current_sbp = self.baseline_sbp
        if self.current_dbp == 0:
            self.current_dbp = self.baseline_dbp
            
        # Initialize True SBP
        # If created manually without effect, assume Office = True
        self.true_mean_sbp = self.current_sbp - self.white_coat_effect
    
    @property
    def is_alive(self) -> bool:
        """Check if patient is alive."""
        return (self.cardiac_state != CardiacState.CV_DEATH and 
                self.renal_state != RenalState.RENAL_DEATH and
                self.cardiac_state != "non_cv_death")  # Handled via flag or state
    
    @property
    def is_bp_controlled(self) -> bool:
        """Check if BP is at target (<140 mmHg SBP)."""
        return self.current_sbp < 140.0
    
    @property
    def has_prior_cv_event(self) -> bool:
        """Check if patient has history of CV events."""
        return (self.prior_mi_count > 0 or 
                self.prior_stroke_count > 0 or 
                self.has_heart_failure)
    
    @property
    def ckd_category(self) -> str:
        """Return CKD category based on eGFR (KDIGO classification)."""
        if self.egfr >= 90: return "G1"
        elif self.egfr >= 60: return "G2"
        elif self.egfr >= 45: return "G3a"
        elif self.egfr >= 30: return "G3b"
        elif self.egfr >= 15: return "G4"
        else: return "G5"
    
    def apply_treatment_effect(self, treatment: Treatment, effect_mmhg: float):
        """Set treatment and cache effect (actual SBP update via update_sbp)."""
        self.treatment = treatment
        self._cached_treatment_effect = effect_mmhg if self.is_adherent else 0
    
    def update_sbp(self, treatment_effect_mmhg: float, rng: np.random.Generator):
        """
        Update SBP with age drift and stochastic variation.
        
        Implements:
        SBP(t+1) = SBP(t) + β_age + ε - treatment_effect
        
        Args:
            treatment_effect_mmhg: Monthly BP reduction from treatment
            rng: Random number generator for stochastic term
        """
        # Age-related increase (0.6 mmHg/year ≈ 0.05 mmHg/month)
        age_drift = 0.05
        
        # Stochastic variation (SD = 2 mmHg monthly)
        epsilon = rng.normal(0, 2.0)
        
        # Update equation
        self.current_sbp = (
            self.current_sbp + 
            age_drift + 
            epsilon - 
            treatment_effect_mmhg
        )
        
        # Update True BP based on new Office BP (maintaining the offset)
        self.true_mean_sbp = self.current_sbp - self.white_coat_effect
        
        # Physiological bounds [90-220 mmHg]
        self.current_sbp = max(90, min(220, self.current_sbp))
        self.true_mean_sbp = max(80, min(210, self.true_mean_sbp))
        
        # Update DBP proportionally (simplified relationship)
        self.current_dbp = self.current_sbp * 0.6
    
    def transition_cardiac(self, new_state: CardiacState):
        """Transition patient to a new cardiac state."""
        self.event_history.append({
            "time": self.time_in_simulation,
            "type": "cardiac",
            "from_state": self.cardiac_state.value,
            "to_state": new_state.value,
            "sbp": self.current_sbp
        })

        if new_state == CardiacState.ACUTE_MI:
            self.prior_mi_count += 1
            self.time_since_last_cv_event = 0
        elif new_state == CardiacState.ACUTE_ISCHEMIC_STROKE:
            self.prior_stroke_count += 1
            self.prior_ischemic_stroke_count += 1
            self.time_since_last_cv_event = 0
        elif new_state == CardiacState.ACUTE_HEMORRHAGIC_STROKE:
            self.prior_stroke_count += 1
            self.prior_hemorrhagic_stroke_count += 1
            self.time_since_last_cv_event = 0
        elif new_state == CardiacState.ACUTE_STROKE:  # Legacy support
            self.prior_stroke_count += 1
            self.time_since_last_cv_event = 0
        elif new_state == CardiacState.TIA:
            self.prior_tia_count += 1
            self.time_since_last_tia = 0
        elif new_state == CardiacState.ACUTE_HF:
            self.has_heart_failure = True

        self.cardiac_state = new_state
        self.time_in_cardiac_state = 0.0

    def transition_renal(self, new_state: RenalState):
        """Transition patient to a new renal state."""
        self.event_history.append({
            "time": self.time_in_simulation,
            "type": "renal",
            "from_state": self.renal_state.value,
            "to_state": new_state.value,
            "egfr": self.egfr
        })
        self.renal_state = new_state
        self.time_in_renal_state = 0.0
        
    def transition_neuro(self, new_state: NeuroState):
        """Transition patient to a new neurological state."""
        self.event_history.append({
            "time": self.time_in_simulation,
            "type": "neuro",
            "from_state": self.neuro_state.value,
            "to_state": new_state.value,
            "sbp": self.current_sbp
        })
        self.neuro_state = new_state
        self.time_in_neuro_state = 0.0
    
    def advance_time(self, months: float = 1.0):
        """Advance simulation time by specified months."""
        self.time_in_simulation += months
        self.time_in_cardiac_state += months
        self.time_in_renal_state += months
        self.time_in_neuro_state += months
        
        if self.time_since_last_cv_event is not None:
            self.time_since_last_cv_event += months
        
        # Age the patient
        self.age += months / 12.0
        
        # Update eGFR with enhanced model
        self._update_egfr(months)
        
        # Update renal state based on new eGFR
        self._update_renal_state_from_egfr()
        
    def _update_egfr(self, months: float):
        """
        Update eGFR with age-stratified decline and BP/diabetes effects.
        
        Based on:
        - MDRD/CKD-EPI natural decline rates
        - Continuous SBP effect (Bakris et al.)
        - Diabetes acceleration (UKPDS)
        
        Args:
            months: Number of months to advance
        """
        # Base decline by age (mL/min/1.73m² per year)
        if self.age < 40:
            base_decline = 0.0
        elif self.age < 65:
            base_decline = 1.0  # Normal aging
        else:
            base_decline = 1.5  # Accelerated in elderly
        
        # SBP effect: Each mmHg > 140 accelerates decline
        sbp_excess = max(0, self.current_sbp - 140)
        sbp_decline = 0.05 * sbp_excess  # 0.05 mL/min/year per mmHg
        
        # Diabetes multiplier (1.5x faster progression)
        dm_multiplier = 1.5 if self.has_diabetes else 1.0
        
        # SGLT2 Inhibitor Protection (DAPA-CKD / EMPA-KIDNEY data)
        # Reduces rate of decline by ~40% (HR ~0.60 for progression)
        sglt2_multiplier = 0.60 if self.on_sglt2_inhibitor else 1.0

        # Baseline risk phenotype modifier for ESRD/renal progression
        # This allows GCUA, EOCRI, and KDIGO phenotypes to influence decline rate
        # Key impact: EOCRI-B (Silent Renal) has 2.0x ESRD risk despite low CV risk
        esrd_phenotype_mod = self.baseline_risk_profile.get_dynamic_modifier("ESRD")

        # Total annual decline
        total_annual_decline = (base_decline + sbp_decline) * dm_multiplier * sglt2_multiplier * esrd_phenotype_mod
        
        # Apply monthly decline
        monthly_decline = total_annual_decline * (months / 12.0)
        self.egfr = max(5, self.egfr - monthly_decline)
        
        # Update Serum Potassium (Option H)
        self._update_potassium(months)
            
    def _update_potassium(self, months: float):
        """
        Update serum potassium levels based on renal function and medication.
        """
        # Base drift (random walk around homeostatic set point)
        # Normal K+ homeostasis is very tight.
        # Drift is higher if eGFR is lower.
        
        drift_sd = 0.1 if self.egfr > 60 else 0.2
        noise = np.random.normal(0, drift_sd)
        
        # Mean tendency
        target_k = 4.2
        if self.egfr < 45: target_k = 4.5
        if self.egfr < 30: target_k = 4.8
        if self.egfr < 15: target_k = 5.2
        
        # MRA Effect (Spironolactone increases K+)
        if self.treatment == Treatment.SPIRONOLACTONE:
            target_k += 0.4 # Mean increase ~0.3-0.5 mmol/L
            
        # Reversion to mean (homeostasis)
        reversion_speed = 0.2
        self.serum_potassium += reversion_speed * (target_k - self.serum_potassium) + noise
        
        # Bounds check
        self.serum_potassium = max(2.5, min(7.0, self.serum_potassium))
        
        # Check Hyperkalemia (> 5.5 mmol/L)
        if self.serum_potassium > 5.5:
            self.has_hyperkalemia = True
        else:
            self.has_hyperkalemia = False
            
    def _update_renal_state_from_egfr(self):
        """Update renal state based on current eGFR (KDIGO thresholds)."""
        if self.renal_state in [RenalState.ESRD, RenalState.RENAL_DEATH]:
            return
            
        new_state = self.renal_state
        if self.egfr < 15:
            new_state = RenalState.ESRD
        elif self.egfr < 30:
            new_state = RenalState.CKD_STAGE_4
        elif self.egfr < 45:
            new_state = RenalState.CKD_STAGE_3B
        elif self.egfr < 60:
            new_state = RenalState.CKD_STAGE_3A
        else:
            new_state = RenalState.CKD_STAGE_1_2
            
        if new_state != self.renal_state:
            self.transition_renal(new_state)
    
    def accrue_costs(self, cost: float):
        """Add costs to cumulative total."""
        self.cumulative_costs += cost
    
    def accrue_qalys(self, qalys: float):
        """Add QALYs to cumulative total."""
        self.cumulative_qalys += qalys
    
    def to_dict(self) -> dict:
        """Convert patient to dictionary for output."""
        return {
            "patient_id": self.patient_id,
            "age": self.age,
            "sex": self.sex.value if hasattr(self.sex, 'value') else self.sex,
            "sbp": self.current_sbp,
            "egfr": self.egfr,
            "treatment": self.treatment.value if hasattr(self.treatment, 'value') else self.treatment,
            "cardiac_state": self.cardiac_state.value if hasattr(self.cardiac_state, 'value') else self.cardiac_state,
            "renal_state": self.renal_state.value if hasattr(self.renal_state, 'value') else self.renal_state,
            "neuro_state": self.neuro_state.value if hasattr(self.neuro_state, 'value') else self.neuro_state,
            "cumulative_costs": self.cumulative_costs,
            "cumulative_qalys": self.cumulative_qalys
        }


def create_patient_from_params(
    patient_id: int,
    age: float,
    sex: str,
    sbp: float,
    dbp: float = None,
    egfr: float = 75.0,
    uacr: float = 30.0,
    total_chol: float = 200.0,
    hdl_chol: float = 50.0,
    has_diabetes: bool = False,
    is_smoker: bool = False,
    **kwargs
) -> Patient:
    """
    Factory function to create a patient with common defaults.
    
    Args:
        patient_id: Unique identifier
        age: Age in years
        sex: 'M' or 'F'
        sbp: Systolic blood pressure
        dbp: Diastolic blood pressure (defaults to SBP * 0.6)
        egfr: Estimated GFR
        uacr: Urine albumin-creatinine ratio
        total_chol: Total cholesterol
        hdl_chol: HDL cholesterol
        has_diabetes: Diabetes status
        is_smoker: Smoking status
        **kwargs: Additional patient attributes
    
    Returns:
        Configured Patient instance
    """
    if dbp is None:
        dbp = sbp * 0.6
    
    sex_enum = Sex.MALE if sex.upper() == 'M' else Sex.FEMALE
    
    return Patient(
        patient_id=patient_id,
        age=age,
        sex=sex_enum,
        baseline_sbp=sbp,
        baseline_dbp=dbp,
        current_sbp=sbp,
        current_dbp=dbp,
        egfr=egfr,
        uacr=uacr,
        total_cholesterol=total_chol,
        hdl_cholesterol=hdl_chol,
        has_diabetes=has_diabetes,
        is_smoker=is_smoker,
        **kwargs
    )
