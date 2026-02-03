"""
Transition probability calculations for cardiac events and mortality.
"""

import numpy as np
from typing import Optional, Union
from dataclasses import dataclass

from .patient import Patient, CardiacState, RenalState, NeuroState, Treatment
from typing import Tuple
from .risks.prevent import (
    PREVENTRiskCalculator, 
    RiskOutcome, 
    annual_to_monthly_prob
)


@dataclass
class TransitionProbabilities:
    """Container for event probabilities."""
    to_mi: float = 0.0
    to_ischemic_stroke: float = 0.0
    to_hemorrhagic_stroke: float = 0.0
    to_tia: float = 0.0
    to_stroke: float = 0.0  # Legacy: total stroke (ischemic + hemorrhagic)
    to_hf: float = 0.0
    to_cv_death: float = 0.0
    to_non_cv_death: float = 0.0


class TransitionCalculator:
    """Calculates probabilities for stochastic events."""

    # Case fatality rates (30-day mortality) - aligned with Excel model
    CASE_FATALITY = {
        "mi": 0.08,
        "ischemic_stroke": 0.10,      # Excel: ~10%
        "hemorrhagic_stroke": 0.25,   # Excel: ~25% (much higher)
        "stroke": 0.12,               # Legacy: weighted average
        "hf": 0.05
    }

    # Stroke subtype distribution (of all strokes)
    # ~85% ischemic, ~15% hemorrhagic (epidemiological data)
    STROKE_ISCHEMIC_FRACTION = 0.85
    STROKE_HEMORRHAGIC_FRACTION = 0.15

    # TIA parameters
    TIA_TO_STROKE_90DAY = 0.10  # 10% stroke risk within 90 days post-TIA

    POST_EVENT_MORTALITY = {
        "post_mi_year1": 0.05, "post_mi_thereafter": 0.03,
        "post_stroke_year1": 0.10, "post_stroke_thereafter": 0.05,
        "heart_failure": 0.08, "esrd": 0.15
    }

    PRIOR_EVENT_MULT = {"mi": 2.5, "stroke": 3.0, "hf": 2.0, "tia": 2.0}
    
    def __init__(self, seed: Optional[int] = None):
        self.risk_calc = PREVENTRiskCalculator()
        self.rng = np.random.default_rng(seed)
        self._bg_mort = {40: 0.002, 50: 0.005, 60: 0.011, 70: 0.027, 80: 0.067, 90: 0.170}
    
    def get_background_mortality(self, age: float) -> float:
        brackets = sorted(self._bg_mort.keys())
        for i, b in enumerate(brackets):
            if age < b:
                if i == 0: return self._bg_mort[b]
                lower, upper = brackets[i-1], b
                frac = (age - lower) / (upper - lower)
                return self._bg_mort[lower] * (1-frac) + self._bg_mort[upper] * frac
        return self._bg_mort[brackets[-1]]
    
    def calculate_transitions(self, patient: Patient) -> TransitionProbabilities:
        probs = TransitionProbabilities()
        if not patient.is_alive: return probs

        # Acute event case fatality (immediate death risk)
        if patient.cardiac_state == CardiacState.ACUTE_MI:
            probs.to_cv_death = self.CASE_FATALITY["mi"]
            return probs
        if patient.cardiac_state == CardiacState.ACUTE_ISCHEMIC_STROKE:
            probs.to_cv_death = self.CASE_FATALITY["ischemic_stroke"]
            return probs
        if patient.cardiac_state == CardiacState.ACUTE_HEMORRHAGIC_STROKE:
            probs.to_cv_death = self.CASE_FATALITY["hemorrhagic_stroke"]
            return probs
        if patient.cardiac_state == CardiacState.ACUTE_STROKE:  # Legacy
            probs.to_cv_death = self.CASE_FATALITY["stroke"]
            return probs
        if patient.cardiac_state == CardiacState.ACUTE_HF:
            probs.to_cv_death = self.CASE_FATALITY["hf"]
            return probs

        # 1. New Cardiac Events (MI, Stroke subtypes, TIA, HF)
        mi_mult = self.PRIOR_EVENT_MULT["mi"] if patient.prior_mi_count > 0 else 1.0
        stroke_mult = self.PRIOR_EVENT_MULT["stroke"] if patient.prior_stroke_count > 0 else 1.0

        # TIA increases stroke risk significantly
        if patient.prior_tia_count > 0:
            stroke_mult *= self.PRIOR_EVENT_MULT["tia"]

        # Use True Mean SBP (Physiological) for risk calculations if available
        # This accounts for White Coat Hypertension modeling
        risk_sbp = getattr(patient, 'true_mean_sbp', patient.current_sbp)

        # Get monthly event probabilities from PREVENT
        probs.to_mi = self.risk_calc.get_monthly_event_prob(
            patient.age, patient.sex.value, risk_sbp, patient.egfr,
            RiskOutcome.MI, patient.has_diabetes, patient.is_smoker,
            patient.total_cholesterol, patient.hdl_cholesterol, patient.bmi, mi_mult
        )

        # Total stroke probability from PREVENT
        total_stroke_prob = self.risk_calc.get_monthly_event_prob(
            patient.age, patient.sex.value, risk_sbp, patient.egfr,
            RiskOutcome.STROKE, patient.has_diabetes, patient.is_smoker,
            patient.total_cholesterol, patient.hdl_cholesterol, patient.bmi, stroke_mult
        )

        # Split into ischemic vs hemorrhagic (epidemiological distribution)
        probs.to_ischemic_stroke = total_stroke_prob * self.STROKE_ISCHEMIC_FRACTION
        probs.to_hemorrhagic_stroke = total_stroke_prob * self.STROKE_HEMORRHAGIC_FRACTION
        probs.to_stroke = total_stroke_prob  # Legacy total

        # TIA probability (approximately 1/3 of ischemic stroke incidence)
        # TIA risk elevated by hypertension, AF, prior TIA
        tia_base = probs.to_ischemic_stroke * 0.33
        if patient.has_atrial_fibrillation:
            tia_base *= 1.5
        probs.to_tia = tia_base

        if not patient.has_heart_failure:
            # SGLT2i Effect on HF Hospitalization: HR ~0.65-0.70 (DAPA-HF, EMPEROR-Reduced)
            sglt2_hf_mult = 0.70 if patient.on_sglt2_inhibitor else 1.0

            probs.to_hf = self.risk_calc.get_monthly_event_prob(
                patient.age, patient.sex.value, risk_sbp, patient.egfr,
                RiskOutcome.HEART_FAILURE, patient.has_diabetes, patient.is_smoker,
                patient.total_cholesterol, patient.hdl_cholesterol, patient.bmi, 1.0
            ) * sglt2_hf_mult

        # 2. Mortality (CV and Non-CV)
        probs.to_cv_death = self._calc_cv_death(patient)
        probs.to_non_cv_death = annual_to_monthly_prob(self.get_background_mortality(patient.age))

        # 3. CRITICAL FIX: Ensure total probability doesn't exceed 1.0
        # This addresses the 10x CV death rate discrepancy
        total_prob = (probs.to_cv_death + probs.to_non_cv_death + probs.to_mi +
                      probs.to_ischemic_stroke + probs.to_hemorrhagic_stroke +
                      probs.to_tia + probs.to_hf)
        if total_prob > 0.95:  # Cap at 95% to leave room for survival
            scale_factor = 0.95 / total_prob
            probs.to_cv_death *= scale_factor
            probs.to_non_cv_death *= scale_factor
            probs.to_mi *= scale_factor
            probs.to_ischemic_stroke *= scale_factor
            probs.to_hemorrhagic_stroke *= scale_factor
            probs.to_tia *= scale_factor
            probs.to_hf *= scale_factor
            probs.to_stroke = probs.to_ischemic_stroke + probs.to_hemorrhagic_stroke

        return probs
    
    def _calc_cv_death(self, patient: Patient) -> float:
        """
        Calculate monthly probability of CV death based on history.

        CRITICAL FIX: This method was producing rates ~10x higher than Excel model.
        Changes made:
        1. Use multiplicative (not additive) risk stacking for competing conditions
        2. Cap maximum annual CV mortality at clinically plausible levels
        3. Ensure mutual exclusivity with other death pathways
        """
        # Base annual CV mortality for resistant HTN population (~1-2%)
        # Aligned with Excel model baseline of ~0.0008/month = ~1%/year
        base_annual = 0.01

        # Risk multipliers (multiplicative, not additive)
        risk_mult = 1.0

        # Cardiac history multipliers
        if patient.cardiac_state == CardiacState.POST_MI:
            # Higher risk in first year (Year 1: ~5%, Year 2+: ~3%)
            if patient.time_since_last_cv_event and patient.time_since_last_cv_event <= 12:
                risk_mult *= (self.POST_EVENT_MORTALITY["post_mi_year1"] / base_annual)
            else:
                risk_mult *= (self.POST_EVENT_MORTALITY["post_mi_thereafter"] / base_annual)

        if patient.cardiac_state == CardiacState.POST_STROKE:
            if patient.time_since_last_cv_event and patient.time_since_last_cv_event <= 12:
                risk_mult *= (self.POST_EVENT_MORTALITY["post_stroke_year1"] / base_annual)
            else:
                risk_mult *= (self.POST_EVENT_MORTALITY["post_stroke_thereafter"] / base_annual)

        if patient.has_heart_failure or patient.cardiac_state == CardiacState.CHRONIC_HF:
            risk_mult *= (self.POST_EVENT_MORTALITY["heart_failure"] / base_annual)

        # Renal state multiplier (60% of ESRD deaths are CV)
        if patient.renal_state == RenalState.ESRD:
            esrd_cv_annual = self.POST_EVENT_MORTALITY["esrd"] * 0.6
            risk_mult *= (1.0 + esrd_cv_annual / base_annual)

        # Calculate annual CV death probability
        ann = base_annual * risk_mult

        # CRITICAL: Cap at clinically plausible maximum (25% annual for highest risk)
        # This prevents the 10x overestimation issue
        ann = min(ann, 0.25)

        return annual_to_monthly_prob(ann)
    
    def sample_event(self, patient: Patient, probs: TransitionProbabilities) -> Optional[CardiacState]:
        """
        Sample the next event/state for the patient.
        Returns the new CardiacState (or CV death) if an event occurs.
        Non-CV death is handled via a special check in simulation or here.
        """
        # Competing risks - order matters (death first, then severe events, then mild)
        events = [
            (probs.to_cv_death, CardiacState.CV_DEATH),
            (probs.to_non_cv_death, "NON_CV_DEATH"),  # Special flag
            (probs.to_mi, CardiacState.ACUTE_MI),
            (probs.to_hemorrhagic_stroke, CardiacState.ACUTE_HEMORRHAGIC_STROKE),
            (probs.to_ischemic_stroke, CardiacState.ACUTE_ISCHEMIC_STROKE),
            (probs.to_hf, CardiacState.ACUTE_HF),
            (probs.to_tia, CardiacState.TIA),
        ]

        for prob, result in events:
            if self.rng.random() < prob:
                return result

        # State transitions without acute events (e.g. Acute -> Chronic)
        if patient.cardiac_state == CardiacState.ACUTE_MI:
            return CardiacState.POST_MI
        if patient.cardiac_state == CardiacState.ACUTE_ISCHEMIC_STROKE:
            return CardiacState.POST_STROKE
        if patient.cardiac_state == CardiacState.ACUTE_HEMORRHAGIC_STROKE:
            return CardiacState.POST_STROKE
        if patient.cardiac_state == CardiacState.ACUTE_STROKE:  # Legacy
            return CardiacState.POST_STROKE
        if patient.cardiac_state == CardiacState.ACUTE_HF:
            return CardiacState.CHRONIC_HF
        # TIA transitions back to NO_ACUTE_EVENT (it's transient)
        if patient.cardiac_state == CardiacState.TIA:
            return CardiacState.NO_ACUTE_EVENT

        return None


class AdherenceTransition:
    """Manages probabilistic transitions between adherent and non-adherent states."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        
    def check_adherence_change(self, patient: Patient) -> bool:
        """
        Check if patient changes adherence status this month.
        Returns: True if status changed.
        """
        if patient.is_adherent:
            # P(Adherent -> Non-Adherent)
            # Base annual rate = 0.10
            annual_prob = 0.10
            
            # Risk factors for dropping adherence
            if patient.age < 50:
                annual_prob += 0.10
            if patient.sdi_score > 75:
                annual_prob += 0.10
                
            # Delivery Mechanism "Attractiveness" Modifier
            # Based on Path Coefficients: FDC (0.817) vs Monotherapy (0.389)
            # Higher coefficient = more attractive = lower dropout
            # Relative Risk of dropout = 0.389 / 0.817 = ~0.48 for FDC
            
            if patient.treatment == Treatment.IXA_001:
                # Assuming IXA-001 is a Single Pill Combination (FDC)
                annual_prob *= 0.48
            elif patient.treatment == Treatment.SPIRONOLACTONE:
                # Spironolactone is typically an add-on pill (Monotherapy regimen complexity)
                pass # Base rate applies
                
            monthly_prob = annual_to_monthly_prob(annual_prob)
            
            if self.rng.random() < monthly_prob:
                patient.is_adherent = False
                patient.time_since_adherence_change = 0.0
                patient.adherence_history.append(False)
                return True
                
        else:
            # P(Non-Adherent -> Adherent)
            # Base annual rate = 0.05 (spontaneous resumption)
            annual_prob = 0.05
            
            # Interventions could increase this (e.g. digital health)
            # Future placeholder: if patient.intervention == "digital": annual_prob += 0.20
            
            monthly_prob = annual_to_monthly_prob(annual_prob)
            
            if self.rng.random() < monthly_prob:
                patient.is_adherent = True
                patient.time_since_adherence_change = 0.0
                patient.adherence_history.append(True)
                return True
                
        # Increment time since change
        patient.time_since_adherence_change += 1.0/12.0
        return False


class NeuroTransition:
    """
    Manages progression of cognitive decline (Normal -> MCI -> Dementia).
    Based on SPRINT-MIND and 2025 ACC/AHA Guidelines.
    Major Risk Factors: Age (Driver), Uncontrolled SBP (Accelerator).
    """
    
    # Annual transition rates (approximate baseline for healthy)
    # Calibrated to approx 10% Dementia prevalence at age 80
    BASE_RATES = {
        "normal_to_mci": 0.02,
        "mci_to_dementia": 0.10,
        "normal_to_dementia": 0.005 # Direct conversion (rare)
    }
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        
    def check_neuro_progression(self, patient: Patient) -> None:
        """
        Check for cognitive state changes.
        """
        if patient.neuro_state == NeuroState.DEMENTIA:
            return  # End state
            
        # 1. Calculate Risk Multipliers
        # Age Multiplier (Doubles every 5 years after 65)
        age_mult = 1.0
        if patient.age > 65:
            age_steps = (patient.age - 65) / 5
            age_mult = 2.0 ** age_steps
            
        # BP Multiplier (SPRINT-MIND: HR ~1.19 for intensive vs standard)
        # We model this as increasing risk for every 10mmHg > 120
        # CRITICAL: Use True Physiological BP (risk_sbp) not White Coat Office BP
        risk_sbp = getattr(patient, 'true_mean_sbp', patient.current_sbp)
        
        bp_mult = 1.0
        if risk_sbp > 120:
            excess = (risk_sbp - 120) / 10
            bp_mult = 1.0 + (excess * 0.15) # 15% increase per 10mmHg
            
        total_mult = age_mult * bp_mult
        
        # 2. Determine Probabilities based on Current State
        if patient.neuro_state == NeuroState.NORMAL_COGNITION:
            prob_mci = annual_to_monthly_prob(self.BASE_RATES["normal_to_mci"] * total_mult)
            prob_dem = annual_to_monthly_prob(self.BASE_RATES["normal_to_dementia"] * total_mult)
            
            # Sample
            if self.rng.random() < prob_dem:
                patient.transition_neuro(NeuroState.DEMENTIA)
            elif self.rng.random() < prob_mci:
                patient.transition_neuro(NeuroState.MILD_COGNITIVE_IMPAIRMENT)
                
        elif patient.neuro_state == NeuroState.MILD_COGNITIVE_IMPAIRMENT:
            prob_dem = annual_to_monthly_prob(self.BASE_RATES["mci_to_dementia"] * total_mult)
            
            if self.rng.random() < prob_dem:
                patient.transition_neuro(NeuroState.DEMENTIA)
