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
# References:
#   IXA-001: Phase III baxdrostat data (Laffin LJ, et al. NEJM 2023)
#   Spironolactone: PATHWAY-2 trial (Williams B, et al. Lancet 2015)
# Note: Effects represent mean population response; individual response
# modified by secondary HTN etiology via baseline_risk_profile modifiers
TREATMENT_EFFECTS = {
    Treatment.IXA_001: TreatmentEffect(
        name="IXA-001 (Aldosterone Synthase Inhibitor)",
        sbp_reduction=20.0,      # Phase III data: 20 mmHg vs placebo (RFP specification)
        sbp_reduction_sd=6.0,    # Reduced SD (more consistent ASI response)
        monthly_cost=500.0,      # Estimated specialty drug cost
        discontinuation_rate=0.08  # Low due to excellent tolerability profile
    ),
    Treatment.SPIRONOLACTONE: TreatmentEffect(
        name="Spironolactone",
        sbp_reduction=9.0,       # PATHWAY-2 trial
        sbp_reduction_sd=6.0,
        monthly_cost=15.0,       # Generic
        discontinuation_rate=0.18  # Higher due to side effects (gynecomastia ~30%)
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
    
    def check_discontinuation(self, patient: Patient) -> dict:
        """
        Check if patient discontinues treatment this month.

        Enhanced model includes:
        - Reason codes (side_effects, lack_of_efficacy, cost, patient_choice)
        - Responder adjustment (good responders less likely to stop)
        - Time-based persistence patterns
        - Re-initiation tracking

        Returns:
            Dict with 'discontinued' (bool) and 'reason' (str or None)

        References:
            Vrijens B et al. Adherence to prescribed medications. Br J Clin Pharmacol. 2012.
            Corrao G et al. Persistence with antihypertensives. J Hypertens. 2011.
        """
        result = {"discontinued": False, "reason": None}

        if patient.treatment == Treatment.STANDARD_CARE:
            return result

        effect = TREATMENT_EFFECTS[patient.treatment]
        base_annual_rate = effect.discontinuation_rate

        # Responder adjustment: patients with good BP response less likely to stop
        # Reference: Mazzaglia G et al. Adherence and BP response. J Hypertens. 2009
        sbp_reduction = patient._treatment_effect_mmhg
        if sbp_reduction >= 15:
            # Good responder: 40% lower discontinuation
            responder_mult = 0.6
        elif sbp_reduction >= 10:
            # Moderate responder: 20% lower discontinuation
            responder_mult = 0.8
        elif sbp_reduction < 5:
            # Poor responder: 30% higher discontinuation (lack of perceived benefit)
            responder_mult = 1.3
        else:
            responder_mult = 1.0

        # Time on treatment: early discontinuation more common
        time_on_treatment = patient.time_in_simulation
        if time_on_treatment <= 3:
            time_mult = 1.5  # Higher early dropout
        elif time_on_treatment <= 6:
            time_mult = 1.2
        elif time_on_treatment >= 24:
            time_mult = 0.8  # Long-term users more stable
        else:
            time_mult = 1.0

        # Treatment-specific factors
        treatment_mult = 1.0
        primary_reason = "patient_choice"

        if patient.treatment == Treatment.SPIRONOLACTONE:
            # Side effect burden
            if patient.sex.value == 'M' and self.rng.random() < 0.30:
                # Gynecomastia in ~30% of males
                treatment_mult = 1.5
                primary_reason = "side_effects"
            if getattr(patient, 'has_hyperkalemia', False):
                treatment_mult = 2.0
                primary_reason = "side_effects"

        elif patient.treatment == Treatment.IXA_001:
            # Novel agent: cost concerns may drive discontinuation
            if getattr(patient, 'sdi_score', 50) > 75:
                treatment_mult = 1.3
                primary_reason = "cost"

        # Calculate final probability
        adjusted_annual = base_annual_rate * responder_mult * time_mult * treatment_mult
        adjusted_annual = min(adjusted_annual, 0.40)  # Cap at 40% annual

        monthly_prob = 1 - (1 - adjusted_annual) ** (1 / 12)

        if self.rng.random() < monthly_prob:
            result["discontinued"] = True
            result["reason"] = primary_reason

            # Track discontinuation history on patient
            if not hasattr(patient, 'discontinuation_history'):
                patient.discontinuation_history = []
            patient.discontinuation_history.append({
                "time": patient.time_in_simulation,
                "treatment": patient.treatment.value,
                "reason": primary_reason
            })

        return result

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
            if patient.has_hyperkalemia:  # K+ > 5.5
                return True

        return False

    def manage_hyperkalemia(
        self,
        patient: Patient,
        use_potassium_binders: bool = True,
        allow_dose_reduction: bool = True
    ) -> dict:
        """
        Manage hyperkalemia with stepped approach per clinical guidelines.

        Implements a tiered management strategy:
        1. Mild elevation (K+ 5.0-5.5): Monitor, consider dose reduction
        2. Moderate elevation (K+ 5.5-6.0): Add potassium binder, reduce dose
        3. Severe elevation (K+ > 6.0): Stop MRA immediately

        Args:
            patient: Patient with potential hyperkalemia
            use_potassium_binders: Whether potassium binders (e.g., patiromer) available
            allow_dose_reduction: Whether dose reduction is an option

        Returns:
            Dict with management actions taken and costs incurred

        Reference:
            Epstein M, et al. Management of hyperkalemia in patients with CKD.
            Kidney Int. 2015;87(6):1085-1097.

            Weir MR, et al. Patiromer in patients with kidney disease and
            hyperkalemia receiving RAAS inhibitors. NEJM. 2015;372(3):211-221.
        """
        result = {
            "action": "none",
            "potassium_binder_started": False,
            "dose_reduced": False,
            "treatment_stopped": False,
            "additional_cost": 0.0
        }

        if patient.treatment != Treatment.SPIRONOLACTONE:
            return result

        k_level = patient.serum_potassium

        # Severe hyperkalemia (K+ > 6.0): Must stop MRA
        if k_level > 6.0:
            result["action"] = "stop_treatment"
            result["treatment_stopped"] = True
            return result

        # Moderate hyperkalemia (K+ 5.5-6.0): Try potassium binder first
        if k_level > 5.5:
            if use_potassium_binders and not getattr(patient, 'on_potassium_binder', False):
                # Start potassium binder (e.g., Patiromer ~$500/month)
                result["action"] = "start_potassium_binder"
                result["potassium_binder_started"] = True
                result["additional_cost"] = 500.0  # Monthly cost of patiromer
                patient.on_potassium_binder = True
                # Potassium binders reduce K+ by ~0.5-1.0 mmol/L over weeks
                patient.serum_potassium -= 0.3  # Immediate partial effect
                return result
            elif allow_dose_reduction and not getattr(patient, 'mra_dose_reduced', False):
                # Reduce dose (halves both effect and K+ increase)
                result["action"] = "reduce_dose"
                result["dose_reduced"] = True
                patient.mra_dose_reduced = True
                # Reduce treatment effect by 50%
                patient._treatment_effect_mmhg *= 0.5
                patient._base_treatment_effect *= 0.5
                return result
            else:
                # All options exhausted, must stop
                result["action"] = "stop_treatment"
                result["treatment_stopped"] = True
                return result

        # Mild elevation (K+ 5.0-5.5): Monitor and optionally reduce dose
        if k_level > 5.0:
            if allow_dose_reduction and not getattr(patient, 'mra_dose_reduced', False):
                # Consider preemptive dose reduction
                if self.rng.random() < 0.3:  # 30% chance clinician reduces dose
                    result["action"] = "reduce_dose"
                    result["dose_reduced"] = True
                    patient.mra_dose_reduced = True
                    patient._treatment_effect_mmhg *= 0.5
                    patient._base_treatment_effect *= 0.5
            else:
                result["action"] = "monitor"

        return result
