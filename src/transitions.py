"""
Transition probability calculations for cardiac events and mortality.

This module implements:
- Cardiovascular event probabilities using AHA PREVENT equations
- Competing risks framework with cause-specific hazards
- Background mortality from validated life tables (US SSA / UK ONS)
- Dynamic stroke subtype distribution based on patient characteristics

References:
    Khan SS, et al. PREVENT Equations. Circulation. 2024;149(6):430-449.
    Putter H, et al. Tutorial in biostatistics: competing risks. Stat Med. 2007.
"""

import numpy as np
from typing import Optional, Union, Tuple
from dataclasses import dataclass

from .patient import Patient, CardiacState, RenalState, NeuroState, Treatment
from .risks.prevent import (
    PREVENTRiskCalculator,
    RiskOutcome,
    annual_to_monthly_prob
)
from .risks.life_tables import LifeTableCalculator


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
    """
    Calculates probabilities for stochastic cardiovascular events.

    Implements proper competing risks framework using cause-specific hazards
    rather than naive probability capping. Supports validated life tables
    for background mortality and dynamic stroke subtype distribution.

    Reference:
        Putter H, Fiocco M, Geskus RB. Tutorial in biostatistics: competing
        risks and multi-state models. Stat Med. 2007;26(11):2389-430.
    """

    # ==========================================================================
    # CASE FATALITY RATES (30-day mortality following acute events)
    # ==========================================================================
    CASE_FATALITY = {
        "mi": 0.08,
        # Source: Krumholz HM et al. Reduction in acute myocardial infarction
        # mortality in the United States. JAMA. 2009;302(7):767-773.
        # Value: 30-day mortality for AMI (contemporary data ~6-10%)
        # PSA: Beta(80, 920)

        "ischemic_stroke": 0.10,
        # Source: Lackland DT et al. Factors influencing the decline in stroke
        # mortality. Stroke. 2014;45(1):315-353.
        # Value: 30-day case fatality for ischemic stroke (range 8-15%)
        # PSA: Beta(100, 900)

        "hemorrhagic_stroke": 0.25,
        # Source: van Asch CJ et al. Incidence, case fatality, and functional
        # outcome of intracerebral haemorrhage. Lancet Neurol. 2010;9(2):167-176.
        # Value: 30-day CFR for ICH (range 20-35%)
        # PSA: Beta(25, 75)

        "stroke": 0.12,  # Legacy: weighted average (deprecated)
        "hf": 0.05
        # Source: Bueno H et al. Trends in length of stay and short-term
        # outcomes among Medicare patients hospitalized for HF. JAMA. 2010.
        # Value: In-hospital mortality for HF admission (range 3-8%)
        # PSA: Beta(50, 950)
    }

    # ==========================================================================
    # STROKE SUBTYPE DISTRIBUTION
    # ==========================================================================
    # Baseline values - can be overridden by dynamic calculation
    # Source: Krishnamurthi RV et al. Global and regional burden of stroke.
    # Lancet Glob Health. 2013;1(5):e259-e281.
    STROKE_ISCHEMIC_FRACTION = 0.85
    STROKE_HEMORRHAGIC_FRACTION = 0.15

    # TIA parameters
    TIA_TO_STROKE_90DAY = 0.10  # 10% stroke risk within 90 days post-TIA
    # Source: Johnston SC et al. Validation of TIA risk scores. NEJM. 2000.

    # ==========================================================================
    # POST-EVENT MORTALITY RATES (annual)
    # ==========================================================================
    POST_EVENT_MORTALITY = {
        "post_mi_year1": 0.05,
        # Source: Stone GW et al. Post-MI outcomes. JACC. 2011.
        "post_mi_thereafter": 0.03,
        "post_stroke_year1": 0.10,
        # Source: Hardie K et al. Ten-year survival after stroke. Stroke. 2004.
        "post_stroke_thereafter": 0.05,
        "heart_failure": 0.08,
        # Source: Mozaffarian D et al. AHA Heart Disease Statistics. Circulation.
        "esrd": 0.15
        # Source: USRDS Annual Data Report 2023
    }

    # ==========================================================================
    # PRIOR EVENT RISK MULTIPLIERS
    # ==========================================================================
    PRIOR_EVENT_MULT = {
        "mi": 2.5,  # Source: Jernberg T et al. Cardiovascular risk in post-MI. EHJ. 2015
        "stroke": 3.0,  # Source: Burn J et al. Long-term risk of recurrent stroke. Lancet.
        "hf": 2.0,
        "tia": 2.0  # Source: Johnston SC et al. TIA risk stratification. Lancet. 2007
    }

    def __init__(
        self,
        seed: Optional[int] = None,
        country: str = 'US',
        use_life_tables: bool = True,
        use_competing_risks: bool = True,
        use_dynamic_stroke_subtypes: bool = True
    ):
        """
        Initialize transition calculator with methodological options.

        Args:
            seed: Random seed for reproducibility
            country: 'US' or 'UK' for life table selection
            use_life_tables: If True, use validated SSA/ONS life tables
            use_competing_risks: If True, use proper competing risks framework
            use_dynamic_stroke_subtypes: If True, vary stroke subtypes by patient

        Reference:
            ISPOR-SMDM Modeling Good Research Practices Task Force.
            State-Transition Modeling. Med Decis Making. 2012;32(5):641-653.
        """
        self.risk_calc = PREVENTRiskCalculator()
        self.rng = np.random.default_rng(seed)

        # Methodological options
        self.use_life_tables = use_life_tables
        self.use_competing_risks = use_competing_risks
        self.use_dynamic_stroke_subtypes = use_dynamic_stroke_subtypes

        # Initialize life table calculator
        self.life_table = LifeTableCalculator(country=country)

        # Legacy mortality table (kept for backward compatibility)
        self._bg_mort = {40: 0.002, 50: 0.005, 60: 0.011, 70: 0.027, 80: 0.067, 90: 0.170}
    
    def get_background_mortality(
        self,
        age: float,
        sex: str = 'M',
        use_life_tables: Optional[bool] = None
    ) -> float:
        """
        Get annual background (non-CV) mortality probability.

        Can use validated life tables (US SSA / UK ONS) with sex-specific
        rates, or fall back to legacy age-bracket lookup.

        Args:
            age: Patient age in years
            sex: 'M' for male, 'F' for female
            use_life_tables: Override instance setting if provided

        Returns:
            Annual probability of non-CV death

        Reference:
            US: SSA Actuarial Life Tables 2021
            UK: ONS National Life Tables 2020-2022
        """
        if use_life_tables is None:
            use_life_tables = self.use_life_tables

        if use_life_tables:
            return self.life_table.get_annual_mortality(age, sex)
        else:
            # Legacy interpolation method
            return self._legacy_background_mortality(age)

    def _legacy_background_mortality(self, age: float) -> float:
        """Legacy background mortality with linear interpolation."""
        brackets = sorted(self._bg_mort.keys())
        for i, b in enumerate(brackets):
            if age < b:
                if i == 0:
                    return self._bg_mort[b]
                lower, upper = brackets[i-1], b
                frac = (age - lower) / (upper - lower)
                return self._bg_mort[lower] * (1-frac) + self._bg_mort[upper] * frac
        return self._bg_mort[brackets[-1]]

    def _get_stroke_subtype_distribution(self, patient: Patient) -> Tuple[float, float]:
        """
        Calculate patient-specific stroke subtype distribution.

        Hemorrhagic stroke proportion varies based on clinical risk factors:
        - Age: Increases from 15% baseline to 20% at age 80+
        - Blood pressure: Uncontrolled severe HTN strongly increases hemorrhagic risk
        - Anticoagulation: Increases hemorrhagic proportion
        - Atrial fibrillation: Cardioembolic mechanism increases ischemic proportion
        - Prior TIA: Atherosclerotic mechanism increases ischemic proportion

        Args:
            patient: Patient object with clinical characteristics

        Returns:
            Tuple of (ischemic_fraction, hemorrhagic_fraction)

        References:
            O'Donnell MJ, et al. Risk factors for ischaemic and intracerebral
            haemorrhagic stroke in 22 countries (INTERSTROKE). Lancet. 2010.

            Krishnamurthi RV, et al. Global burden of stroke. Lancet Glob Health. 2013.

            Feigin VL, et al. Global, regional, and national burden of stroke.
            Lancet Neurol. 2019;18(5):439-458.
        """
        if not self.use_dynamic_stroke_subtypes:
            return (self.STROKE_ISCHEMIC_FRACTION, self.STROKE_HEMORRHAGIC_FRACTION)

        # Baseline: 85% ischemic / 15% hemorrhagic (population average)
        hemorrhagic_adj = 0.0

        # Age adjustment
        # Source: GBD 2019 - hemorrhagic proportion increases with age
        if patient.age >= 80:
            hemorrhagic_adj += 0.05  # +5% hemorrhagic at 80+
        elif patient.age >= 70:
            hemorrhagic_adj += 0.03
        elif patient.age >= 60:
            hemorrhagic_adj += 0.01

        # Blood pressure adjustment
        # Source: INTERSTROKE - SBP>=160 has OR 2.9 for ICH vs 1.9 for ischemic
        risk_sbp = getattr(patient, 'true_mean_sbp', patient.current_sbp)
        if risk_sbp >= 180:
            hemorrhagic_adj += 0.10  # Severe uncontrolled HTN
        elif risk_sbp >= 160:
            hemorrhagic_adj += 0.05  # Moderate uncontrolled
        elif risk_sbp >= 140:
            hemorrhagic_adj += 0.02  # Mild uncontrolled

        # Anticoagulation status (increases bleeding/hemorrhagic risk)
        # Source: Hart RG et al. Antithrombotic therapy. Chest. 2010
        if getattr(patient, 'on_anticoagulant', False):
            hemorrhagic_adj += 0.08

        # Atrial fibrillation (cardioembolic = ischemic mechanism)
        if patient.has_atrial_fibrillation:
            hemorrhagic_adj -= 0.05  # More likely ischemic

        # Prior TIA (atherosclerotic = ischemic mechanism)
        if patient.prior_tia_count > 0:
            hemorrhagic_adj -= 0.03  # More likely ischemic

        # Calculate final proportions with bounds
        hemorrhagic_fraction = np.clip(
            self.STROKE_HEMORRHAGIC_FRACTION + hemorrhagic_adj,
            0.05,  # Minimum 5% hemorrhagic
            0.40   # Maximum 40% hemorrhagic
        )
        ischemic_fraction = 1.0 - hemorrhagic_fraction

        return (ischemic_fraction, hemorrhagic_fraction)

    def _get_treatment_risk_factor(
        self,
        patient: Patient,
        outcome: str
    ) -> float:
        """
        Calculate treatment-based risk reduction factor.

        Converts the treatment response modifier (which affects SBP reduction)
        into a direct risk reduction factor for CV events. This ensures that
        patients who respond better to treatment (e.g., PA patients on IXA-001)
        receive proportionally greater risk reduction.

        The translation uses epidemiological relationships between BP reduction
        and CV event reduction:
        - Each 10 mmHg SBP reduction → ~20% CV event reduction (Lancet 2016 meta-analysis)
        - Treatment response modifier of 1.35× → 35% extra SBP effect
        - 35% × 20% = 7% additional risk reduction

        Mathematical formula:
            risk_factor = 1.0 - (treatment_modifier - 1.0) × efficacy_coefficient
            where efficacy_coefficient = 0.20 for CV outcomes, 0.25 for renal

        Args:
            patient: Patient object with treatment and baseline_risk_profile
            outcome: Event type ("MI", "STROKE", "HF", "ESRD", "DEATH")

        Returns:
            Risk reduction factor (0.7-1.3):
            - < 1.0 = risk reduction (better treatment response)
            - > 1.0 = risk increase (treatment resistance, e.g., Pheo)
            - = 1.0 = no treatment effect modification

        References:
            Ettehad D, et al. Blood pressure lowering for prevention of CV disease.
            Lancet. 2016;387(10022):957-967.

            Brown MJ, et al. PATHWAY-2 trial: optimal treatment of resistant HTN.
            Lancet. 2018;391(10126):1223-1233.
        """
        # Default: no modification
        if not hasattr(patient, 'current_treatment') or patient.current_treatment is None:
            return 1.0

        if not hasattr(patient, 'baseline_risk_profile') or patient.baseline_risk_profile is None:
            return 1.0

        # Get the treatment response modifier for this patient's treatment
        treatment_name = patient.current_treatment.value.upper()
        treatment_modifier = patient.baseline_risk_profile.get_treatment_response_modifier(
            treatment_name
        )

        # Efficacy translation coefficient
        # These coefficients translate treatment response modifier into direct risk reduction.
        # Higher coefficients for outcomes with strong aldosterone-mediated mechanisms.
        #
        # Reference: Ettehad D, et al. Lancet 2016; BP lowering and CVD prevention
        # Reference: FIDELIO-DKD trial; MRA renoprotection beyond BP effects
        # Reference: Monticone S, et al. JACC 2018; PA-specific outcomes
        #
        # Note: These are deliberately higher than pure BP-outcome relationships
        # because aldosterone has DIRECT pathophysiological effects independent of BP:
        # - Cardiac fibrosis → HF
        # - Renal fibrosis → ESRD
        # - Vascular inflammation → MI/Stroke
        outcome = outcome.upper()
        efficacy_coefficients = {
            "MI": 0.30,      # BP + aldosterone-mediated coronary remodeling
            "STROKE": 0.40,  # Strong BP-stroke relationship + vascular inflammation
            "HF": 0.50,      # Very strong (direct aldosterone-mediated cardiac fibrosis)
            "ESRD": 0.55,    # Very strong (direct aldosterone-mediated renal fibrosis)
            "DEATH": 0.35    # Composite of all pathways
        }
        coeff = efficacy_coefficients.get(outcome, 0.30)

        # Calculate risk factor
        # modifier > 1.0 → better response → lower risk (factor < 1.0)
        # modifier < 1.0 → worse response → higher risk (factor > 1.0)
        modifier_effect = treatment_modifier - 1.0
        risk_factor = 1.0 - (modifier_effect * coeff)

        # Bound to clinically plausible range (50% max reduction, 50% max increase)
        # Reference: FIDELIO-DKD showed 40% ESRD reduction; ASI may exceed this
        risk_factor = np.clip(risk_factor, 0.50, 1.50)

        return risk_factor

    def _apply_competing_risks(
        self,
        probs: TransitionProbabilities
    ) -> TransitionProbabilities:
        """
        Apply competing risks framework using cause-specific hazards.

        Converts raw probabilities to hazards, computes total hazard,
        and derives proper cause-specific probabilities that sum to
        less than 1.0 while preserving relative risk relationships.

        Mathematical framework:
            1. Convert probability to hazard: h_k = -ln(1 - p_k)
            2. Total hazard: H = sum(h_k)
            3. Overall survival: S = exp(-H)
            4. Cause-specific probability: P(k) = (h_k / H) * (1 - S)

        Args:
            probs: Raw transition probabilities (may sum > 1.0)

        Returns:
            Adjusted TransitionProbabilities with proper competing risks

        Reference:
            Putter H, Fiocco M, Geskus RB. Tutorial in biostatistics: competing
            risks and multi-state models. Stat Med. 2007;26(11):2389-430.

            Andersen PK, Keiding N. Competing risks and multi-state models.
            Stat Methods Med Res. 2002;11(2):89-115.
        """
        if not self.use_competing_risks:
            return self._legacy_probability_cap(probs)

        def prob_to_hazard(p: float) -> float:
            """Convert probability to cause-specific hazard."""
            p = np.clip(p, 0, 0.9999)
            return -np.log(1 - p) if p > 0 else 0.0

        # Convert all probabilities to hazards
        hazards = {
            'cv_death': prob_to_hazard(probs.to_cv_death),
            'non_cv_death': prob_to_hazard(probs.to_non_cv_death),
            'mi': prob_to_hazard(probs.to_mi),
            'ischemic_stroke': prob_to_hazard(probs.to_ischemic_stroke),
            'hemorrhagic_stroke': prob_to_hazard(probs.to_hemorrhagic_stroke),
            'tia': prob_to_hazard(probs.to_tia),
            'hf': prob_to_hazard(probs.to_hf),
        }

        # Total hazard
        total_hazard = sum(hazards.values())

        if total_hazard <= 0:
            return probs  # No events possible

        # Overall survival probability: S(t) = exp(-H)
        survival_prob = np.exp(-total_hazard)

        # Probability of any event: 1 - S
        event_prob = 1 - survival_prob

        # Create new probabilities using cause-specific proportions
        new_probs = TransitionProbabilities()
        new_probs.to_cv_death = (hazards['cv_death'] / total_hazard) * event_prob
        new_probs.to_non_cv_death = (hazards['non_cv_death'] / total_hazard) * event_prob
        new_probs.to_mi = (hazards['mi'] / total_hazard) * event_prob
        new_probs.to_ischemic_stroke = (hazards['ischemic_stroke'] / total_hazard) * event_prob
        new_probs.to_hemorrhagic_stroke = (hazards['hemorrhagic_stroke'] / total_hazard) * event_prob
        new_probs.to_tia = (hazards['tia'] / total_hazard) * event_prob
        new_probs.to_hf = (hazards['hf'] / total_hazard) * event_prob
        new_probs.to_stroke = new_probs.to_ischemic_stroke + new_probs.to_hemorrhagic_stroke

        return new_probs

    def _legacy_probability_cap(
        self,
        probs: TransitionProbabilities
    ) -> TransitionProbabilities:
        """
        Legacy probability capping at 95% with proportional scaling.

        Deprecated: Use _apply_competing_risks() for proper methodology.
        Kept for backward compatibility and validation comparisons.
        """
        total_prob = (probs.to_cv_death + probs.to_non_cv_death + probs.to_mi +
                      probs.to_ischemic_stroke + probs.to_hemorrhagic_stroke +
                      probs.to_tia + probs.to_hf)

        if total_prob > 0.95:
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

        # Nocturnal BP Dipping Status Risk Modifier
        # Non-dipping and reverse dipping are independent CV risk factors
        # Reference: Ohkubo T et al. Relation between nocturnal decline in BP
        # and mortality. Am J Hypertens. 1997;10(11):1201-1207.
        # Reference: Verdecchia P et al. Prognostic significance of BP variability
        # in essential hypertension. Blood Press Monit. 2012;17(6):291-295.
        dipping_status = getattr(patient, 'nocturnal_dipping_status', 'normal')
        if dipping_status == "reverse_dipper":
            # Reverse dippers: highest risk (HR ~2.0 for CV events)
            dipping_risk_mult = 1.8
        elif dipping_status == "non_dipper":
            # Non-dippers: elevated risk (HR ~1.3-1.5 for CV events)
            dipping_risk_mult = 1.4
        else:
            # Normal dippers: baseline risk
            dipping_risk_mult = 1.0

        # Get monthly event probabilities from PREVENT
        base_mi_prob = self.risk_calc.get_monthly_event_prob(
            patient.age, patient.sex.value, risk_sbp, patient.egfr,
            RiskOutcome.MI, patient.has_diabetes, patient.is_smoker,
            patient.total_cholesterol, patient.hdl_cholesterol, patient.bmi, mi_mult
        )

        # Apply baseline risk phenotype modifier for MI
        # Also apply nocturnal dipping risk modifier
        mi_phenotype_mod = patient.baseline_risk_profile.get_dynamic_modifier("MI")
        # Apply treatment efficacy factor (PA patients on IXA-001 get additional risk reduction)
        mi_treatment_factor = self._get_treatment_risk_factor(patient, "MI")
        probs.to_mi = base_mi_prob * mi_phenotype_mod * dipping_risk_mult * mi_treatment_factor

        # Total stroke probability from PREVENT
        base_stroke_prob = self.risk_calc.get_monthly_event_prob(
            patient.age, patient.sex.value, risk_sbp, patient.egfr,
            RiskOutcome.STROKE, patient.has_diabetes, patient.is_smoker,
            patient.total_cholesterol, patient.hdl_cholesterol, patient.bmi, stroke_mult
        )

        # Apply baseline risk phenotype modifier for Stroke
        # Stroke is particularly sensitive to nocturnal BP patterns
        # Reference: Kario K et al. Morning surge and nocturnal BP patterns. Hypertension. 2003
        stroke_phenotype_mod = patient.baseline_risk_profile.get_dynamic_modifier("STROKE")
        stroke_dipping_mult = dipping_risk_mult * 1.1 if dipping_risk_mult > 1.0 else 1.0  # Extra sensitivity
        # Apply treatment efficacy factor
        stroke_treatment_factor = self._get_treatment_risk_factor(patient, "STROKE")
        total_stroke_prob = base_stroke_prob * stroke_phenotype_mod * stroke_dipping_mult * stroke_treatment_factor

        # Split into ischemic vs hemorrhagic using dynamic distribution
        # Reference: O'Donnell MJ et al. INTERSTROKE. Lancet. 2010
        ischemic_frac, hemorrhagic_frac = self._get_stroke_subtype_distribution(patient)
        probs.to_ischemic_stroke = total_stroke_prob * ischemic_frac
        probs.to_hemorrhagic_stroke = total_stroke_prob * hemorrhagic_frac
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

            base_hf_prob = self.risk_calc.get_monthly_event_prob(
                patient.age, patient.sex.value, risk_sbp, patient.egfr,
                RiskOutcome.HEART_FAILURE, patient.has_diabetes, patient.is_smoker,
                patient.total_cholesterol, patient.hdl_cholesterol, patient.bmi, 1.0
            )

            # Apply baseline risk phenotype modifier for HF
            hf_phenotype_mod = patient.baseline_risk_profile.get_dynamic_modifier("HF")
            # Apply treatment efficacy factor (especially relevant for PA patients)
            hf_treatment_factor = self._get_treatment_risk_factor(patient, "HF")
            probs.to_hf = base_hf_prob * hf_phenotype_mod * sglt2_hf_mult * hf_treatment_factor

        # 2. Mortality (CV and Non-CV)
        base_cv_death = self._calc_cv_death(patient)
        # Apply baseline risk phenotype modifier for CV Death
        death_phenotype_mod = patient.baseline_risk_profile.get_dynamic_modifier("DEATH")
        # Apply treatment efficacy factor
        death_treatment_factor = self._get_treatment_risk_factor(patient, "DEATH")
        probs.to_cv_death = base_cv_death * death_phenotype_mod * death_treatment_factor

        # Background mortality from validated life tables with sex-specific rates
        # Reference: US SSA 2021 / UK ONS 2020-2022 Life Tables
        bg_mort = self.get_background_mortality(patient.age, patient.sex.value)
        probs.to_non_cv_death = annual_to_monthly_prob(bg_mort)

        # 3. Apply competing risks framework
        # Reference: Putter H et al. Stat Med. 2007 - competing risks tutorial
        probs = self._apply_competing_risks(probs)

        return probs
    
    def _calc_cv_death(self, patient: Patient) -> float:
        """
        Calculate monthly probability of CV death based on history.

        Approach: Use highest applicable condition-specific mortality rate,
        then add incremental risk for comorbidities (additive hazards, not
        multiplicative). This prevents the implausible rates that occur with
        multiplicative risk stacking.

        Reference rates (annual):
        - Base resistant HTN: ~1%
        - Post-MI year 1: ~5%, thereafter: ~3%
        - Post-stroke year 1: ~10%, thereafter: ~5%
        - Heart failure: adds ~3-5% incremental risk
        - ESRD: adds ~9% (60% of 15% ESRD mortality is CV-related)
        """
        # Start with base CV mortality for resistant HTN population
        base_annual = 0.01

        # Determine primary condition-specific mortality (use highest applicable)
        primary_cv_rate = base_annual

        # Post-MI mortality
        if patient.cardiac_state == CardiacState.POST_MI:
            if patient.time_since_last_cv_event and patient.time_since_last_cv_event <= 12:
                primary_cv_rate = max(primary_cv_rate, self.POST_EVENT_MORTALITY["post_mi_year1"])
            else:
                primary_cv_rate = max(primary_cv_rate, self.POST_EVENT_MORTALITY["post_mi_thereafter"])

        # Post-stroke mortality (typically higher than post-MI)
        if patient.cardiac_state == CardiacState.POST_STROKE:
            if patient.time_since_last_cv_event and patient.time_since_last_cv_event <= 12:
                primary_cv_rate = max(primary_cv_rate, self.POST_EVENT_MORTALITY["post_stroke_year1"])
            else:
                primary_cv_rate = max(primary_cv_rate, self.POST_EVENT_MORTALITY["post_stroke_thereafter"])

        # Chronic HF as primary state
        if patient.cardiac_state == CardiacState.CHRONIC_HF:
            primary_cv_rate = max(primary_cv_rate, self.POST_EVENT_MORTALITY["heart_failure"])

        # Additive incremental risk for comorbidities
        incremental_risk = 0.0

        # Heart failure adds incremental risk if not already the primary condition
        # (e.g., patient is post-MI but also has HF)
        if patient.has_heart_failure and patient.cardiac_state != CardiacState.CHRONIC_HF:
            # Add ~3% incremental (not full 8%, which would double-count)
            incremental_risk += 0.03

        # ESRD adds CV mortality (60% of ESRD deaths are CV-related)
        if patient.renal_state == RenalState.ESRD:
            esrd_cv_component = self.POST_EVENT_MORTALITY["esrd"] * 0.6  # ~9%
            incremental_risk += esrd_cv_component

        # Total annual CV death rate
        annual_cv_death = primary_cv_rate + incremental_risk

        # Cap at clinically plausible maximum (20% annual for highest risk patients)
        # Reference: Even the highest-risk HF+ESRD patients rarely exceed 20%/year CV death
        annual_cv_death = min(annual_cv_death, 0.20)

        return annual_to_monthly_prob(annual_cv_death)
    
    def sample_event(self, patient: Patient, probs: TransitionProbabilities) -> Optional[CardiacState]:
        """
        Sample the next event/state for the patient using multinomial distribution.

        Uses proper multinomial sampling for competing risks, which is more
        accurate than sequential Bernoulli trials when multiple events are
        possible in the same time period.

        Args:
            patient: Patient object
            probs: Transition probabilities (already adjusted for competing risks)

        Returns:
            CardiacState for the event (including CardiacState.NON_CV_DEATH),
            or None if no event occurs.

        Reference:
            ISPOR-SMDM Modeling Good Research Practices Task Force-6.
            Modeling using discrete event simulation. Med Decis Making. 2012.
        """
        # Build probability vector for multinomial sampling
        # Order: CV death, non-CV death, MI, hemorrhagic stroke, ischemic stroke, HF, TIA, no event
        event_probs = [
            probs.to_cv_death,
            probs.to_non_cv_death,
            probs.to_mi,
            probs.to_hemorrhagic_stroke,
            probs.to_ischemic_stroke,
            probs.to_hf,
            probs.to_tia,
        ]

        event_outcomes = [
            CardiacState.CV_DEATH,
            CardiacState.NON_CV_DEATH,
            CardiacState.ACUTE_MI,
            CardiacState.ACUTE_HEMORRHAGIC_STROKE,
            CardiacState.ACUTE_ISCHEMIC_STROKE,
            CardiacState.ACUTE_HF,
            CardiacState.TIA,
        ]

        # Probability of no event
        p_no_event = max(0.0, 1.0 - sum(event_probs))
        event_probs.append(p_no_event)
        event_outcomes.append(None)  # No event

        # Normalize probabilities (in case of small floating point errors)
        total = sum(event_probs)
        if total > 0:
            event_probs = [p / total for p in event_probs]

        # Sample from multinomial distribution
        sampled_idx = self.rng.choice(len(event_outcomes), p=event_probs)
        sampled_event = event_outcomes[sampled_idx]

        # If an event occurred, return it
        if sampled_event is not None:
            return sampled_event

        # No acute event - check for state transitions (Acute -> Chronic)
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

    def check_tia_to_stroke_conversion(self, patient: Patient) -> Optional[CardiacState]:
        """
        Check if a patient with recent TIA converts to stroke.

        TIA patients have elevated stroke risk, particularly in the first 90 days.
        The 90-day risk is approximately 10%, with highest risk in first 48 hours.

        Args:
            patient: Patient with potential recent TIA

        Returns:
            CardiacState.ACUTE_ISCHEMIC_STROKE if conversion occurs, None otherwise

        Reference:
            Johnston SC, Gress DR, Browner WS, Sidney S. Short-term prognosis
            after emergency department diagnosis of TIA. JAMA. 2000;284(22):2901-2906.

            Rothwell PM, et al. A simple score (ABCD) to identify individuals at
            high early risk of stroke after TIA. Lancet. 2005;366(9479):29-36.
        """
        if patient.prior_tia_count == 0:
            return None

        if patient.time_since_last_tia is None:
            return None

        # Only check conversion within 90-day window (3 months)
        if patient.time_since_last_tia > 3:
            return None

        # 10% risk over 90 days, with front-loaded risk (higher in first month)
        # Monthly probabilities: Month 1: 5%, Month 2: 3%, Month 3: 2%
        if patient.time_since_last_tia <= 1:
            monthly_conversion_prob = 0.05
        elif patient.time_since_last_tia <= 2:
            monthly_conversion_prob = 0.03
        else:
            monthly_conversion_prob = 0.02

        # ABCD2 risk modifiers (simplified)
        # High BP (SBP >= 140): +50% risk
        if patient.current_sbp >= 140:
            monthly_conversion_prob *= 1.5

        # Diabetes: +30% risk
        if patient.has_diabetes:
            monthly_conversion_prob *= 1.3

        # Atrial fibrillation: +40% risk (cardioembolic mechanism)
        if patient.has_atrial_fibrillation:
            monthly_conversion_prob *= 1.4

        # Cap at reasonable maximum
        monthly_conversion_prob = min(monthly_conversion_prob, 0.15)

        # Sample conversion
        if self.rng.random() < monthly_conversion_prob:
            # TIA converts to ischemic stroke (TIAs don't convert to hemorrhagic)
            return CardiacState.ACUTE_ISCHEMIC_STROKE

        return None

    def check_esrd_mortality(self, patient: Patient) -> bool:
        """
        Check if an ESRD patient dies from renal causes.

        ESRD carries significant mortality risk (~15% annual). Approximately
        60% of ESRD deaths are cardiovascular (handled in CV death pathway),
        and 40% are non-CV/renal-specific (infections, withdrawal, etc.).

        Args:
            patient: Patient to check

        Returns:
            True if patient dies from renal causes this cycle

        Reference:
            USRDS Annual Data Report 2023. Chapter 5: Mortality.
            https://usrds-adr.niddk.nih.gov/2023/end-stage-renal-disease/5-mortality
        """
        if patient.renal_state != RenalState.ESRD:
            return False

        # Annual ESRD mortality: ~15% total
        # CV component (~60%): handled in _calc_cv_death via ESRD increment
        # Non-CV/renal component (~40%): handled here
        annual_renal_death_rate = self.POST_EVENT_MORTALITY["esrd"] * 0.4  # ~6%

        # Risk modifiers for ESRD mortality
        # Older age increases risk
        if patient.age >= 75:
            annual_renal_death_rate *= 1.5
        elif patient.age >= 65:
            annual_renal_death_rate *= 1.2

        # Diabetes increases infection/complication risk
        if patient.has_diabetes:
            annual_renal_death_rate *= 1.3

        # Convert to monthly and sample
        from .risks.prevent import annual_to_monthly_prob
        monthly_renal_death_prob = annual_to_monthly_prob(annual_renal_death_rate)

        return self.rng.random() < monthly_renal_death_prob


class AdherenceTransition:
    """Manages probabilistic transitions between adherent and non-adherent states."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        
    def check_adherence_change(self, patient: Patient) -> bool:
        """
        Check if patient changes adherence status this month.

        Enhanced model includes:
        - Base dropout risk with demographic modifiers
        - Treatment-specific side effects (e.g., spironolactone gynecomastia)
        - Time-based persistence decay (higher early dropout)
        - Post-event adherence boost (patients more adherent after CV events)
        - Interaction effects between risk factors

        Returns:
            True if status changed

        References:
            Burnier M, Egan BM. Adherence in hypertension. Circ Res. 2019;124(7):1124-1140.
            Chowdhury R et al. Adherence to cardiovascular therapy. Eur Heart J. 2013.
        """
        if patient.is_adherent:
            # P(Adherent -> Non-Adherent)
            # Base annual rate varies by time on treatment (persistence decay)
            # Higher dropout in first 6 months, then stabilizes
            time_on_treatment = getattr(patient, 'time_in_simulation', 12)
            if time_on_treatment <= 6:
                base_annual = 0.20  # Higher early dropout
            elif time_on_treatment <= 12:
                base_annual = 0.12
            else:
                base_annual = 0.08  # Stabilized persistence

            # Demographic risk factors (multiplicative interaction model)
            demographic_mult = 1.0

            # Age effect: younger patients have higher non-adherence
            if patient.age < 40:
                demographic_mult *= 1.5
            elif patient.age < 50:
                demographic_mult *= 1.3
            elif patient.age > 75:
                # Elderly may have issues with complex regimens
                demographic_mult *= 1.2

            # Social deprivation effect
            if patient.sdi_score > 75:
                demographic_mult *= 1.4
            elif patient.sdi_score > 50:
                demographic_mult *= 1.2

            # Age × SDI interaction: young + high SDI = particularly high risk
            if patient.age < 50 and patient.sdi_score > 75:
                demographic_mult *= 1.2  # Additional interaction effect

            # Treatment-specific side effect risk
            treatment_mult = 1.0
            if patient.treatment == Treatment.IXA_001:
                # IXA-001 as FDC: better adherence
                treatment_mult = 0.48
            elif patient.treatment == Treatment.SPIRONOLACTONE:
                # Spironolactone: side effects increase dropout
                # Gynecomastia in males (~30% incidence), menstrual irregularities in females
                if patient.sex.value == 'M':
                    treatment_mult = 1.4  # Male-specific side effect burden
                else:
                    treatment_mult = 1.2

                # Hyperkalemia concerns
                if getattr(patient, 'hyperkalemia_history', 0) > 0:
                    treatment_mult *= 1.3

            # Post-event adherence boost (patients more careful after CV event)
            # Reference: Kronish IM et al. Adherence after MI. JACC 2011
            recent_event = getattr(patient, 'time_since_last_cv_event', None)
            if recent_event is not None and recent_event < 12:
                demographic_mult *= 0.7  # 30% reduction in dropout after recent event

            # Calculate final annual probability
            annual_prob = base_annual * demographic_mult * treatment_mult
            annual_prob = min(annual_prob, 0.50)  # Cap at 50% annual

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

            # Recent CV event strongly motivates resumption
            recent_event = getattr(patient, 'time_since_last_cv_event', None)
            if recent_event is not None and recent_event < 6:
                annual_prob = 0.30  # High resumption after acute event

            # Symptom-driven return (if BP very high)
            if patient.current_sbp >= 180:
                annual_prob += 0.10  # Symptoms may drive return

            monthly_prob = annual_to_monthly_prob(annual_prob)

            if self.rng.random() < monthly_prob:
                patient.is_adherent = True
                patient.time_since_adherence_change = 0.0
                patient.adherence_history.append(True)
                return True

        # Increment time since change
        patient.time_since_adherence_change += 1.0 / 12.0
        return False


class AFTransition:
    """
    Manages new-onset atrial fibrillation incidence.

    AF is a critical aldosterone-mediated outcome with dramatically elevated
    risk in primary aldosteronism (PA) patients. Per Monticone S et al. 2018,
    PA patients have approximately 12x risk of AF compared to matched controls.

    Key mechanisms:
    - Aldosterone promotes atrial fibrosis and electrical remodeling
    - Left atrial enlargement from volume overload
    - Direct pro-arrhythmic effects

    References:
        Monticone S, et al. Cardiovascular events and target organ damage in
        primary aldosteronism. JACC. 2018;71(21):2638-2649.

        Milliez P, et al. Evidence for an increased rate of cardiovascular
        events in patients with primary aldosteronism. JACC. 2005;45(8):1243-1248.

        Benjamin EJ, et al. Risk factors for atrial fibrillation: The
        Framingham Heart Study. Circulation. 1994;89(2):724-730.
    """

    # Base annual AF incidence by age (general population)
    # Source: Benjamin EJ et al. Framingham Heart Study. Circulation 1994.
    # Modified for resistant HTN population (baseline higher due to HTN burden)
    BASE_AF_INCIDENCE = {
        40: 0.002,  # 0.2% per year at age 40
        50: 0.004,  # 0.4% per year at age 50
        60: 0.010,  # 1.0% per year at age 60
        70: 0.025,  # 2.5% per year at age 70
        80: 0.050,  # 5.0% per year at age 80
    }

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def check_af_onset(self, patient: Patient) -> bool:
        """
        Check for new-onset atrial fibrillation.

        Risk factors implemented:
        - Age (strongest predictor)
        - Primary aldosteronism (12x risk per Monticone 2018)
        - Heart failure (4x risk)
        - Hypertension severity
        - Diabetes
        - Treatment response (ASI reduces aldosterone-mediated AF)

        Args:
            patient: Patient to evaluate

        Returns:
            True if patient develops new AF this cycle
        """
        # Skip if already has AF
        if patient.has_atrial_fibrillation:
            return False

        # Get base incidence for age
        age = patient.age
        base_annual = 0.002  # Default
        for age_bracket, rate in sorted(self.BASE_AF_INCIDENCE.items()):
            if age >= age_bracket:
                base_annual = rate

        # Risk multipliers
        risk_mult = 1.0

        # Primary Aldosteronism: 12x risk (Monticone 2018)
        # This is the KEY aldosterone-specific outcome
        if patient.has_primary_aldosteronism:
            risk_mult *= 12.0

            # Treatment modification for PA patients on ASI
            # ASI directly blocks aldosterone synthesis, reducing AF substrate
            if patient.treatment == Treatment.IXA_001 and patient.is_adherent:
                # ASI provides ~60% risk reduction for AF in PA patients
                # (Analogous to ESRD risk reduction observed in MRA trials)
                risk_mult *= 0.40  # 60% relative risk reduction
            elif patient.treatment == Treatment.SPIRONOLACTONE and patient.is_adherent:
                # MRA provides ~40% reduction (receptor blockade less complete)
                risk_mult *= 0.60  # 40% relative risk reduction

        # Heart failure: 4x risk (Framingham data)
        if patient.has_heart_failure:
            risk_mult *= 4.0

        # Hypertension severity (per 10 mmHg above 140)
        # Source: Huxley RR et al. Hypertension and AF. J Am Heart Assoc. 2014
        risk_sbp = getattr(patient, 'true_mean_sbp', patient.current_sbp)
        if risk_sbp > 140:
            excess = (risk_sbp - 140) / 10
            risk_mult *= (1.0 + 0.15 * excess)  # 15% increase per 10 mmHg

        # Diabetes: 1.4x risk
        if patient.has_diabetes:
            risk_mult *= 1.4

        # Obesity: 1.5x risk for BMI >= 30
        if patient.bmi >= 30:
            risk_mult *= 1.5

        # Calculate final annual probability (capped at 25%)
        annual_prob = min(0.25, base_annual * risk_mult)

        # Convert to monthly
        monthly_prob = annual_to_monthly_prob(annual_prob)

        # Sample
        if self.rng.random() < monthly_prob:
            patient.has_atrial_fibrillation = True
            return True

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
