"""
Health state utility values for QALY calculation.
"""

from typing import Any


# Baseline utility by age group (US population norms)
BASELINE_UTILITY = {
    40: 0.90, 50: 0.87, 60: 0.84, 70: 0.80, 80: 0.75, 90: 0.70
}

# Disutility values (additive decrements)
DISUTILITY = {
    # Cardiac Conditions
    "controlled_htn": 0.00,
    "uncontrolled_htn": 0.04,
    "post_mi": 0.12,
    "post_stroke": 0.18,
    "acute_hf": 0.25,
    "chronic_hf": 0.15,
    
    # Renal Conditions
    "ckd_stage_3a": 0.01,  # Mild decrement (early Stage 3)
    "ckd_stage_3b": 0.03,  # Moderate decrement (advanced Stage 3)
    "ckd_stage_4": 0.06,
    "esrd": 0.35,
    
    # Comorbidities
    "diabetes": 0.04,
    "obesity": 0.02,
    "prior_mi": 0.03,  # Additional decrement for history? Or captured in state?
    "prior_stroke": 0.05
}

# Acute event disutilities (applied for 1 month)
ACUTE_EVENT_DISUTILITY = {
    "acute_mi": 0.20,
    "acute_stroke": 0.40,
    "acute_hf": 0.25
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
        if getattr(patient, 'is_bp_controlled', False):
            total_decrement += DISUTILITY["controlled_htn"]
        else:
            total_decrement += DISUTILITY["uncontrolled_htn"]
    elif c_val in ACUTE_EVENT_DISUTILITY:
        total_decrement += ACUTE_EVENT_DISUTILITY[c_val]
    elif c_val in DISUTILITY:
        total_decrement += DISUTILITY[c_val]
        
    # Renal state decrement
    r_state = getattr(patient, 'renal_state', None)
    r_val = r_state.value if hasattr(r_state, 'value') else str(r_val)
    
    if r_val in DISUTILITY:
        total_decrement += DISUTILITY[r_val]
        
    # Comorbidities
    if getattr(patient, 'has_diabetes', False):
        total_decrement += DISUTILITY["diabetes"]
        
    return max(0.0, baseline - total_decrement)


def calculate_monthly_qaly(patient: Any, discount_rate: float = 0.03) -> float:
    """Calculate discounted monthly QALY."""
    utility = get_utility(patient)
    monthly_qaly = utility / 12
    
    years = getattr(patient, 'time_in_simulation', 0) / 12
    discount_factor = 1 / ((1 + discount_rate) ** years)
    
    return monthly_qaly * discount_factor
