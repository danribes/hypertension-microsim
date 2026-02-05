"""
Health state utility values for QALY calculation.

This module provides utility values for cost-utility analysis following
NICE DSU Technical Support Document 12 recommendations and ISPOR guidelines.

All utility values are on the EQ-5D scale (0 = death, 1 = perfect health).
Disutilities are subtracted from baseline to obtain health state utility.

References:
    Ara R, Brazier JE. Populating an economic model with health state utility
    values: moving toward better practice. Value Health. 2010;13(5):509-518.

    Sullivan PW, Ghushchyan V. Preference-based EQ-5D index scores for chronic
    conditions in the United States. Med Decis Making. 2006;26(4):410-420.

    NICE Decision Support Unit. Technical Support Document 12: The use of
    health state utility values in decision models. 2011.

CHEERS 2022 Compliance:
    Item 17: Report methods for valuing health outcomes (utilities).
"""

from typing import Any


# =============================================================================
# BASELINE UTILITY BY AGE (Resistant HTN Population)
# =============================================================================
# Note: Resistant HTN patients have lower baseline utility than general population
# due to underlying disease burden, polypharmacy, and comorbidities.
#
# General population norms (Sullivan PW, 2006):
#   Age 60: 0.84, Age 70: 0.80
#
# Resistant HTN adjustment: approximately -0.03 to -0.05 decrement
# Reference: Yoon SS et al. Resistant hypertension and QoL. J Clin Hypertens. 2015.
# Reference: Sim JJ et al. Resistant hypertension health outcomes. J Am Heart Assoc. 2015.
#
# PSA: Normal distribution with SD=0.05 for each age bracket
BASELINE_UTILITY = {
    40: 0.87,  # Age 40-49, resistant HTN (vs 0.90 general pop)
    50: 0.84,  # Age 50-59 (vs 0.87)
    60: 0.81,  # Age 60-69 (vs 0.84)
    70: 0.77,  # Age 70-79 (vs 0.80)
    80: 0.72,  # Age 80-89 (vs 0.75)
    90: 0.67   # Age 90+ (vs 0.70)
}

# =============================================================================
# DISUTILITY VALUES (Additive Decrements)
# =============================================================================
# Method: Additive disutility model per NICE TSD 12 recommendations
# Values derived from condition-specific EQ-5D studies
DISUTILITY = {
    # -------------------------------------------------------------------------
    # Cardiac Conditions
    # -------------------------------------------------------------------------
    "controlled_htn": 0.00,
    # Source: Hypertension alone has minimal impact on EQ-5D when controlled
    # Reference: Wang Y et al. Health utilities for CVD. Eur J Prev Cardiol. 2019

    "uncontrolled_htn": 0.04,
    # Source: Uncontrolled HTN associated with symptoms (headache, anxiety)
    # Reference: Mancia G et al. ESH/ESC Guidelines. J Hypertens. 2013

    "post_mi": 0.12,
    # Source: Chronic post-MI utility decrement
    # Reference: Lacey EA, Walters SJ. Utility values for post-MI states.
    # Health Qual Life Outcomes. 2003;1:18.
    # PSA: Beta(α=88, β=12) mean=0.12, SD=0.03

    "post_stroke": 0.18,
    # Source: Average disutility for chronic stroke (varies by severity)
    # Reference: Luengo-Fernandez R et al. Quality of life after TIA and stroke.
    # Cerebrovasc Dis. 2013;36(5-6):372-378.
    # Range: 0.10 (mild) to 0.50 (severe disability)
    # PSA: Beta(α=72, β=28) mean=0.18, SD=0.05

    "acute_hf": 0.25,
    # Source: Acute decompensated HF hospitalization
    # Reference: Lewis EF et al. Health-related QoL in HF. JACC. 2007

    "chronic_hf": 0.15,
    # Source: Stable chronic HF (NYHA II-III average)
    # Reference: Calvert MJ et al. Cost-effectiveness of SGLT2i in HF.
    # Eur J Heart Fail. 2021.
    # PSA: Beta(α=85, β=15) mean=0.15, SD=0.04

    # -------------------------------------------------------------------------
    # Renal Conditions (CKD stages per KDIGO)
    # -------------------------------------------------------------------------
    "ckd_stage_3a": 0.01,
    # Source: Early CKD (eGFR 45-59) - minimal symptomatic impact
    # Reference: Gorodetskaya I et al. Health-related QoL and CKD stages.
    # Am J Kidney Dis. 2005;45(4):658-666.

    "ckd_stage_3b": 0.03,
    # Source: Moderate CKD (eGFR 30-44)
    # Reference: Gorodetskaya I et al. 2005

    "ckd_stage_4": 0.06,
    # Source: Severe CKD (eGFR 15-29)
    # Reference: Gorodetskaya I et al. 2005
    # PSA: Beta(α=94, β=6)

    "esrd": 0.35,
    # Source: ESRD on dialysis
    # Reference: Wasserfallen JB et al. Quality of life on dialysis.
    # Nephrol Dial Transplant. 2004;19(6):1594-1599.
    # Range: 0.25-0.45 depending on dialysis modality
    # PSA: Beta(α=65, β=35)

    # -------------------------------------------------------------------------
    # Comorbidities (Additional decrements)
    # -------------------------------------------------------------------------
    "diabetes": 0.04,
    # Source: Type 2 diabetes mellitus (uncomplicated)
    # Reference: Sullivan PW et al. Catalogue of EQ-5D scores for UK.
    # Med Decis Making. 2011;31(6):800-804.

    "obesity": 0.02,
    # Source: BMI ≥30 impact on QoL
    # Reference: Jia H, Lubetkin EI. Obesity and QoL. Obes Rev. 2005

    "prior_mi": 0.03,
    # Source: History of MI (on top of current cardiac state)
    # Note: May be captured in post_mi state - use cautiously to avoid double-counting

    "prior_stroke": 0.05,
    # Source: History of stroke with residual deficit
    # Reference: Luengo-Fernandez R et al. 2013

    "atrial_fibrillation": 0.05,
    # Source: Chronic atrial fibrillation
    # Reference: Dorian P et al. The impairment of health-related quality of
    # life in patients with intermittent atrial fibrillation. JACC. 2000.
    # Includes: palpitations, fatigue, anxiety about stroke, anticoagulation burden
    # PSA: Beta(α=95, β=5)

    # -------------------------------------------------------------------------
    # Neurological/Cognitive States
    # -------------------------------------------------------------------------
    "mci": 0.05,
    # Source: Mild Cognitive Impairment
    # Reference: Andersen CK et al. QoL in dementia. Health Qual Life Outcomes. 2004
    # MCI has modest impact on self-reported QoL
    # PSA: Beta(α=95, β=5)

    "dementia": 0.30,
    # Source: Dementia (moderate severity average)
    # Reference: Wlodarczyk JH et al. QoL in Alzheimer's disease. Pharmacoeconomics. 2004
    # Range: 0.15 (mild) to 0.50 (severe)
    # PSA: Beta(α=70, β=30)

    # -------------------------------------------------------------------------
    # Resistant Hypertension Specific
    # -------------------------------------------------------------------------
    "resistant_htn_baseline": 0.02,
    # Source: Additional burden of resistant HTN vs controlled HTN
    # Reference: Sim JJ et al. Resistant HTN and health outcomes. J Am Heart Assoc. 2015
    # Includes medication burden, clinic visits, anxiety about control

    "hyperkalemia_episode": 0.03
    # Source: Hyperkalemia requiring treatment modification
    # Reference: Luo J et al. Hyperkalemia and health-related QoL. Clin Kidney J. 2020
    # Temporary disutility for monitoring/dietary changes
}

# =============================================================================
# ACUTE EVENT DISUTILITIES (Applied for event month only)
# =============================================================================
# Acute disutilities reflect the severe temporary impact during hospitalization
# and immediate recovery. Applied for 1 cycle (1 month) only.
#
# Reference: Sullivan PW et al. A national catalog of preference-based scores.
# Med Care. 2005;43(7):736-749.
ACUTE_EVENT_DISUTILITY = {
    "acute_mi": 0.20,
    # Source: Acute MI hospitalization
    # Reference: Lacey EA, Walters SJ. Health Qual Life Outcomes. 2003
    # PSA: Beta(α=80, β=20)

    "acute_stroke": 0.40,
    # Source: Acute stroke (average of ischemic/hemorrhagic)
    # Reference: Luengo-Fernandez R et al. 2013
    # Note: Hemorrhagic typically higher disutility than ischemic
    # PSA: Beta(α=60, β=40)

    "acute_ischemic_stroke": 0.35,
    # Source: Acute ischemic stroke hospitalization
    # Reference: Luengo-Fernandez R et al. Stroke 2013
    # Lower than hemorrhagic due to less severe presentation
    # PSA: Beta(α=65, β=35)

    "acute_hemorrhagic_stroke": 0.50,
    # Source: Acute hemorrhagic stroke (ICH/SAH)
    # Reference: Luengo-Fernandez R et al. 2013; Dewey HM et al. 2004
    # Higher disutility due to severity and ICU requirement
    # PSA: Beta(α=50, β=50)

    "tia": 0.10,
    # Source: Transient ischemic attack
    # Reference: Moran GM et al. Health Qual Life Outcomes. 2014
    # Lower acute impact as symptoms resolve within 24h
    # But includes anxiety/investigation burden
    # PSA: Beta(α=90, β=10)

    "acute_hf": 0.25,
    # Source: Acute HF admission
    # Reference: Lewis EF et al. JACC 2007
    # PSA: Beta(α=75, β=25)

    "new_af": 0.15
    # Source: New-onset AF requiring hospitalization/cardioversion
    # Reference: Dorian P et al. JACC 2000; Reynolds MR et al. AF ablation QoL. Circ 2006
    # Acute impact from palpitations, anxiety, hospitalization
    # PSA: Beta(α=85, β=15)
}


def get_utility(patient: Any) -> float:
    """
    Calculate utility value for a patient based on additive disutilities.
    
    Args:
        patient: Patient object
        
    Returns:
        Utility value (0-1)
    """
    if not getattr(patient, 'is_alive', True):
        return 0.0
        
    # Start with baseline utility for age
    age = getattr(patient, 'age', 60)
    baseline = 0.84
    for a, u in sorted(BASELINE_UTILITY.items()):
        if age < a + 10:
            baseline = u
            break
            
    total_decrement = 0.0
    
    # Cardiac state decrement
    c_state = getattr(patient, 'cardiac_state', None)
    c_val = c_state.value if hasattr(c_state, 'value') else str(c_state)
    
    if c_val == "no_acute_event":
        # Use SBP-based gradient instead of binary controlled/uncontrolled
        # This captures the continuous QoL improvement with better BP control
        # Reference: Mancia G et al. ESH/ESC Guidelines. J Hypertens. 2013
        current_sbp = getattr(patient, 'current_sbp', 140)

        # Gradient disutility based on SBP level:
        # - SBP < 130: Well controlled, minimal disutility (0.00)
        # - SBP 130-140: Controlled, mild disutility (0.01)
        # - SBP 140-160: Uncontrolled, moderate disutility (0.02-0.04)
        # - SBP 160-180: Poorly controlled, high disutility (0.04-0.06)
        # - SBP > 180: Severely uncontrolled, very high disutility (0.06+)
        if current_sbp < 130:
            htn_disutility = 0.00  # Well controlled
        elif current_sbp < 140:
            # Linear gradient from 0.00 to 0.01 over 130-140 range
            htn_disutility = 0.01 * (current_sbp - 130) / 10
        elif current_sbp < 160:
            # Linear gradient from 0.01 to 0.04 over 140-160 range
            htn_disutility = 0.01 + 0.03 * (current_sbp - 140) / 20
        elif current_sbp < 180:
            # Linear gradient from 0.04 to 0.06 over 160-180 range
            htn_disutility = 0.04 + 0.02 * (current_sbp - 160) / 20
        else:
            # Severe HTN: cap at 0.08 disutility
            htn_disutility = min(0.08, 0.06 + 0.02 * (current_sbp - 180) / 20)

        total_decrement += htn_disutility
    elif c_val in ACUTE_EVENT_DISUTILITY:
        total_decrement += ACUTE_EVENT_DISUTILITY[c_val]
    elif c_val in DISUTILITY:
        total_decrement += DISUTILITY[c_val]
        
    # Renal state decrement
    r_state = getattr(patient, 'renal_state', None)
    r_val = r_state.value if hasattr(r_state, 'value') else str(r_state)

    if r_val in DISUTILITY:
        total_decrement += DISUTILITY[r_val]

    # Neuro state decrement (MCI, dementia)
    n_state = getattr(patient, 'neuro_state', None)
    if n_state is not None:
        n_val = n_state.value if hasattr(n_state, 'value') else str(n_state)
        if n_val in DISUTILITY:
            total_decrement += DISUTILITY[n_val]

    # Comorbidities
    if getattr(patient, 'has_diabetes', False):
        total_decrement += DISUTILITY["diabetes"]

    # Atrial fibrillation (chronic burden)
    if getattr(patient, 'has_atrial_fibrillation', False):
        total_decrement += DISUTILITY["atrial_fibrillation"]

    # Hyperkalemia impact (if recent episode)
    if getattr(patient, 'has_hyperkalemia', False):
        total_decrement += DISUTILITY.get("hyperkalemia_episode", 0.03)

    # Resistant HTN baseline burden
    # Applied if patient has resistant HTN characteristics
    # Burden proportional to SBP level and medication count
    num_meds = getattr(patient, 'num_antihypertensives', 0)
    current_sbp = getattr(patient, 'current_sbp', 140)
    if num_meds >= 3 and current_sbp >= 140:
        # Resistant HTN with uncontrolled BP: additional burden
        # Scales with both medication burden and BP control
        resistant_burden = 0.01 + 0.01 * min(1.0, (current_sbp - 140) / 40)
        total_decrement += resistant_burden

    return max(0.0, baseline - total_decrement)


def calculate_monthly_qaly(
    patient: Any,
    discount_rate: float = 0.03,
    cycle_length_months: float = 1.0,
    use_half_cycle: bool = True
) -> float:
    """
    Calculate discounted monthly QALY with half-cycle correction.

    Half-cycle correction assumes that health state utility is experienced
    at the midpoint of each cycle, rather than at the beginning or end.
    This produces more accurate QALY estimates in discrete-time models.

    Formula with half-cycle:
        years = (time_in_simulation + 0.5 * cycle_length) / 12
        discount = 1 / (1 + r)^years
        qaly = (utility / 12) * discount

    Args:
        patient: Patient object with time_in_simulation attribute
        discount_rate: Annual discount rate (default 3%)
        cycle_length_months: Length of simulation cycle in months
        use_half_cycle: If True, apply half-cycle correction

    Returns:
        Discounted monthly QALY

    Reference:
        Briggs A, Sculpher M, Claxton K. Decision Modelling for Health
        Economic Evaluation. Oxford University Press. 2006. Chapter 3.

        Sanders GD, et al. Recommendations for conduct, methodological
        practices, and reporting of cost-effectiveness analyses. JAMA.
        2016;316(10):1093-1103.
    """
    utility = get_utility(patient)
    monthly_qaly = utility / 12

    time_months = getattr(patient, 'time_in_simulation', 0)

    if use_half_cycle:
        adjusted_months = time_months + (0.5 * cycle_length_months)
    else:
        adjusted_months = time_months

    years = adjusted_months / 12.0
    discount_factor = 1.0 / ((1.0 + discount_rate) ** years)

    return monthly_qaly * discount_factor
