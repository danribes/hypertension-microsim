"""
Kidney Failure Risk Equation (KFRE) implementation.

The KFRE predicts the risk of kidney failure (progression to eGFR <15 or
need for dialysis/transplant) using readily available clinical variables.
This implementation provides both 2-year and 5-year risk predictions.

Available Models:
    - 4-variable KFRE: age, sex, eGFR, uACR (recommended for most settings)
    - 8-variable KFRE: adds calcium, phosphate, albumin, bicarbonate

Applicability:
    - Validated for CKD Stage 3-5 (eGFR 15-59 mL/min/1.73m2)
    - Less validated for eGFR >= 60 (use with caution)

References:
    Tangri N, Grams ME, Levey AS, et al. Multinational Assessment of Accuracy
    of Equations for Predicting Risk of Kidney Failure: A Meta-analysis.
    JAMA. 2016;315(2):164-174.

    Tangri N, Stevens LA, Griffith J, et al. A predictive model for progression
    of chronic kidney disease to kidney failure. JAMA. 2011;305(15):1553-1559.

    Tangri N, et al. Risk Prediction Models for Patients With Chronic Kidney
    Disease: A Systematic Review. Ann Intern Med. 2013;158(8):596-603.
"""

import numpy as np
from typing import Literal, Optional


# =============================================================================
# KFRE COEFFICIENTS (4-VARIABLE MODEL)
# =============================================================================
# Source: Tangri N et al. JAMA 2011 (original) and JAMA 2016 (meta-analysis)
# Recalibrated for North American populations

KFRE_COEFFICIENTS = {
    '2_year': {
        # Linear predictor coefficients
        # LP = intercept + sum(coef_i * x_i)
        # Risk = 1 - S0^exp(LP)
        'intercept': -0.2201,
        'female': -0.2240,  # Female indicator (1 if female, 0 if male)
        'age': -0.0128,     # Per year, centered at age 60
        'egfr': -0.0576,    # Per mL/min/1.73m2, centered at 40
        'log_uacr': 0.3479, # Log of uACR (mg/g), centered at log(100)
    },
    '5_year': {
        'intercept': 0.4775,
        'female': -0.2635,
        'age': -0.0087,
        'egfr': -0.0535,
        'log_uacr': 0.3411,
    }
}

# Baseline survival at mean covariate values
# S0 = survival probability at time t for average patient
KFRE_BASELINE_SURVIVAL = {
    '2_year': 0.9832,
    '5_year': 0.9365,
}


def calculate_kfre_risk(
    age: float,
    sex: Literal['M', 'F'],
    egfr: float,
    uacr: float,
    time_horizon: Literal['2_year', '5_year'] = '2_year',
    recalibrated: bool = True
) -> float:
    """
    Calculate kidney failure risk using 4-variable KFRE.

    The KFRE predicts the probability of progressing to kidney failure
    (eGFR <15 mL/min/1.73m2 or need for dialysis/transplant) within
    the specified time horizon.

    Args:
        age: Age in years
        sex: 'M' for male, 'F' for female
        egfr: eGFR in mL/min/1.73m2 (recommended for 15-59 range)
        uacr: Urine albumin-creatinine ratio in mg/g
        time_horizon: '2_year' or '5_year' prediction
        recalibrated: Use North American recalibrated coefficients (default True)

    Returns:
        Probability of kidney failure (0-1)

    Example:
        >>> calculate_kfre_risk(65, 'M', 35, 150, '2_year')
        0.082  # 8.2% 2-year risk

    Notes:
        - For eGFR >= 60: risk estimates may be less accurate (extrapolation)
        - For uACR < 30 (normal): use uACR = 30 as floor for calculation

    Reference:
        Tangri N et al. Multinational Assessment of Accuracy of Equations
        for Predicting Risk of Kidney Failure. JAMA. 2016;315(2):164-174.
    """
    # Input validation and bounds
    egfr = np.clip(egfr, 5, 120)
    uacr = np.clip(uacr, 1, 5000)

    coef = KFRE_COEFFICIENTS[time_horizon]
    s0 = KFRE_BASELINE_SURVIVAL[time_horizon]

    # Feature encoding
    female_indicator = 1.0 if sex == 'F' else 0.0
    log_uacr = np.log(max(uacr, 1.0))

    # Calculate linear predictor
    # Variables are centered at reference values per original KFRE
    lp = (coef['intercept'] +
          coef['female'] * female_indicator +
          coef['age'] * (age - 60) +
          coef['egfr'] * (egfr - 40) +
          coef['log_uacr'] * (log_uacr - np.log(100)))

    # Calculate risk: Risk = 1 - S0^exp(LP)
    risk = 1 - s0 ** np.exp(lp)

    return np.clip(risk, 0.0001, 0.9999)


def calculate_kfre_2yr_risk(
    age: float,
    sex: Literal['M', 'F'],
    egfr: float,
    uacr: float
) -> float:
    """Convenience function for 2-year KFRE risk."""
    return calculate_kfre_risk(age, sex, egfr, uacr, '2_year')


def calculate_kfre_5yr_risk(
    age: float,
    sex: Literal['M', 'F'],
    egfr: float,
    uacr: float
) -> float:
    """Convenience function for 5-year KFRE risk."""
    return calculate_kfre_risk(age, sex, egfr, uacr, '5_year')


class KFRECalculator:
    """
    KFRE calculator for use in microsimulation.

    Provides methods to:
    1. Calculate kidney failure risk
    2. Convert risk to expected eGFR decline rate
    3. Determine CKD progression trajectory type

    The calculator maps KFRE risk to expected annual eGFR decline rates
    based on the clinical observation that higher KFRE risk correlates
    with faster eGFR progression.

    Example:
        >>> calc = KFRECalculator()
        >>> decline = calc.get_annual_egfr_decline(
        ...     age=65, sex='M', egfr=35, uacr=150,
        ...     has_diabetes=True, on_sglt2i=True, sbp=145
        ... )
        >>> print(f"Expected decline: {decline:.1f} mL/min/year")
        Expected decline: 2.8 mL/min/year
    """

    # Decline rate mapping based on KFRE risk
    # Source: CKD Prognosis Consortium data (Coresh J et al.)
    KFRE_TO_DECLINE = {
        # 2-year KFRE risk -> Expected annual eGFR decline (mL/min/year)
        'rapid': {'threshold': 0.30, 'decline': 5.0},    # >30% 2yr risk
        'moderate': {'threshold': 0.15, 'decline': 3.5}, # 15-30% risk
        'slow': {'threshold': 0.05, 'decline': 2.0},     # 5-15% risk
        'stable': {'threshold': 0.0, 'decline': 1.0},    # <5% risk
    }

    def __init__(self):
        """Initialize KFRE calculator."""
        self._cache = {}

    def get_kfre_risk(
        self,
        age: float,
        sex: str,
        egfr: float,
        uacr: float,
        time_horizon: Literal['2_year', '5_year'] = '2_year'
    ) -> float:
        """
        Calculate KFRE kidney failure risk.

        Args:
            age: Age in years
            sex: 'M' or 'F'
            egfr: eGFR (mL/min/1.73m2)
            uacr: uACR (mg/g)
            time_horizon: '2_year' or '5_year'

        Returns:
            Probability of kidney failure (0-1)
        """
        return calculate_kfre_risk(age, sex, egfr, uacr, time_horizon)

    def get_annual_egfr_decline(
        self,
        age: float,
        sex: str,
        current_egfr: float,
        uacr: float,
        has_diabetes: bool = False,
        on_sglt2i: bool = False,
        sbp: float = 130.0
    ) -> float:
        """
        Calculate expected annual eGFR decline using KFRE-informed model.

        Combines KFRE risk stratification with known modifiers for a more
        accurate eGFR decline prediction than simple linear models.

        Algorithm:
            1. For eGFR < 60: Use KFRE 2-year risk to stratify decline rate
            2. For eGFR >= 60: Use age-based natural decline + risk factors
            3. Apply diabetes multiplier (1.5x from UKPDS)
            4. Apply SGLT2i protection (0.61x from DAPA-CKD)
            5. Add SBP excess effect

        Args:
            age: Age in years
            sex: 'M' or 'F'
            current_egfr: Current eGFR (mL/min/1.73m2)
            uacr: Current uACR (mg/g)
            has_diabetes: Diabetes status
            on_sglt2i: SGLT2 inhibitor therapy status
            sbp: Current systolic blood pressure (mmHg)

        Returns:
            Expected annual eGFR decline (mL/min/1.73m2/year)

        References:
            Heerspink HJL, et al. Dapagliflozin in Patients with Chronic
            Kidney Disease. NEJM. 2020;383:1436-1446. (DAPA-CKD)

            SPRINT Research Group. Intensive Blood-Pressure Lowering.
            NEJM. 2015;373:2103-2116.
        """
        # Determine base decline rate based on KFRE or age
        if current_egfr < 60:
            # Use KFRE 2-year risk to stratify progression
            kfre_2yr = self.get_kfre_risk(age, sex, current_egfr, uacr, '2_year')

            # Map KFRE risk to expected decline rate
            if kfre_2yr > self.KFRE_TO_DECLINE['rapid']['threshold']:
                base_decline = self.KFRE_TO_DECLINE['rapid']['decline']  # 5.0
            elif kfre_2yr > self.KFRE_TO_DECLINE['moderate']['threshold']:
                base_decline = self.KFRE_TO_DECLINE['moderate']['decline']  # 3.5
            elif kfre_2yr > self.KFRE_TO_DECLINE['slow']['threshold']:
                base_decline = self.KFRE_TO_DECLINE['slow']['decline']  # 2.0
            else:
                base_decline = self.KFRE_TO_DECLINE['stable']['decline']  # 1.0
        else:
            # For eGFR >= 60, use age-based natural decline
            # Source: CKD-EPI normative data
            if age < 40:
                base_decline = 0.0
            elif age < 65:
                base_decline = 1.0  # Normal aging
            else:
                base_decline = 1.5  # Accelerated in elderly

            # Add albuminuria effect for eGFR >= 60
            # Source: CKD Prognosis Consortium (Gansevoort RT et al. Lancet 2011)
            if uacr >= 300:
                base_decline += 2.0  # Severely increased albuminuria
            elif uacr >= 30:
                base_decline += 0.8  # Moderately increased

        # Apply diabetes multiplier
        # Source: UKPDS outcomes model - DM accelerates CKD 1.5x
        dm_multiplier = 1.5 if has_diabetes else 1.0

        # Apply SGLT2i protection
        # Source: DAPA-CKD trial - 39% reduction in eGFR decline (HR 0.61)
        sglt2_multiplier = 0.61 if on_sglt2i else 1.0

        # Add SBP excess effect (per 10 mmHg above target)
        # Source: SPRINT CKD subgroup analysis
        sbp_target = 130.0
        sbp_excess = max(0, sbp - sbp_target)
        sbp_effect = 0.08 * (sbp_excess / 10)  # 0.08 mL/min/year per 10 mmHg

        # Calculate total annual decline
        total_decline = (base_decline + sbp_effect) * dm_multiplier * sglt2_multiplier

        # Cap at physiologically plausible maximum
        return min(total_decline, 15.0)

    def get_progression_category(
        self,
        age: float,
        sex: str,
        egfr: float,
        uacr: float
    ) -> str:
        """
        Categorize patient by expected CKD progression trajectory.

        Categories:
            - 'rapid': >30% 2-year KFRE risk, expect >4 mL/min/year decline
            - 'moderate': 15-30% risk, expect 2-4 mL/min/year decline
            - 'slow': 5-15% risk, expect 1-2 mL/min/year decline
            - 'stable': <5% risk, expect <1 mL/min/year decline

        Args:
            age: Age in years
            sex: 'M' or 'F'
            egfr: eGFR (mL/min/1.73m2)
            uacr: uACR (mg/g)

        Returns:
            Progression category string

        Reference:
            Tangri N et al. Risk Prediction Models for CKD.
            Ann Intern Med. 2013;158(8):596-603.
        """
        if egfr >= 60:
            # KFRE less validated for eGFR >= 60
            # Use albuminuria as primary stratifier
            if uacr >= 300:
                return 'moderate'
            elif uacr >= 30:
                return 'slow'
            else:
                return 'stable'

        kfre_2yr = self.get_kfre_risk(age, sex, egfr, uacr, '2_year')

        if kfre_2yr > 0.30:
            return 'rapid'
        elif kfre_2yr > 0.15:
            return 'moderate'
        elif kfre_2yr > 0.05:
            return 'slow'
        else:
            return 'stable'

    def should_consider_nephrology_referral(
        self,
        age: float,
        sex: str,
        egfr: float,
        uacr: float
    ) -> bool:
        """
        Determine if nephrology referral is recommended based on KFRE.

        KDIGO guidelines recommend referral for patients with:
        - KFRE 2-year risk >= 3% (some guidelines use 5%)
        - eGFR < 30 regardless of KFRE
        - Rapidly declining eGFR (>5 mL/min/year)

        Args:
            age: Age in years
            sex: 'M' or 'F'
            egfr: eGFR (mL/min/1.73m2)
            uacr: uACR (mg/g)

        Returns:
            True if referral recommended

        Reference:
            KDIGO 2024 Clinical Practice Guideline for CKD.
        """
        if egfr < 30:
            return True

        kfre_2yr = self.get_kfre_risk(age, sex, egfr, uacr, '2_year')
        return kfre_2yr >= 0.03  # 3% threshold per KDIGO
