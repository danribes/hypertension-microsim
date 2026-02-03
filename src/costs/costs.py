"""
Cost inputs for US and UK markets.
"""

from dataclasses import dataclass
from typing import Dict, Any, Union
from enum import Enum


@dataclass
class CostInputs:
    """Cost inputs for a specific market."""
    currency: str
    
    # Drug costs (monthly)
    ixa_001_monthly: float
    spironolactone_monthly: float
    sglt2_inhibitor_monthly: float # Added for Option F
    background_therapy_monthly: float
    
    # Lab costs (Option H)
    lab_test_cost_k: float
    
    # Acute event costs
    mi_acute: float
    stroke_acute: float  # Legacy: average stroke cost
    ischemic_stroke_acute: float  # Ischemic stroke (lower cost)
    hemorrhagic_stroke_acute: float  # Hemorrhagic stroke (higher cost)
    tia_acute: float  # TIA (lower cost, typically ER visit + workup)
    hf_admission: float
    
    # Annual management costs - Cardiac
    controlled_htn_annual: float
    uncontrolled_htn_annual: float
    post_mi_annual: float
    post_stroke_annual: float
    heart_failure_annual: float
    
    # Annual management costs - Renal
    ckd_stage_3a_annual: float
    ckd_stage_3b_annual: float
    ckd_stage_4_annual: float
    esrd_annual: float

    # Indirect Costs (Productivity Loss)
    daily_wage: float
    absenteeism_acute_mi_days: int
    absenteeism_stroke_days: int
    absenteeism_hf_days: int
    disability_multiplier_stroke: float  # % of annual wage lost
    disability_multiplier_hf: float      # % of annual wage lost


# US costs (2024 USD)
US_COSTS = CostInputs(
    currency="USD",
    ixa_001_monthly=500.0,
    spironolactone_monthly=15.0,
    sglt2_inhibitor_monthly=450.0, # Brand name (Jardiance/Farxiga) approx cost
    background_therapy_monthly=75.0,
    mi_acute=25000.0,
    stroke_acute=35000.0,  # Legacy average
    ischemic_stroke_acute=15200.0,  # Aligned with Excel model
    hemorrhagic_stroke_acute=22500.0,  # Higher cost (ICU, surgery)
    tia_acute=2100.0,  # ER visit + imaging workup
    hf_admission=18000.0,
    lab_test_cost_k=15.0, # Option H: Lab Cost
    controlled_htn_annual=800.0,
    uncontrolled_htn_annual=1200.0,
    post_mi_annual=5500.0,
    post_stroke_annual=12000.0,
    heart_failure_annual=15000.0,
    ckd_stage_3a_annual=2500.0,
    ckd_stage_3b_annual=4500.0,
    ckd_stage_4_annual=8000.0,
    esrd_annual=90000.0,
    # Indirect
    daily_wage=240.0,            # ~$60k annual / 250 days
    absenteeism_acute_mi_days=7,
    absenteeism_stroke_days=30,
    absenteeism_hf_days=5,
    disability_multiplier_stroke=0.20,
    disability_multiplier_hf=0.15,
)

# UK costs (2024 GBP)
UK_COSTS = CostInputs(
    currency="GBP",
    ixa_001_monthly=400.0,
    spironolactone_monthly=8.0,
    sglt2_inhibitor_monthly=35.0, # Generic Dapagliflozin available in UK (much cheaper)
    background_therapy_monthly=40.0,
    mi_acute=8000.0,
    stroke_acute=12000.0,  # Legacy average
    ischemic_stroke_acute=6000.0,  # NHS Reference Costs
    hemorrhagic_stroke_acute=9000.0,  # Higher cost
    tia_acute=850.0,  # Rapid access TIA clinic
    hf_admission=5500.0,
    lab_test_cost_k=3.0, # Option H: Lab Cost
    controlled_htn_annual=350.0,
    uncontrolled_htn_annual=550.0,
    post_mi_annual=2200.0,
    post_stroke_annual=5500.0,
    heart_failure_annual=6000.0,
    ckd_stage_3a_annual=1200.0,
    ckd_stage_3b_annual=2200.0,
    ckd_stage_4_annual=3500.0,
    esrd_annual=35000.0,
    # Indirect
    daily_wage=160.0,            # ~£40k annual
    absenteeism_acute_mi_days=14, # More generous sick leave
    absenteeism_stroke_days=60,
    absenteeism_hf_days=10,
    disability_multiplier_stroke=0.30, # Higher impact on lower wage
    disability_multiplier_hf=0.20,
)


def get_drug_cost(patient: Any, costs: CostInputs) -> float:
    """Calculate monthly drug cost based on regimen."""
    total = 0.0
    
    # Base treatment logic (simplified)
    # Assuming treatment enum implies the PRIMARY investigational drug
    t_val = getattr(patient, 'treatment', None)
    t_str = t_val.value if hasattr(t_val, 'value') else str(t_val)
    
    if t_str == "ixa_001":
        total += costs.ixa_001_monthly
    elif t_str == "spironolactone":
        total += costs.spironolactone_monthly
    else:
        # Standard care cost is baseline
        # In this model, IXA/SPIRO might be added ON TOP of or INSTEAD of standard care
        # Let's assume they REPLACE a standard agent, but background therapy typically remains
        pass
        
    # Always add background therapy cost (ACEi/ARB/CCB etc)
    total += costs.background_therapy_monthly
    
    # SGLT2 Inhibitor (Add-on)
    if getattr(patient, 'on_sglt2_inhibitor', False):
        total += costs.sglt2_inhibitor_monthly
        
    return total


def get_total_cost(patient: Any, costs: CostInputs, is_monthly: bool = True) -> float:
    """
    Get total management cost for a patient based on cardiac and renal states.
    Acute event costs are handled separately in simulation.
    """
    total_annual = 0.0
    
    # Cardiac State Costs
    c_state = getattr(patient, 'cardiac_state', None)
    c_val = c_state.value if hasattr(c_state, 'value') else str(c_state)
    
    if c_val == "controlled_htn": # Derived from BP in simulation, but here based on state?
        # Patient.cardiac_state doesn't track controlled/uncontrolled HTN anymore
        # We need to check BP control
        if getattr(patient, 'is_bp_controlled', False):
            total_annual += costs.controlled_htn_annual
        else:
            total_annual += costs.uncontrolled_htn_annual
    elif c_val == "no_acute_event":
         # Fallback to BP control status
        if getattr(patient, 'is_bp_controlled', False):
            total_annual += costs.controlled_htn_annual
        else:
            total_annual += costs.uncontrolled_htn_annual
    elif c_val == "post_mi":
        total_annual += costs.post_mi_annual
    elif c_val == "post_stroke":
        total_annual += costs.post_stroke_annual
    elif c_val == "chronic_hf" or c_val == "acute_hf":
        total_annual += costs.heart_failure_annual
        
    # Renal State Costs (Additive)
    r_state = getattr(patient, 'renal_state', None)
    r_val = r_state.value if hasattr(r_state, 'value') else str(r_val)
    
    if r_val == "ckd_stage_3a":
        total_annual += costs.ckd_stage_3a_annual
    elif r_val == "ckd_stage_3b":
        total_annual += costs.ckd_stage_3b_annual
    elif r_val == "ckd_stage_4":
        total_annual += costs.ckd_stage_4_annual
    elif r_val == "esrd":
        total_annual += costs.esrd_annual
        
    return total_annual / 12 if is_monthly else total_annual

def get_event_cost(event_type: str, costs: CostInputs) -> float:
    """Get one-time cost for acute events."""
    if event_type == "acute_mi":
        return costs.mi_acute
    elif event_type == "acute_ischemic_stroke":
        return costs.ischemic_stroke_acute
    elif event_type == "acute_hemorrhagic_stroke":
        return costs.hemorrhagic_stroke_acute
    elif event_type == "acute_stroke":  # Legacy
        return costs.stroke_acute
    elif event_type == "tia":
        return costs.tia_acute
    elif event_type == "acute_hf":
        return costs.hf_admission
    return 0.0

def get_productivity_loss(patient: Any, costs: CostInputs, is_monthly: bool = True) -> float:
    """
    Calculate productivity loss due to disability (Chronic).
    Acute absenteeism is calculated separately.
    """
    # Only applies to working age (< 65)
    if patient.age >= 65:
        return 0.0
        
    annual_loss = 0.0
    c_state = getattr(patient, 'cardiac_state', None)
    c_val = c_state.value if hasattr(c_state, 'value') else str(c_state)
    
    annual_wage = costs.daily_wage * 250 # approx working days
    
    if c_val == "post_stroke":
        annual_loss = annual_wage * costs.disability_multiplier_stroke
    elif c_val in ["chronic_hf", "acute_hf"]:
        annual_loss = annual_wage * costs.disability_multiplier_hf
        
    return annual_loss / 12 if is_monthly else annual_loss

def get_acute_absenteeism_cost(event_type: str, costs: CostInputs, age: float) -> float:
    """Calculate one-time absenteeism cost for acute events."""
    if age >= 65:
        return 0.0

    days_lost = 0
    if event_type == "acute_mi":
        days_lost = costs.absenteeism_acute_mi_days
    elif event_type in ["acute_stroke", "acute_ischemic_stroke", "acute_hemorrhagic_stroke"]:
        days_lost = costs.absenteeism_stroke_days
    elif event_type == "tia":
        days_lost = 3  # TIA typically requires short workup
    elif event_type == "acute_hf":
        days_lost = costs.absenteeism_hf_days

    return days_lost * costs.daily_wage
