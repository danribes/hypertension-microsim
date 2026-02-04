"""
PREVENT cardiovascular risk equation implementation.

Based on the 2024 AHA PREVENT equations for 10-year and 30-year
cardiovascular disease risk prediction.

Reference:
Khan SS, et al. Development and Validation of the American Heart Association's 
PREVENT Equations. Circulation. 2024;149(6):430-449.
"""

import numpy as np
from typing import Optional
from enum import Enum


class RiskOutcome(Enum):
    """Available PREVENT risk outcomes."""
    CVD_TOTAL = "cvd_total"  # Total CVD (ASCVD + HF)
    ASCVD = "ascvd"          # Atherosclerotic CVD
    HEART_FAILURE = "hf"     # Heart failure
    MI = "mi"                # Myocardial infarction
    STROKE = "stroke"        # Stroke


# PREVENT model coefficients for 10-year total CVD risk
# Base model (without optional predictors)
PREVENT_COEFFICIENTS = {
    # Female coefficients
    "F": {
        "intercept": -4.890,
        "ln_age": 0.976,
        "ln_sbp": 1.008,
        "bp_treated": 0.162,
        "ln_sbp_x_bp_treated": -0.094,
        "diabetes": 0.626,
        "smoker": 0.499,
        "ln_egfr": -0.478,
        "ln_total_chol": 0.252,
        "ln_hdl_chol": -0.436,
        "ln_bmi": 0.327,
    },
    # Male coefficients
    "M": {
        "intercept": -4.324,
        "ln_age": 0.847,
        "ln_sbp": 0.982,
        "bp_treated": 0.147,
        "ln_sbp_x_bp_treated": -0.082,
        "diabetes": 0.671,
        "smoker": 0.546,
        "ln_egfr": -0.395,
        "ln_total_chol": 0.228,
        "ln_hdl_chol": -0.389,
        "ln_bmi": 0.301,
    }
}

# Baseline survival at 10 years
S0_10_YEAR = {
    "F": 0.9792,
    "M": 0.9712
}


def calculate_prevent_risk(
    age: float,
    sex: str,
    sbp: float,
    bp_treated: bool = True,
    has_diabetes: bool = False,
    is_smoker: bool = False,
    egfr: float = 90.0,
    total_cholesterol: float = 200.0,
    hdl_cholesterol: float = 50.0,
    bmi: float = 28.0,
    uacr: Optional[float] = None,
) -> float:
    """
    Calculate 10-year cardiovascular disease risk using PREVENT equation.
    
    Args:
        age: Age in years (30-79)
        sex: 'M' for male, 'F' for female
        sbp: Systolic blood pressure (mmHg)
        bp_treated: Whether on antihypertensive medication
        has_diabetes: Diabetes status
        is_smoker: Current smoking status
        egfr: Estimated GFR (mL/min/1.73m²)
        total_cholesterol: Total cholesterol (mg/dL)
        hdl_cholesterol: HDL cholesterol (mg/dL)
        bmi: Body mass index (kg/m²)
        uacr: Urine albumin-creatinine ratio (optional, for enhanced model)
    
    Returns:
        10-year CVD risk as probability (0-1)
    """
    # Validate inputs
    sex = sex.upper()
    if sex not in ["M", "F"]:
        raise ValueError(f"Sex must be 'M' or 'F', got {sex}")
    
    # Clamp age to valid range
    age = np.clip(age, 30, 79)
    
    # Get coefficients for sex
    coef = PREVENT_COEFFICIENTS[sex]
    s0 = S0_10_YEAR[sex]
    
    # Calculate log transforms
    ln_age = np.log(age)
    ln_sbp = np.log(sbp)
    ln_egfr = np.log(np.clip(egfr, 15, 120))
    ln_total_chol = np.log(np.clip(total_cholesterol, 100, 400))
    ln_hdl_chol = np.log(np.clip(hdl_cholesterol, 20, 100))
    ln_bmi = np.log(np.clip(bmi, 15, 50))
    
    # Binary conversions
    bp_treated_val = 1.0 if bp_treated else 0.0
    diabetes_val = 1.0 if has_diabetes else 0.0
    smoker_val = 1.0 if is_smoker else 0.0
    
    # Calculate linear predictor
    xb = (
        coef["intercept"] +
        coef["ln_age"] * ln_age +
        coef["ln_sbp"] * ln_sbp +
        coef["bp_treated"] * bp_treated_val +
        coef["ln_sbp_x_bp_treated"] * ln_sbp * bp_treated_val +
        coef["diabetes"] * diabetes_val +
        coef["smoker"] * smoker_val +
        coef["ln_egfr"] * ln_egfr +
        coef["ln_total_chol"] * ln_total_chol +
        coef["ln_hdl_chol"] * ln_hdl_chol +
        coef["ln_bmi"] * ln_bmi
    )
    
    # Optional UACR adjustment (if available)
    if uacr is not None and uacr > 30:
        # Approximate coefficient for elevated UACR
        ln_uacr = np.log(np.clip(uacr, 1, 5000))
        xb += 0.15 * (ln_uacr - np.log(30))  # Relative to normal threshold
    
    # Calculate 10-year risk
    risk = 1 - s0 ** np.exp(xb)
    
    return np.clip(risk, 0.001, 0.999)


def calculate_event_specific_risk(
    total_cvd_risk: float,
    outcome: RiskOutcome
) -> float:
    """
    Decompose total CVD risk into event-specific risks.
    
    Based on observed proportions in epidemiological studies.
    
    Args:
        total_cvd_risk: Total 10-year CVD risk
        outcome: Specific outcome type
    
    Returns:
        10-year risk for specific outcome
    """
    # Approximate proportions of total CVD risk
    RISK_PROPORTIONS = {
        RiskOutcome.MI: 0.30,
        RiskOutcome.STROKE: 0.25,
        RiskOutcome.HEART_FAILURE: 0.25,
        RiskOutcome.ASCVD: 0.55,  # MI + stroke combined
        RiskOutcome.CVD_TOTAL: 1.0
    }
    
    proportion = RISK_PROPORTIONS.get(outcome, 1.0)
    return total_cvd_risk * proportion


def annual_to_monthly_prob(annual_prob: float) -> float:
    """
    Convert annual probability to monthly probability.
    
    Uses the standard formula: p_month = 1 - (1 - p_year)^(1/12)
    
    Args:
        annual_prob: Annual probability (0-1)
        
    Returns:
        Monthly probability (0-1)
    """
    annual_prob = np.clip(annual_prob, 0.0, 0.999)
    return 1 - (1 - annual_prob) ** (1/12)


def ten_year_to_annual_prob(ten_year_prob: float) -> float:
    """
    Convert 10-year probability to annual probability.

    Args:
        ten_year_prob: 10-year probability (0-1)

    Returns:
        Annual probability (0-1)
    """
    ten_year_prob = np.clip(ten_year_prob, 0.0, 0.999)
    return 1 - (1 - ten_year_prob) ** 0.1


def ten_year_to_monthly_prob(ten_year_prob: float) -> float:
    """
    Convert 10-year probability to monthly probability.
    
    Args:
        ten_year_prob: 10-year probability (0-1)
        
    Returns:
        Monthly probability (0-1)
    """
    annual_prob = ten_year_to_annual_prob(ten_year_prob)
    return annual_to_monthly_prob(annual_prob)


def apply_bp_reduction_rr(
    baseline_risk: float,
    sbp_reduction_mmhg: float,
    outcome: RiskOutcome
) -> float:
    """
    Apply relative risk reduction for blood pressure lowering.
    
    Based on meta-analyses of BP trials (Law et al., Ettehad et al.)
    
    Args:
        baseline_risk: Baseline risk (probability)
        sbp_reduction_mmhg: SBP reduction in mmHg (positive = lower BP)
        outcome: Type of CV outcome
    
    Returns:
        Adjusted risk after BP reduction
    """
    # Relative risk per 10 mmHg reduction in SBP
    RR_PER_10_MMHG = {
        RiskOutcome.STROKE: 0.64,        # 36% reduction
        RiskOutcome.MI: 0.78,            # 22% reduction  
        RiskOutcome.HEART_FAILURE: 0.72, # 28% reduction
        RiskOutcome.ASCVD: 0.70,         # ~30% reduction
        RiskOutcome.CVD_TOTAL: 0.75      # ~25% reduction
    }
    
    rr_per_10 = RR_PER_10_MMHG.get(outcome, 0.75)
    
    # Calculate RR for actual reduction
    n_10mmhg = sbp_reduction_mmhg / 10.0
    rr = rr_per_10 ** n_10mmhg
    
    return baseline_risk * rr


class PREVENTRiskCalculator:
    """
    Encapsulates PREVENT risk calculation for use in simulation.
    """
    
    def __init__(self):
        self.cache = {}
    
    def get_cvd_risk(
        self, 
        age: float,
        sex: str,
        sbp: float,
        egfr: float,
        has_diabetes: bool = False,
        is_smoker: bool = False,
        total_cholesterol: float = 200.0,
        hdl_cholesterol: float = 50.0,
        bmi: float = 28.0,
        uacr: Optional[float] = None,
        bp_treated: bool = True
    ) -> float:
        """Calculate 10-year CVD risk."""
        return calculate_prevent_risk(
            age=age,
            sex=sex,
            sbp=sbp,
            bp_treated=bp_treated,
            has_diabetes=has_diabetes,
            is_smoker=is_smoker,
            egfr=egfr,
            total_cholesterol=total_cholesterol,
            hdl_cholesterol=hdl_cholesterol,
            bmi=bmi,
            uacr=uacr
        )
    
    def get_monthly_event_prob(
        self,
        age: float,
        sex: str,
        sbp: float,
        egfr: float,
        outcome: RiskOutcome,
        has_diabetes: bool = False,
        is_smoker: bool = False,
        total_cholesterol: float = 200.0,
        hdl_cholesterol: float = 50.0,
        bmi: float = 28.0,
        prior_event_multiplier: float = 1.0
    ) -> float:
        """
        Calculate monthly probability of a specific CV event.
        
        Args:
            age: Patient age
            sex: 'M' or 'F'
            sbp: Current systolic BP
            egfr: Current eGFR
            outcome: Type of CV event
            has_diabetes: Diabetes status
            is_smoker: Smoking status
            total_cholesterol: Total cholesterol
            hdl_cholesterol: HDL cholesterol
            bmi: BMI
            prior_event_multiplier: Multiplier for prior event history
            
        Returns:
            Monthly probability of the event
        """
        # Get 10-year CVD risk
        ten_year_cvd = self.get_cvd_risk(
            age=age,
            sex=sex,
            sbp=sbp,
            egfr=egfr,
            has_diabetes=has_diabetes,
            is_smoker=is_smoker,
            total_cholesterol=total_cholesterol,
            hdl_cholesterol=hdl_cholesterol,
            bmi=bmi
        )
        
        # Get event-specific risk
        ten_year_event = calculate_event_specific_risk(ten_year_cvd, outcome)
        
        # Apply prior event multiplier
        ten_year_event *= prior_event_multiplier
        
        # Convert to monthly
        return ten_year_to_monthly_prob(ten_year_event)
