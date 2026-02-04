"""
Treatment effects module for hypertension microsimulation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import numpy as np

from .patient import Patient, Treatment
from .risk_assessment import BaselineRiskProfile


@dataclass
class TreatmentEffect:
    """Treatment effect parameters."""
    name: str
    sbp_reduction: float      # Mean SBP reduction (mmHg)
    sbp_reduction_sd: float   # SD of SBP reduction
    monthly_cost: float       # Monthly drug cost (USD)
    discontinuation_rate: float  # Annual discontinuation rate


# Treatment effect data from clinical trials
TREATMENT_EFFECTS = {
    Treatment.IXA_001: TreatmentEffect(
        name="IXA-001 (Aldosterone Synthase Inhibitor)",
        sbp_reduction=20.0,      # Phase III data
        sbp_reduction_sd=8.0,
        monthly_cost=500.0,      # Estimated specialty drug cost
        discontinuation_rate=0.12  # Aligned with Excel model (was 0.08)
    ),
    Treatment.SPIRONOLACTONE: TreatmentEffect(
        name="Spironolactone",
        sbp_reduction=9.0,       # PATHWAY-2 trial
        sbp_reduction_sd=6.0,
        monthly_cost=15.0,       # Generic
        discontinuation_rate=0.15  # Higher due to side effects
    ),
    Treatment.STANDARD_CARE: TreatmentEffect(
        name="Standard Care",
        sbp_reduction=3.0,       # Minimal additional effect
        sbp_reduction_sd=5.0,
        monthly_cost=50.0,       # Background therapy
        discontinuation_rate=0.10
    )
}


class TreatmentManager:
    """Manages treatment assignment and effects."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
    
    def assign_treatment(self, patient: Patient, treatment: Treatment) -> float:
        """
        Assign treatment and return individual SBP reduction.

        Args:
            patient: Patient to treat
            treatment: Treatment to assign

        Returns:
            Individual SBP reduction (mmHg)
        """
        effect = TREATMENT_EFFECTS[treatment]

        # Sample individual treatment response
        sbp_reduction = self.rng.normal(
            effect.sbp_reduction,
            effect.sbp_reduction_sd
        )
        sbp_reduction = max(0, sbp_reduction)  # No negative effect

        # Apply primary aldosteronism treatment response modifier
        # PA patients have enhanced response to aldosterone-targeting therapies
        if hasattr(patient, 'baseline_risk_profile') and patient.baseline_risk_profile is not None:
            treatment_modifier = patient.baseline_risk_profile.get_treatment_response_modifier(
                treatment.value.upper()
            )
            sbp_reduction *= treatment_modifier

        # Store base effect (unpenalized)
        patient._base_treatment_effect = sbp_reduction

        # Apply adherence modifier
        if not patient.is_adherent:
            sbp_reduction *= 0.3  # 70% reduction in effect

        # Apply to patient
        patient.apply_treatment_effect(treatment, sbp_reduction)

        # Store for monthly updates
        patient._treatment_effect_mmhg = sbp_reduction

        return sbp_reduction
        
    def update_effect_for_adherence(self, patient: Patient):
        """
        Recalculate treatment effect based on current adherence status.
        Uses stored base effect.
        """
        effect = patient._base_treatment_effect
        
        if not patient.is_adherent:
            effect *= 0.3
            
        patient._treatment_effect_mmhg = effect
        patient.apply_treatment_effect(patient.treatment, effect)
    
    def get_monthly_effect(self, treatment: Treatment) -> float:
        """
        Get the monthly treatment effect (for use in update_sbp).
        
        Returns:
            Monthly SBP reduction in mmHg
        """
        effect = TREATMENT_EFFECTS[treatment]
        # Monthly effect is approximately annual effect / 12 (simplified)
        # In practice, this would be pre-calculated during assignment
        return effect.sbp_reduction / 12.0
    
    def get_monthly_cost(self, treatment: Treatment) -> float:
        """Get monthly treatment cost."""
        return TREATMENT_EFFECTS[treatment].monthly_cost
    
    def check_discontinuation(self, patient: Patient) -> bool:
        """
        Check if patient discontinues treatment this month.
        
        Returns:
            True if patient discontinues
        """
        if patient.treatment == Treatment.STANDARD_CARE:
            return False
        
        effect = TREATMENT_EFFECTS[patient.treatment]
        monthly_disc_prob = 1 - (1 - effect.discontinuation_rate) ** (1/12)
        
        monthly_disc_prob = 1 - (1 - effect.discontinuation_rate) ** (1/12)
        
        return self.rng.random() < monthly_disc_prob

    def should_intensify_treatment(self, patient: Patient) -> bool:
        """
        Determine if treatment should be intensified.
        Models Clinical Inertia: Providers often fail to act on elevated BP.
        
        2025 ACC/AHA Guideline Rule:
        - If BP > 130/80 after 3-6 months, intensify.
        
        Real-world Inertia:
        - Approx 50% likelihood of NO action despite indication.
        """
        # Clinical Indication (Office BP > 130)
        # Note: Using Office BP (current_sbp) not True BP constraint
        if patient.current_sbp < 130:
            return False
            
        # Clinical Inertia Check
        # 50% probability of failure to act (Inertia)
        if self.rng.random() < 0.50:
            return False # Inertia: No action taken
            
        return True
        
    def check_safety_stop_rules(self, patient: Patient) -> bool:
        """
        Check for safety stopping rules (Option H: Hyperkalemia).
        Returns True if treatment MUST be stopped immediately.
        """
        # Rule: MRA (Spironolactone) must be stopped if K+ > 5.5 mmol/L
        if patient.treatment == Treatment.SPIRONOLACTONE:
            if patient.has_hyperkalemia: # K+ > 5.5
                return True
                
        return False
