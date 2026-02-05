"""
Cost inputs for US and UK markets.

All costs are reported in 2024 local currency (USD/GBP) and should be
inflated appropriately for future analyses. Sources are documented per
CHEERS 2022 reporting guidelines.

References:
    Husereau D, et al. Consolidated Health Economic Evaluation Reporting
    Standards 2022 (CHEERS 2022) Statement. BMJ. 2022;376:e067975.

    NICE. NICE health technology evaluations: the manual. PMG36. 2022.
    Section 4.4: Cost identification, measurement, and valuation.
"""

from dataclasses import dataclass
from typing import Dict, Any, Union
from enum import Enum


@dataclass
class CostInputs:
    """
    Cost inputs for a specific market.

    All costs should be documented with:
    - Source (publication or database)
    - Price year (e.g., 2024 USD)
    - PSA distribution for sensitivity analysis

    CHEERS 2022 Compliance:
        Item 15: Report the methods for estimating resource quantities.
        Item 16: Report unit costs, currency, price date, conversion methods.
    """
    currency: str

    # =========================================================================
    # DRUG COSTS (monthly)
    # =========================================================================
    ixa_001_monthly: float
    # Source: Manufacturer pricing (placeholder - adjust to actual WAC/ASP)
    # PSA: Gamma(mean=500, SD=100)

    spironolactone_monthly: float
    # Source: NADAC (National Average Drug Acquisition Cost) 2024
    # https://data.medicaid.gov/nadac
    # PSA: Gamma(mean=15, SD=5)

    sglt2_inhibitor_monthly: float
    # US: Brand WAC (Jardiance/Farxiga) ~$450/month
    # UK: Generic dapagliflozin ~£35/month (off-patent)
    # Source: US - SSR Health Net Price Report; UK - NHS Drug Tariff
    # PSA: Gamma(mean=450, SD=90) for US; Gamma(mean=35, SD=7) for UK

    background_therapy_monthly: float
    # Source: Generic ACEi/ARB/CCB combination therapy
    # Reference: Moran AE et al. Cost-effectiveness of HTN treatment. JAMA. 2015.
    # PSA: Gamma(mean=75, SD=25)

    potassium_binder_monthly: float
    # Potassium binders (patiromer/Veltassa, sodium zirconium/Lokelma)
    # Source: US - SSR Health Net Price Report 2024
    # Patiromer ~$500/month, sodium zirconium ~$400/month
    # UK - NHS Drug Tariff (patiromer ~£300/month)
    # Reference: Weir MR et al. Patiromer in hyperkalemia. NEJM. 2015.
    # PSA: Gamma(mean=500, SD=100)

    # =========================================================================
    # LAB COSTS
    # =========================================================================
    lab_test_cost_k: float
    # Serum potassium monitoring cost
    # Source: US - Medicare Clinical Laboratory Fee Schedule 2024 (CPT 80051)
    # UK - NHS Reference Costs (DAPS08)
    # PSA: Gamma(mean=15, SD=5)

    # =========================================================================
    # ACUTE EVENT COSTS (one-time, hospitalization)
    # =========================================================================
    mi_acute: float
    # Source: US - HCUP NIS 2022, DRG 280-282 (AMI w/o MCC)
    # Mean cost: $22,000-28,000 (severity-dependent)
    # Reference: Kauf TL et al. Costs of AMI. Am Heart J. 2006.
    # PSA: Gamma(mean=25000, SD=5000)

    stroke_acute: float  # Legacy: weighted average stroke cost (deprecated)

    ischemic_stroke_acute: float
    # Source: US - HCUP NIS 2022, DRG 61-63 (Ischemic Stroke)
    # UK - NHS Reference Costs 2022-23 (AA22-AA24)
    # Reference: Wang G et al. Costs of stroke. Stroke. 2014.
    # PSA: Gamma(mean=15200, SD=3000)

    hemorrhagic_stroke_acute: float
    # Source: US - HCUP NIS 2022, DRG 64-66 (ICH/SAH)
    # Higher cost due to ICU, neurosurgical intervention
    # Reference: Qureshi AI et al. Intracerebral haemorrhage. Lancet. 2009.
    # PSA: Gamma(mean=22500, SD=5000)

    tia_acute: float
    # Source: US - HCUP 2022, ER visit + imaging workup (CT/MRI, carotid doppler)
    # UK - NHS Reference Costs (Rapid Access TIA clinic)
    # Reference: Johnston SC et al. Short-term prognosis after TIA. JAMA. 2000.
    # PSA: Gamma(mean=2100, SD=500)

    hf_admission: float
    # Source: US - HCUP NIS 2022, DRG 291-293 (HF admission)
    # Reference: Heidenreich PA et al. Forecasting HF costs. Circ HF. 2013.
    # PSA: Gamma(mean=18000, SD=4000)

    af_acute: float
    # Source: US - HCUP NIS 2022, DRG 308-310 (Cardiac arrhythmia admission)
    # Includes cardioversion, rate control, anticoagulation initiation
    # Reference: Kim MH et al. Estimation of total incremental health care
    # costs in patients with atrial fibrillation. Circ CV Qual Outcomes. 2011.
    # PSA: Gamma(mean=8500, SD=2000)

    # =========================================================================
    # ANNUAL MANAGEMENT COSTS - CARDIAC
    # =========================================================================
    controlled_htn_annual: float
    # Source: Moran AE et al. Cost-effectiveness of HTN treatment. JAMA. 2015.
    # Includes: 2-4 primary care visits, routine labs, medications
    # PSA: Gamma(mean=800, SD=200)

    uncontrolled_htn_annual: float
    # Source: Valderrama AL et al. Direct medical costs of HTN. J Am Soc Hypertens. 2014.
    # Higher due to: more visits, specialist referrals, medication titration
    # PSA: Gamma(mean=1200, SD=300)

    post_mi_annual: float
    # Source: Zhao Z et al. Post-MI costs in US patients. JMCP. 2010.
    # Includes: cardiology follow-up, cardiac rehab, secondary prevention meds
    # PSA: Gamma(mean=5500, SD=1000)

    post_stroke_annual: float
    # Source: Luengo-Fernandez R et al. Cost of stroke care. Stroke. 2013.
    # High cost due to: rehabilitation, disability care, specialist follow-up
    # PSA: Gamma(mean=12000, SD=3000)

    heart_failure_annual: float
    # Source: Dunlay SM et al. Lifetime costs of HF. Circ HF. 2011.
    # Includes: HF clinic, diuretic management, frequent hospitalizations
    # PSA: Gamma(mean=15000, SD=4000)

    af_annual: float
    # Source: Kim MH et al. Total incremental costs in AF. Circ CV Qual Outcomes. 2011.
    # Includes: Anticoagulation (DOAC ~$500/month), INR monitoring (warfarin),
    # rate/rhythm control meds, cardiology follow-up, echo monitoring
    # US: ~$8,500/year (DOAC) or ~$3,000/year (warfarin)
    # UK: ~£2,500/year (DOAC at NHS prices)
    # PSA: Gamma(mean=8500, SD=2000)

    # =========================================================================
    # ANNUAL MANAGEMENT COSTS - RENAL
    # =========================================================================
    ckd_stage_3a_annual: float
    # Source: Vupputuri S et al. Direct medical costs of CKD. Kidney Int. 2014.
    # Early-stage CKD: nephrology referral, monitoring
    # PSA: Gamma(mean=2500, SD=500)

    ckd_stage_3b_annual: float
    # Source: Vupputuri S et al. 2014
    # Increased monitoring, complication management
    # PSA: Gamma(mean=4500, SD=900)

    ckd_stage_4_annual: float
    # Source: Smith DH et al. Costs of CKD stages. Am J Kidney Dis. 2004.
    # Pre-dialysis education, vascular access preparation
    # PSA: Gamma(mean=8000, SD=2000)

    esrd_annual: float
    # Source: USRDS Annual Data Report 2023 (Chapter 9: Healthcare Expenditures)
    # US: ~$90,000/year for hemodialysis
    # UK: ~£35,000/year (NICE TA guidance)
    # Reference: Honeycutt AA et al. Medical costs of CKD in US. JASN. 2013.
    # PSA: Gamma(mean=90000, SD=15000)

    # =========================================================================
    # INDIRECT COSTS (Productivity Loss) - Societal Perspective
    # =========================================================================
    daily_wage: float
    # Source: US BLS Occupational Employment and Wage Statistics 2024
    # Median wage ~$60,000/year = $240/day (250 working days)
    # UK: ONS ASHE 2024, median ~£40,000/year = £160/day
    # PSA: Gamma

    absenteeism_acute_mi_days: int
    # Source: Greiner W et al. Productivity loss after acute coronary syndrome.
    # Eur J Health Econ. 2004. Range: 5-14 days depending on severity.
    # PSA: Uniform(5, 14)

    absenteeism_stroke_days: int
    # Source: Dewilde S et al. Work absence and return after stroke. BMJ Open. 2017.
    # Highly variable (7-90+ days); 30 days represents mild-moderate stroke.
    # PSA: Uniform(14, 60)

    absenteeism_hf_days: int
    # Source: Liao L et al. Costs and resource use in HF. JACC HF. 2007.
    # PSA: Uniform(3, 10)

    disability_multiplier_stroke: float
    # Percentage of annual wage lost due to chronic disability post-stroke
    # Source: Tanaka E et al. Long-term costs of stroke. Stroke. 2011.
    # Range: 0.10-0.40 depending on severity; 0.20 for moderate stroke.
    # PSA: Beta(α=20, β=80)

    disability_multiplier_hf: float
    # Source: Heidenreich PA et al. Economic impact of HF. Circulation. 2013.
    # PSA: Beta(α=15, β=85)


# =============================================================================
# US COSTS (2024 USD)
# =============================================================================
# Price year: 2024
# Perspective: Healthcare system (direct medical) + Societal (indirect)
# Sources: HCUP NIS, Medicare Fee Schedules, NADAC, BLS
#
# Reference: Wang G, et al. Age-specific and sex-specific mortality in 187
# countries. Lancet. 2012;380(9859):2071-2094.
# =============================================================================
US_COSTS = CostInputs(
    currency="USD",

    # --- Drug Costs (Monthly) ---
    ixa_001_monthly=500.0,
    # Source: Manufacturer WAC (placeholder - adjust per actual pricing)

    spironolactone_monthly=15.0,
    # Source: NADAC 2024 - generic spironolactone 25mg x 30

    sglt2_inhibitor_monthly=450.0,
    # Source: SSR Health Net Price Report 2024 - Jardiance/Farxiga brand

    background_therapy_monthly=75.0,
    # Source: NADAC 2024 - generic ACEi/ARB + CCB + thiazide

    potassium_binder_monthly=500.0,
    # Source: SSR Health Net Price Report 2024 - Patiromer (Veltassa)

    # --- Acute Event Costs ---
    mi_acute=25000.0,
    # Source: HCUP NIS 2022 - DRG 280-282 mean cost

    stroke_acute=35000.0,  # Legacy: weighted average (deprecated)

    ischemic_stroke_acute=15200.0,
    # Source: HCUP NIS 2022 - DRG 61-63 (aligned with Excel model)

    hemorrhagic_stroke_acute=22500.0,
    # Source: HCUP NIS 2022 - DRG 64-66 (ICH, higher severity)

    tia_acute=2100.0,
    # Source: HCUP 2022 - ER + CT/MRI + carotid doppler

    hf_admission=18000.0,
    # Source: HCUP NIS 2022 - DRG 291-293

    af_acute=8500.0,
    # Source: HCUP NIS 2022 - DRG 308-310 (Cardiac arrhythmia)
    # Reference: Kim MH et al. Circ CV Qual Outcomes. 2011

    lab_test_cost_k=15.0,
    # Source: Medicare CLFS 2024 - CPT 80051 (BMP)

    # --- Annual Management Costs ---
    # Note: Resistant HTN patients have ~1.5-2x higher costs than general HTN
    # due to more frequent visits, additional testing, and specialist referrals.
    # Reference: Sim JJ et al. Resistant hypertension and healthcare costs.
    # J Am Heart Assoc. 2015;4(12):e002404.

    controlled_htn_annual=1200.0,
    # Source: Resistant HTN baseline (higher than general HTN ~$800)
    # Includes additional monitoring, specialist visits
    # Reference: Sim JJ et al. 2015 - adjusted to 2024

    uncontrolled_htn_annual=1800.0,
    # Source: Uncontrolled resistant HTN (additional costs vs controlled)
    # Includes more frequent visits, medication adjustments
    # Reference: Sim JJ et al. 2015; Daugherty SL et al. Circulation 2012

    post_mi_annual=5500.0,
    # Source: Zhao Z et al. JMCP 2010 - adjusted to 2024

    post_stroke_annual=12000.0,
    # Source: Luengo-Fernandez R et al. Stroke 2013 - adjusted

    heart_failure_annual=15000.0,
    # Source: Dunlay SM et al. Circ HF 2011 - adjusted

    af_annual=8500.0,
    # Source: Kim MH et al. Circ CV Qual Outcomes 2011
    # Includes DOAC ($500/month), cardiology visits, monitoring

    ckd_stage_3a_annual=2500.0,
    # Source: Vupputuri S et al. Kidney Int 2014

    ckd_stage_3b_annual=4500.0,
    # Source: Vupputuri S et al. 2014

    ckd_stage_4_annual=8000.0,
    # Source: Smith DH et al. Am J Kidney Dis 2004 - adjusted

    esrd_annual=90000.0,
    # Source: USRDS Annual Data Report 2023, Chapter 9

    # --- Indirect Costs (Societal Perspective) ---
    daily_wage=240.0,
    # Source: BLS OEWS 2024 - median wage $60k/year

    absenteeism_acute_mi_days=7,
    # Source: Greiner W et al. Eur J Health Econ 2004

    absenteeism_stroke_days=30,
    # Source: Dewilde S et al. BMJ Open 2017

    absenteeism_hf_days=5,
    # Source: Liao L et al. JACC HF 2007

    disability_multiplier_stroke=0.20,
    # Source: Tanaka E et al. Stroke 2011

    disability_multiplier_hf=0.15,
    # Source: Heidenreich PA et al. Circulation 2013
)

# =============================================================================
# UK COSTS (2024 GBP)
# =============================================================================
# Price year: 2024
# Perspective: NHS (direct medical) + Societal (indirect)
# Sources: NHS Reference Costs 2022-23, NHS Drug Tariff, ONS ASHE
#
# Reference: NICE. Guide to the methods of technology appraisal 2013 (PMG9).
# Sections 5.4-5.5: Measuring and valuing health effects and costs.
# =============================================================================
UK_COSTS = CostInputs(
    currency="GBP",

    # --- Drug Costs (Monthly) ---
    ixa_001_monthly=400.0,
    # Source: Estimated UK PPRS price (placeholder)

    spironolactone_monthly=8.0,
    # Source: NHS Drug Tariff April 2024 - spironolactone 25mg x 28

    sglt2_inhibitor_monthly=35.0,
    # Source: NHS Drug Tariff 2024 - generic dapagliflozin (off-patent UK)

    background_therapy_monthly=40.0,
    # Source: NHS Drug Tariff 2024 - generic ACEi/ARB + amlodipine

    potassium_binder_monthly=300.0,
    # Source: NHS Drug Tariff 2024 - Patiromer (Veltassa)

    # --- Acute Event Costs ---
    mi_acute=8000.0,
    # Source: NHS Reference Costs 2022-23 - EB10A-C (STEMI/NSTEMI)

    stroke_acute=12000.0,  # Legacy: weighted average (deprecated)

    ischemic_stroke_acute=6000.0,
    # Source: NHS Reference Costs 2022-23 - AA22A-D (Ischemic Stroke)

    hemorrhagic_stroke_acute=9000.0,
    # Source: NHS Reference Costs 2022-23 - AA23A-C (ICH)

    tia_acute=850.0,
    # Source: NHS Reference Costs 2022-23 - Rapid Access TIA clinic pathway

    hf_admission=5500.0,
    # Source: NHS Reference Costs 2022-23 - EB03A-D (Heart Failure)

    af_acute=3500.0,
    # Source: NHS Reference Costs 2022-23 - EB07A-C (Cardiac arrhythmia)

    lab_test_cost_k=3.0,
    # Source: NHS Reference Costs 2022-23 - DAPS08 (Clinical Chemistry)

    # --- Annual Management Costs ---
    controlled_htn_annual=350.0,
    # Source: NICE CG127 costing report (adjusted to 2024)

    uncontrolled_htn_annual=550.0,
    # Source: NICE CG127 costing report (adjusted)

    post_mi_annual=2200.0,
    # Source: Luengo-Fernandez R et al. Heart 2006 (adjusted to 2024)

    post_stroke_annual=5500.0,
    # Source: Luengo-Fernandez R et al. Stroke 2013 (UK data)

    heart_failure_annual=6000.0,
    # Source: NICE TA388 Heart Failure ERG Report

    af_annual=2500.0,
    # Source: NHS Reference Costs + DOAC at NHS tariff prices

    ckd_stage_3a_annual=1200.0,
    # Source: Kerr M et al. Nephrol Dial Transplant 2012 (UK CKD costs)

    ckd_stage_3b_annual=2200.0,
    # Source: Kerr M et al. 2012

    ckd_stage_4_annual=3500.0,
    # Source: Kerr M et al. 2012

    esrd_annual=35000.0,
    # Source: NHS Reference Costs 2022-23 - Renal Dialysis (LD01-06)
    # Also: Kerr M et al. Estimating costs of CKD in UK. Nephrol Dial Transplant. 2012

    # --- Indirect Costs (Societal Perspective) ---
    daily_wage=160.0,
    # Source: ONS ASHE 2024 - median full-time wage £40k/year

    absenteeism_acute_mi_days=14,
    # Source: UK statutory sick pay provisions + clinical recovery

    absenteeism_stroke_days=60,
    # Source: Dewilde S et al. BMJ Open 2017 (UK cohort)

    absenteeism_hf_days=10,
    # Source: Clinical expert opinion

    disability_multiplier_stroke=0.30,
    # Source: Patel A et al. Stroke 2020 (UK productivity data)

    disability_multiplier_hf=0.20,
    # Source: Stewart S et al. Heart 2002
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

    # Atrial fibrillation (additive) - chronic anticoagulation and monitoring
    if getattr(patient, 'has_atrial_fibrillation', False):
        total_annual += costs.af_annual

    # Renal State Costs (Additive)
    r_state = getattr(patient, 'renal_state', None)
    r_val = r_state.value if hasattr(r_state, 'value') else str(r_state)

    if r_val == "ckd_stage_3a":
        total_annual += costs.ckd_stage_3a_annual
    elif r_val == "ckd_stage_3b":
        total_annual += costs.ckd_stage_3b_annual
    elif r_val == "ckd_stage_4":
        total_annual += costs.ckd_stage_4_annual
    elif r_val == "esrd":
        total_annual += costs.esrd_annual
    elif r_val == "renal_death":
        # No ongoing costs for deceased patients
        pass

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
    elif event_type == "new_af":
        return costs.af_acute
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
