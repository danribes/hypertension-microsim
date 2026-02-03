"""
Baseline risk assessment algorithms for population stratification.

Implements:
- GCUA phenotype classification (Nelson, Framingham, Bansal)
- KDIGO risk matrix
- Framingham CVD risk score

These assessments are calculated once at baseline for each patient
and used for subgroup analysis. They do NOT modify model dynamics.
"""

from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class RiskInputs:
    """Input variables for risk calculations."""
    age: float
    sex: str  # "male" or "female"
    egfr: float
    uacr: Optional[float]
    sbp: float
    total_chol: float
    hdl_chol: float
    has_diabetes: bool
    is_smoker: bool
    has_cvd: bool
    has_heart_failure: bool
    bmi: Optional[float]
    # New risk factors
    sdi_score: float = 50.0  # Social Deprivation Index (0-100)
    nocturnal_sbp: float = 120.0  # mmHg
    is_on_bp_meds: bool = True


@dataclass
class BaselineRiskProfile:
    """Baseline risk stratification (calculated once at patient generation)."""
    
    # Renal risk (stratification method depends on CKD status)
    renal_risk_type: Literal["GCUA", "KDIGO"] = "KDIGO"
    
    # GCUA fields (for non-CKD, age 60+)
    gcua_phenotype: Optional[str] = None  # "I", "II", "III", "IV", "Moderate", "Low"
    gcua_phenotype_name: Optional[str] = None  # "Accelerated Ager", etc.
    gcua_nelson_risk: Optional[float] = None  # 5-year incident CKD risk %
    gcua_cvd_risk: Optional[float] = None  # 10-year CVD risk %
    gcua_mortality_risk: Optional[float] = None  # 5-year mortality risk %
    
    # KDIGO fields (for CKD patients)
    kdigo_gfr_category: Optional[str] = None  # "G1", "G2", "G3a", "G3b", "G4", "G5"
    kdigo_albuminuria_category: Optional[str] = None  # "A1", "A2", "A3"
    kdigo_risk_level: Optional[str] = None  # "Low", "Moderate", "High", "Very High"
    
    # Cardiovascular risk (all patients)
    framingham_risk: Optional[float] = None  # 10-year CVD risk %
    framingham_category: Optional[str] = None  # "Low", "Borderline", "Intermediate", "High"
    
    # Confidence
    risk_profile_confidence: str = "high"  # "high", "moderate", "low" based on missing data


def calculate_gcua_phenotype(inputs: RiskInputs) -> dict:
    """
    Calculate GCUA phenotype for patients age 60+, eGFR > 60.
    
    Returns:
        {
            'eligible': bool,
            'phenotype': str,  # "I", "II", "III", "IV", "Moderate", "Low"
            'phenotype_name': str,
            'nelson_risk': float,
            'cvd_risk': float,
            'mortality_risk': float,
            'confidence': str
        }
    """
    # Check eligibility
    if inputs.age < 60:
        return {'eligible': False, 'reason': 'Age < 60'}
    if inputs.egfr <= 60:
        return {'eligible': False, 'reason': 'eGFR <= 60 (use KDIGO instead)'}
    
    # Module 1: Nelson/CKD-PC - 5-year incident CKD risk
    nelson_risk = _calculate_nelson_risk(inputs)
    
    # Module 2: Framingham CVD risk (simplified PREVENT alternative)
    cvd_risk = _calculate_framingham_risk(inputs)
    
    # Module 3: Bansal mortality risk
    mortality_risk = _calculate_bansal_mortality(inputs)
    
    # Assign phenotype
    phenotype_info = _assign_phenotype(nelson_risk, cvd_risk, mortality_risk)
    
    # Confidence based on missing data
    missing_count = sum([
        inputs.uacr is None,
        inputs.bmi is None
    ])
    confidence = "high" if missing_count == 0 else ("moderate" if missing_count == 1 else "low")
    
    return {
        'eligible': True,
        'phenotype': phenotype_info['type'],
        'phenotype_name': phenotype_info['name'],
        'nelson_risk': nelson_risk,
        'cvd_risk': cvd_risk,
        'mortality_risk': mortality_risk,
        'confidence': confidence
    }


def calculate_kdigo_risk(inputs: RiskInputs) -> dict:
    """
    Calculate KDIGO risk matrix for CKD patients.
    
    Returns:
        {
            'gfr_category': str,  # "G1", "G2", "G3a", "G3b", "G4", "G5"
            'albuminuria_category': str,  # "A1", "A2", "A3"
            'risk_level': str,  # "Low", "Moderate", "High", "Very High"
            'confidence': str
        }
    """
    # GFR category
    if inputs.egfr >= 90:
        gfr_cat = "G1"
    elif inputs.egfr >= 60:
        gfr_cat = "G2"
    elif inputs.egfr >= 45:
        gfr_cat = "G3a"
    elif inputs.egfr >= 30:
        gfr_cat = "G3b"
    elif inputs.egfr >= 15:
        gfr_cat = "G4"
    else:
        gfr_cat = "G5"
    
    # Albuminuria category
    if inputs.uacr is not None:
        if inputs.uacr < 30:
            alb_cat = "A1"
        elif inputs.uacr < 300:
            alb_cat = "A2"
        else:
            alb_cat = "A3"
        confidence = "high"
    else:
        alb_cat = "A1"  # Assume normal if missing
        confidence = "low"
    
    # KDIGO risk matrix lookup
    risk_matrix = {
        ("G1", "A1"): "Low", ("G1", "A2"): "Moderate", ("G1", "A3"): "High",
        ("G2", "A1"): "Low", ("G2", "A2"): "Moderate", ("G2", "A3"): "High",
        ("G3a", "A1"): "Moderate", ("G3a", "A2"): "High", ("G3a", "A3"): "Very High",
        ("G3b", "A1"): "High", ("G3b", "A2"): "Very High", ("G3b", "A3"): "Very High",
        ("G4", "A1"): "Very High", ("G4", "A2"): "Very High", ("G4", "A3"): "Very High",
        ("G5", "A1"): "Very High", ("G5", "A2"): "Very High", ("G5", "A3"): "Very High",
    }
    
    risk_level = risk_matrix.get((gfr_cat, alb_cat), "Moderate")
    
    return {
        'gfr_category': gfr_cat,
        'albuminuria_category': alb_cat,
        'risk_level': risk_level,
        'confidence': confidence
    }


def calculate_framingham_risk(inputs: RiskInputs) -> dict:
    """
    Calculate Framingham 10-year CVD risk.
    
    Returns:
        {
            'risk': float,  # Percentage 0-100
            'category': str,  # "Low", "Borderline", "Intermediate", "High"
            'confidence': str
        }
    """
    risk_pct = _calculate_framingham_risk(inputs)
    
    if risk_pct < 5:
        category = "Low"
    elif risk_pct < 7.5:
        category = "Borderline"
    elif risk_pct < 20:
        category = "Intermediate"
    else:
        category = "High"
    
    return {
        'risk': risk_pct,
        'category': category,
        'confidence': "high"
    }


# ============================================
# Internal calculation functions
# ============================================

def _calculate_nelson_risk(inputs: RiskInputs) -> float:
    """Nelson/CKD-PC incident CKD equation (simplified)."""
    baseline = 2.5
    multiplier = 1.0
    
    # Age
    if inputs.age >= 80:
        multiplier *= 3.2
    elif inputs.age >= 75:
        multiplier *= 2.4
    elif inputs.age >= 70:
        multiplier *= 1.8
    elif inputs.age >= 65:
        multiplier *= 1.4
    
    # Sex
    if inputs.sex == "male":
        multiplier *= 1.15
    
    # eGFR
    if inputs.egfr < 75:
        multiplier *= 2.8
    elif inputs.egfr < 90:
        multiplier *= 1.8
    
    # uACR
    if inputs.uacr is not None:
        if inputs.uacr >= 300:
            multiplier *= 4.5
        elif inputs.uacr >= 30:
            multiplier *= 2.5
    
    # Diabetes
    if inputs.has_diabetes:
        multiplier *= 1.7
    
    # CVD
    if inputs.has_cvd:
        multiplier *= 1.8
    
    # Heart Failure
    if inputs.has_heart_failure:
        multiplier *= 2.2
    
    risk = min(baseline * multiplier, 85.0)
    return round(risk, 1)


def _calculate_framingham_risk(inputs: RiskInputs) -> float:
    """Framingham 10-year CVD risk equation."""
    points = 0
    
    # Age points (for males, adjust for females)
    if inputs.sex == "male":
        if inputs.age >= 75:
            points += 15
        elif inputs.age >= 70:
            points += 14
        elif inputs.age >= 65:
            points += 12
        elif inputs.age >= 60:
            points += 11
        elif inputs.age >= 55:
            points += 10
        elif inputs.age >= 50:
            points += 8
        elif inputs.age >= 45:
            points += 6
    else:  # female
        if inputs.age >= 75:
            points += 16
        elif inputs.age >= 70:
            points += 14
        elif inputs.age >= 65:
            points += 12
        elif inputs.age >= 60:
            points += 10
        elif inputs.age >= 55:
            points += 8
    
    # Total cholesterol
    if inputs.total_chol >= 280:
        points += 8
    elif inputs.total_chol >= 240:
        points += 6
    elif inputs.total_chol >= 200:
        points += 5
    elif inputs.total_chol >= 160:
        points += 3
    
    # HDL cholesterol
    if inputs.hdl_chol >= 60:
        points -= 2
    elif inputs.hdl_chol >= 50:
        points -= 1
    elif inputs.hdl_chol < 40:
        points += 1
    
    # SBP (treated)
    if inputs.is_on_bp_meds:
        if inputs.sbp >= 160:
            points += 3
        elif inputs.sbp >= 140:
            points += 2
        elif inputs.sbp >= 130:
            points += 1
        elif inputs.sbp < 120:
            points -= 2
    else:
        if inputs.sbp >= 160:
            points += 3
        elif inputs.sbp >= 140:
            points += 2
        elif inputs.sbp >= 130:
            points += 2
        elif inputs.sbp >= 120:
            points += 1
    
    # Diabetes
    if inputs.has_diabetes:
        points += 3
    
    # Smoking
    if inputs.is_smoker:
        points += 4
        
    # Priority 2: Social Deprivation Index (SDI) correction
    # High deprivation (>75) acts as an independent risk factor
    if inputs.sdi_score > 75:
        points += 3  # Roughly equivalent to diabetes
        
    # Priority 3: Nocturnal Blood Pressure correction
    # Reverse dipping or non-dipping adds risk
    # If nocturnal SBP > 130 (approximate threshold for nocturnal HTN)
    if inputs.nocturnal_sbp > 130:
        points += 2
    
    # Convert points to risk percentage
    risk_lookup = {
        0: 0.5, 1: 0.6, 2: 0.7, 3: 0.8, 4: 0.9,
        5: 1.1, 6: 1.4, 7: 1.6, 8: 1.9, 9: 2.3,
        10: 2.8, 11: 3.3, 12: 3.9, 13: 4.7, 14: 5.6,
        15: 6.7, 16: 7.9, 17: 9.4, 18: 11.2, 19: 13.3,
        20: 15.6, 21: 18.4, 22: 21.6, 23: 25.3, 24: 29.4
    }
    
    if points < 0:
        return 0.5
    elif points >= 24:
        return min(30.0 + (points - 24) * 3, 50.0)
    else:
        return risk_lookup.get(points, 5.0)


def _calculate_bansal_mortality(inputs: RiskInputs) -> float:
    """Bansal geriatric mortality score."""
    points = 0
    
    # Age
    if inputs.age >= 85:
        points += 8
    elif inputs.age >= 80:
        points += 6
    elif inputs.age >= 75:
        points += 4
    elif inputs.age >= 70:
        points += 2
    
    # Sex
    if inputs.sex == "male":
        points += 1
    
    # eGFR
    if inputs.egfr < 60:
        points += 4
    elif inputs.egfr < 75:
        points += 2
    
    # uACR
    if inputs.uacr is not None:
        if inputs.uacr >= 300:
            points += 4
        elif inputs.uacr >= 30:
            points += 2
    
    # Heart Failure
    if inputs.has_heart_failure:
        points += 5
    
    # CVD
    if inputs.has_cvd:
        points += 3
    
    # Diabetes
    if inputs.has_diabetes:
        points += 2
    
    # Convert to risk
    if points <= 5:
        risk = 5 + points * 2
    elif points <= 10:
        risk = 15 + (points - 5) * 5
    elif points <= 15:
        risk = 40 + (points - 10) * 6
    else:
        risk = min(70 + (points - 15) * 4, 95)
    
    return round(risk, 1)


def _assign_phenotype(renal_risk: float, cvd_risk: float, mortality_risk: float) -> dict:
    """Assign GCUA phenotype based on risk scores."""
    # Phenotype IV: The Senescent (takes precedence)
    if mortality_risk >= 50:
        return {'type': 'IV', 'name': 'Senescent'}
    
    # Phenotype I: Accelerated Ager
    if renal_risk >= 15 and cvd_risk >= 20:
        return {'type': 'I', 'name': 'Accelerated Ager'}
    
    # Phenotype II: Silent Renal
    if renal_risk >= 15 and cvd_risk < 7.5:
        return {'type': 'II', 'name': 'Silent Renal'}
    
    # Phenotype III: Vascular Dominant
    if renal_risk < 5 and cvd_risk >= 20:
        return {'type': 'III', 'name': 'Vascular Dominant'}
    
    # Moderate
    if renal_risk >= 5 and renal_risk < 15:
        return {'type': 'Moderate', 'name': 'Moderate Risk'}
    
    # Low
    return {'type': 'Low', 'name': 'Low Risk'}
