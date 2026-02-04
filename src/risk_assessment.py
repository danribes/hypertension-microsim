"""
Baseline risk assessment algorithms for population stratification.

Implements:
- GCUA phenotype classification (Nelson, Framingham, Bansal) - Age ≥60
- EOCRI phenotype classification (PREVENT-based) - Age 18-59
- KDIGO risk matrix
- Framingham CVD risk score
- PREVENT 30-year/lifetime CVD risk score

The model uses a dual-branch age-based risk architecture:
- Age ≥ 60: Route to GCUA (existing logic)
- Age 18-59: Route to EOCRI (new logic for "silent" renal risk)

These assessments are calculated once at baseline for each patient.
They serve two purposes:
1. Subgroup analysis and reporting
2. Dynamic risk modification via phenotype-based multipliers in simulation
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
    # EOCRI-specific inputs
    has_dyslipidemia: bool = False  # For vascular phenotype classification
    has_obesity: bool = False  # BMI ≥ 30 (alternative to raw BMI)


@dataclass
class BaselineRiskProfile:
    """Baseline risk stratification (calculated once at patient generation)."""

    # Renal risk (stratification method depends on age and CKD status)
    # "GCUA" for age 60+, "EOCRI" for age 18-59, "KDIGO" for CKD patients
    renal_risk_type: Literal["GCUA", "EOCRI", "KDIGO"] = "KDIGO"

    # GCUA fields (for non-CKD, age 60+)
    gcua_phenotype: Optional[str] = None  # "I", "II", "III", "IV", "Moderate", "Low"
    gcua_phenotype_name: Optional[str] = None  # "Accelerated Ager", etc.
    gcua_nelson_risk: Optional[float] = None  # 5-year incident CKD risk %
    gcua_cvd_risk: Optional[float] = None  # 10-year CVD risk %
    gcua_mortality_risk: Optional[float] = None  # 5-year mortality risk %

    # EOCRI fields (for non-CKD, age 18-59) - Early-Onset Cardiorenal Risk Indicator
    eocri_phenotype: Optional[str] = None  # "A", "B", "C", "Low"
    eocri_phenotype_name: Optional[str] = None  # "Early Metabolic", "Silent Renal", etc.
    eocri_prevent_risk: Optional[float] = None  # 30-year/lifetime CVD risk % (PREVENT)
    eocri_renal_progression_risk: Optional[str] = None  # "High", "Moderate", "Low"
    eocri_albuminuria_status: Optional[str] = None  # "Elevated" (≥30) or "Normal" (<30)
    eocri_metabolic_burden: Optional[int] = None  # Count of metabolic risk factors (0-4)

    # KDIGO fields (for CKD patients)
    kdigo_gfr_category: Optional[str] = None  # "G1", "G2", "G3a", "G3b", "G4", "G5"
    kdigo_albuminuria_category: Optional[str] = None  # "A1", "A2", "A3"
    kdigo_risk_level: Optional[str] = None  # "Low", "Moderate", "High", "Very High"

    # Cardiovascular risk (all patients)
    framingham_risk: Optional[float] = None  # 10-year CVD risk %
    framingham_category: Optional[str] = None  # "Low", "Borderline", "Intermediate", "High"

    # PREVENT lifetime risk (age 18-59 patients)
    prevent_30yr_risk: Optional[float] = None  # 30-year CVD risk %
    prevent_risk_category: Optional[str] = None  # "Low", "Borderline", "Intermediate", "High"

    # Confidence
    risk_profile_confidence: str = "high"  # "high", "moderate", "low" based on missing data

    def get_dynamic_modifier(self, outcome: str) -> float:
        """
        Calculate outcome-specific risk multiplier based on baseline phenotype.

        This method enables baseline risk stratification to influence simulation
        dynamics by returning multiplicative modifiers for event probabilities.

        Args:
            outcome: Event type - one of:
                "MI" - Myocardial infarction
                "STROKE" - Ischemic/hemorrhagic stroke
                "HF" - Heart failure hospitalization
                "ESRD" - End-stage renal disease progression
                "DEATH" - All-cause mortality

        Returns:
            Multiplicative modifier (0.7-2.5x baseline probability)
            1.0 means no modification from baseline PREVENT calculation

        Clinical Rationale:
            - GCUA-I (Accelerated Ager): Multi-organ decline synergy
            - GCUA-II (Silent Renal): Renal-dominant, CV relatively preserved
            - GCUA-III (Vascular Dominant): Atherosclerotic pathway primary
            - GCUA-IV (Senescent): High competing mortality risk
            - EOCRI-A (Early Metabolic): Metabolic syndrome accelerates both pathways
            - EOCRI-B (Silent Renal): KEY TARGET - low CV but high renal risk
            - EOCRI-C (Premature Vascular): Young atherosclerosis
            - KDIGO levels: Established CKD burden scales risk
        """
        outcome = outcome.upper()
        modifier = 1.0

        # GCUA-based modifiers (age ≥60, eGFR >60)
        if self.renal_risk_type == "GCUA" and self.gcua_phenotype:
            gcua_modifiers = {
                # Phenotype I: Accelerated Ager - high renal + high CVD
                # Multi-organ decline, synergistic damage
                "I": {"MI": 1.3, "STROKE": 1.4, "HF": 1.4, "ESRD": 1.3, "DEATH": 1.5},

                # Phenotype II: Silent Renal - high renal + low CVD
                # Primary renal trajectory, CV relatively protected
                "II": {"MI": 0.9, "STROKE": 0.95, "HF": 1.1, "ESRD": 1.4, "DEATH": 1.2},

                # Phenotype III: Vascular Dominant - low renal + high CVD
                # Atherosclerotic pathway, renal protected
                "III": {"MI": 1.4, "STROKE": 1.5, "HF": 1.2, "ESRD": 0.8, "DEATH": 1.3},

                # Phenotype IV: Senescent - high mortality
                # Frailty, competing risks dominate
                "IV": {"MI": 1.8, "STROKE": 2.0, "HF": 2.2, "ESRD": 1.5, "DEATH": 2.5},

                # Moderate risk
                "Moderate": {"MI": 1.1, "STROKE": 1.1, "HF": 1.15, "ESRD": 1.15, "DEATH": 1.1},

                # Low risk
                "Low": {"MI": 0.9, "STROKE": 0.9, "HF": 0.9, "ESRD": 0.9, "DEATH": 0.85},
            }

            phenotype_mods = gcua_modifiers.get(self.gcua_phenotype, {})
            modifier = phenotype_mods.get(outcome, 1.0)

        # EOCRI-based modifiers (age 18-59, eGFR >60)
        elif self.renal_risk_type == "EOCRI" and self.eocri_phenotype:
            eocri_modifiers = {
                # Type A: Early Metabolic - elevated uACR + diabetes/obesity
                # Metabolic syndrome accelerates both CV and renal damage
                "A": {"MI": 1.2, "STROKE": 1.3, "HF": 1.5, "ESRD": 1.5, "DEATH": 1.4},

                # Type B: Silent Renal - elevated uACR alone (KEY TARGET)
                # Low short-term CV risk but high long-term renal risk
                # Would be missed by Framingham - captures "hidden" renal trajectory
                "B": {"MI": 0.7, "STROKE": 0.75, "HF": 0.9, "ESRD": 2.0, "DEATH": 1.1},

                # Type C: Premature Vascular - normal uACR + high lipids/smoking
                # Young atherosclerosis, renal relatively protected
                "C": {"MI": 1.6, "STROKE": 1.7, "HF": 1.3, "ESRD": 0.8, "DEATH": 1.2},

                # Low risk
                "Low": {"MI": 0.8, "STROKE": 0.8, "HF": 0.85, "ESRD": 0.9, "DEATH": 0.8},
            }

            phenotype_mods = eocri_modifiers.get(self.eocri_phenotype, {})
            modifier = phenotype_mods.get(outcome, 1.0)

        # KDIGO-based modifiers (eGFR ≤60)
        elif self.renal_risk_type == "KDIGO" and self.kdigo_risk_level:
            kdigo_modifiers = {
                # Very High: G4-G5 or severe albuminuria
                # Established advanced CKD, high CV and mortality burden
                "Very High": {"MI": 1.4, "STROKE": 1.5, "HF": 1.6, "ESRD": 1.8, "DEATH": 2.0},

                # High: G3b or moderate-severe albuminuria
                "High": {"MI": 1.2, "STROKE": 1.3, "HF": 1.4, "ESRD": 1.5, "DEATH": 1.5},

                # Moderate: G3a or mild-moderate albuminuria
                "Moderate": {"MI": 1.1, "STROKE": 1.1, "HF": 1.2, "ESRD": 1.2, "DEATH": 1.1},

                # Low: G1-G2 with minimal albuminuria (shouldn't be in KDIGO pathway)
                "Low": {"MI": 0.9, "STROKE": 0.9, "HF": 0.95, "ESRD": 0.95, "DEATH": 0.9},
            }

            risk_mods = kdigo_modifiers.get(self.kdigo_risk_level, {})
            modifier = risk_mods.get(outcome, 1.0)

        # Additional Framingham-based adjustment for all patients
        # High Framingham risk compounds phenotype-specific risk
        if self.framingham_category == "High" and outcome in ["MI", "STROKE", "DEATH"]:
            modifier *= 1.1  # 10% additional increase for high Framingham
        elif self.framingham_category == "Low" and outcome in ["MI", "STROKE"]:
            modifier *= 0.95  # 5% reduction for low Framingham

        return modifier


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


def calculate_eocri_phenotype(inputs: RiskInputs) -> dict:
    """
    Calculate EOCRI (Early-Onset Cardiorenal Risk Indicator) phenotype for
    non-geriatric patients (age 18-59) with preserved eGFR (>60).

    This implements the 2025 AHA/ACC Guidelines recommendation to use PREVENT
    equation for capturing renal and metabolic risk in younger adults.

    Phenotypes:
        Type A (Early Metabolic): Resistant HTN + uACR > 30 + Diabetes/Obesity
            - "Accelerated Ager (Young)" - High lifetime risk for CVD and ESRD
            - Triggers aggressive BP control + SGLT2i + Statin simulation

        Type B (Silent Renal): Resistant HTN + uACR > 30 + No Diabetes/Normal Lipids
            - "Isolated Albuminuric" - Key target for early intervention
            - Low short-term CVD risk but high long-term renal risk
            - Key Value Driver: Triggers early ASI/RAASi use

        Type C (Premature Vascular): Resistant HTN + uACR < 30 + High Lipids/Smoker
            - "Vascular Dominant" - Primary risk is premature MI/Stroke
            - Triggers standard CVD prevention (Statins/Antiplatelets)

    Returns:
        {
            'eligible': bool,
            'phenotype': str,  # "A", "B", "C", "Low"
            'phenotype_name': str,
            'prevent_risk': float,  # 30-year CVD risk %
            'renal_progression_risk': str,  # "High", "Moderate", "Low"
            'albuminuria_status': str,  # "Elevated" or "Normal"
            'metabolic_burden': int,  # Count of metabolic factors
            'confidence': str
        }
    """
    # Check eligibility: Age 18-59, eGFR > 60
    if inputs.age < 18:
        return {'eligible': False, 'reason': 'Age < 18'}
    if inputs.age >= 60:
        return {'eligible': False, 'reason': 'Age >= 60 (use GCUA instead)'}
    if inputs.egfr <= 60:
        return {'eligible': False, 'reason': 'eGFR <= 60 (use KDIGO instead)'}

    # Calculate PREVENT 30-year/lifetime CVD risk
    prevent_risk = _calculate_prevent_30yr_risk(inputs)

    # Assess albuminuria status (key EOCRI discriminator)
    has_elevated_uacr = inputs.uacr is not None and inputs.uacr >= 30
    albuminuria_status = "Elevated" if has_elevated_uacr else "Normal"

    # Calculate metabolic burden score (0-4)
    metabolic_burden = _calculate_metabolic_burden(inputs)

    # Determine renal progression risk based on albuminuria and metabolic factors
    renal_progression_risk = _calculate_renal_progression_risk(inputs, has_elevated_uacr)

    # Assign EOCRI phenotype
    phenotype_info = _assign_eocri_phenotype(
        inputs, has_elevated_uacr, metabolic_burden, prevent_risk
    )

    # Confidence assessment
    missing_count = sum([
        inputs.uacr is None,
        inputs.bmi is None,
    ])
    confidence = "high" if missing_count == 0 else ("moderate" if missing_count == 1 else "low")

    return {
        'eligible': True,
        'phenotype': phenotype_info['type'],
        'phenotype_name': phenotype_info['name'],
        'prevent_risk': prevent_risk,
        'renal_progression_risk': renal_progression_risk,
        'albuminuria_status': albuminuria_status,
        'metabolic_burden': metabolic_burden,
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


# ============================================
# EOCRI Internal calculation functions
# ============================================

def _calculate_prevent_30yr_risk(inputs: RiskInputs) -> float:
    """
    Calculate AHA PREVENT 30-year/lifetime CVD risk for younger adults.

    Based on 2024 AHA PREVENT equation which integrates:
    - Traditional CVD risk factors (SBP, lipids, smoking, diabetes)
    - Cardiovascular-Kidney-Metabolic (CKM) syndrome variables (eGFR, uACR)

    Unlike Framingham, PREVENT explicitly includes renal function as a core
    predictor, making it suitable for identifying "silent" renal risk.

    Reference: Khan SS, et al. Circulation 2024; PREVENT equations.
    """
    # Base 30-year risk by age and sex
    # Younger adults have lower baseline but longer exposure time
    if inputs.sex == "male":
        if inputs.age >= 50:
            base_risk = 18.0
        elif inputs.age >= 40:
            base_risk = 12.0
        elif inputs.age >= 30:
            base_risk = 7.0
        else:
            base_risk = 4.0
    else:  # female
        if inputs.age >= 50:
            base_risk = 12.0
        elif inputs.age >= 40:
            base_risk = 7.0
        elif inputs.age >= 30:
            base_risk = 4.0
        else:
            base_risk = 2.5

    multiplier = 1.0

    # SBP effect (PREVENT weights SBP heavily for lifetime risk)
    if inputs.sbp >= 180:
        multiplier *= 2.8
    elif inputs.sbp >= 160:
        multiplier *= 2.2
    elif inputs.sbp >= 150:
        multiplier *= 1.8
    elif inputs.sbp >= 140:
        multiplier *= 1.5
    elif inputs.sbp >= 130:
        multiplier *= 1.2

    # eGFR effect (CKM integration in PREVENT)
    if inputs.egfr < 75:
        multiplier *= 1.5
    elif inputs.egfr < 90:
        multiplier *= 1.2

    # uACR effect (key differentiator from Framingham)
    if inputs.uacr is not None:
        if inputs.uacr >= 300:
            multiplier *= 2.5
        elif inputs.uacr >= 30:
            multiplier *= 1.7

    # Diabetes (strong lifetime risk factor)
    if inputs.has_diabetes:
        # Diabetes in young adults is particularly impactful
        if inputs.age < 40:
            multiplier *= 2.8
        elif inputs.age < 50:
            multiplier *= 2.2
        else:
            multiplier *= 1.8

    # Lipids
    if inputs.total_chol >= 240:
        multiplier *= 1.4
    elif inputs.total_chol >= 200:
        multiplier *= 1.2

    if inputs.hdl_chol < 40:
        multiplier *= 1.3
    elif inputs.hdl_chol < 50:
        multiplier *= 1.15

    # Smoking (major lifetime impact in young adults)
    if inputs.is_smoker:
        if inputs.age < 40:
            multiplier *= 2.5
        else:
            multiplier *= 2.0

    # BMI/Obesity
    if inputs.bmi is not None:
        if inputs.bmi >= 35:
            multiplier *= 1.6
        elif inputs.bmi >= 30:
            multiplier *= 1.3
        elif inputs.bmi >= 25:
            multiplier *= 1.1

    # Prior CVD (secondary prevention)
    if inputs.has_cvd:
        multiplier *= 2.5

    # Heart failure
    if inputs.has_heart_failure:
        multiplier *= 2.2

    # Social determinants (SDI effect on lifetime risk)
    if inputs.sdi_score > 75:
        multiplier *= 1.3
    elif inputs.sdi_score > 50:
        multiplier *= 1.1

    # Nocturnal hypertension (additional risk in PREVENT)
    if inputs.nocturnal_sbp > 130:
        multiplier *= 1.2

    # Calculate final risk with cap
    risk = min(base_risk * multiplier, 85.0)
    return round(risk, 1)


def _calculate_metabolic_burden(inputs: RiskInputs) -> int:
    """
    Calculate metabolic burden score for EOCRI classification.

    Counts metabolic risk factors (0-4):
    - Diabetes
    - Obesity (BMI >= 30 or has_obesity flag)
    - Dyslipidemia
    - Hypertension (assumed present in resistant HTN population)

    Higher burden indicates Type A (Early Metabolic) phenotype.
    """
    burden = 0

    # Diabetes
    if inputs.has_diabetes:
        burden += 1

    # Obesity
    is_obese = inputs.has_obesity or (inputs.bmi is not None and inputs.bmi >= 30)
    if is_obese:
        burden += 1

    # Dyslipidemia
    if inputs.has_dyslipidemia:
        burden += 1
    elif inputs.total_chol >= 240 or inputs.hdl_chol < 40:
        burden += 1

    # Hypertension - always present in this population (resistant HTN)
    burden += 1

    return min(burden, 4)


def _calculate_renal_progression_risk(inputs: RiskInputs, has_elevated_uacr: bool) -> str:
    """
    Assess renal progression risk for EOCRI.

    Unlike GCUA which uses Nelson equation for 5-year CKD risk,
    EOCRI focuses on current damage markers (uACR) and acceleration factors.

    Risk Categories:
    - High: Elevated uACR + diabetes OR eGFR declining toward 60
    - Moderate: Elevated uACR alone OR multiple metabolic factors
    - Low: Normal uACR and preserved eGFR
    """
    # High risk: albuminuria + diabetes (strong progression driver)
    if has_elevated_uacr and inputs.has_diabetes:
        return "High"

    # High risk: severe albuminuria
    if inputs.uacr is not None and inputs.uacr >= 300:
        return "High"

    # High risk: borderline eGFR with any albuminuria
    if inputs.egfr < 75 and has_elevated_uacr:
        return "High"

    # Moderate risk: isolated elevated uACR
    if has_elevated_uacr:
        return "Moderate"

    # Moderate risk: borderline eGFR without albuminuria
    if inputs.egfr < 75:
        return "Moderate"

    # Moderate risk: multiple metabolic factors (potential future damage)
    metabolic_count = sum([
        inputs.has_diabetes,
        inputs.bmi is not None and inputs.bmi >= 30,
        inputs.has_dyslipidemia or inputs.total_chol >= 240,
        inputs.sbp >= 150  # Severe uncontrolled HTN
    ])
    if metabolic_count >= 3:
        return "Moderate"

    return "Low"


def _assign_eocri_phenotype(
    inputs: RiskInputs,
    has_elevated_uacr: bool,
    metabolic_burden: int,
    prevent_risk: float
) -> dict:
    """
    Assign EOCRI phenotype based on clinical criteria.

    Phenotype Assignment Logic (for patients with eGFR > 60):

    Type A (Early Metabolic / "Accelerated Ager Young"):
        - Elevated uACR (≥30 mg/g) AND
        - Diabetes OR Obesity (BMI ≥30)
        - These patients are on accelerated trajectory for both CVD and ESRD

    Type B (Silent Renal / "Isolated Albuminuric"):
        - Elevated uACR (≥30 mg/g) AND
        - NO diabetes AND normal lipids
        - KEY TARGET: Low short-term CVD risk but high long-term renal risk
        - Often missed by traditional Framingham-based algorithms

    Type C (Premature Vascular / "Vascular Dominant"):
        - Normal uACR (<30 mg/g) AND
        - High lipids OR smoker
        - Primary risk is premature MI/Stroke, not renal

    Low Risk:
        - Normal uACR AND
        - No significant vascular risk factors
    """
    # Determine obesity status
    is_obese = inputs.has_obesity or (inputs.bmi is not None and inputs.bmi >= 30)

    # Determine dyslipidemia/high lipid status
    has_high_lipids = (
        inputs.has_dyslipidemia or
        inputs.total_chol >= 240 or
        inputs.hdl_chol < 40
    )

    # Type A: Early Metabolic (Accelerated Ager - Young)
    # Elevated uACR + (Diabetes OR Obesity)
    if has_elevated_uacr and (inputs.has_diabetes or is_obese):
        return {
            'type': 'A',
            'name': 'Early Metabolic',
            'clinical_equivalent': 'Accelerated Ager (Young)',
            'treatment_trigger': 'Aggressive BP + SGLT2i + Statin'
        }

    # Type B: Silent Renal (Isolated Albuminuric)
    # Elevated uACR + NO diabetes + normal/near-normal lipids
    # This is the KEY target population for EOCRI
    if has_elevated_uacr and not inputs.has_diabetes and not has_high_lipids:
        return {
            'type': 'B',
            'name': 'Silent Renal',
            'clinical_equivalent': 'Isolated Albuminuric',
            'treatment_trigger': 'Early ASI/RAASi + SGLT2i'
        }

    # Type B also captures: elevated uACR without diabetes (broader definition)
    # Even with some lipid abnormality, if no diabetes, renal risk dominates
    if has_elevated_uacr and not inputs.has_diabetes:
        return {
            'type': 'B',
            'name': 'Silent Renal',
            'clinical_equivalent': 'Isolated Albuminuric',
            'treatment_trigger': 'Early ASI/RAASi + SGLT2i'
        }

    # Type C: Premature Vascular (Vascular Dominant)
    # Normal uACR + (High lipids OR smoker)
    if not has_elevated_uacr and (has_high_lipids or inputs.is_smoker):
        return {
            'type': 'C',
            'name': 'Premature Vascular',
            'clinical_equivalent': 'Vascular Dominant',
            'treatment_trigger': 'Statins + Antiplatelets'
        }

    # Also classify as Type C if PREVENT risk is high despite normal uACR
    if not has_elevated_uacr and prevent_risk >= 25:
        return {
            'type': 'C',
            'name': 'Premature Vascular',
            'clinical_equivalent': 'Vascular Dominant',
            'treatment_trigger': 'Statins + Antiplatelets'
        }

    # Low Risk: Normal uACR and no significant vascular risk factors
    return {
        'type': 'Low',
        'name': 'Low Risk',
        'clinical_equivalent': 'Standard Monitoring',
        'treatment_trigger': 'Standard HTN Management'
    }
