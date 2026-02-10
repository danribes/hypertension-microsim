# costs.jl — Cost inputs and cost calculation functions

# ============================================================================
# CostInputs struct
# ============================================================================
struct CostInputs
    # Drug costs (monthly)
    ixa_001_monthly::Float64
    spironolactone_monthly::Float64
    sglt2_inhibitor_monthly::Float64
    background_therapy_monthly::Float64
    potassium_binder_monthly::Float64

    # Lab
    lab_test_cost_k::Float64

    # Acute event costs
    mi_acute::Float64
    ischemic_stroke_acute::Float64
    hemorrhagic_stroke_acute::Float64
    tia_acute::Float64
    hf_admission::Float64
    af_acute::Float64

    # Annual management — Cardiac
    controlled_htn_annual::Float64
    uncontrolled_htn_annual::Float64
    post_mi_annual::Float64
    post_stroke_annual::Float64
    heart_failure_annual::Float64
    af_annual::Float64

    # Annual management — Renal
    ckd_stage_3a_annual::Float64
    ckd_stage_3b_annual::Float64
    ckd_stage_4_annual::Float64
    esrd_annual::Float64

    # Indirect costs
    daily_wage::Float64
    absenteeism_acute_mi_days::Int
    absenteeism_stroke_days::Int
    absenteeism_hf_days::Int
    disability_multiplier_stroke::Float64
    disability_multiplier_hf::Float64
end

# US costs (2024 USD)
const US_COSTS = CostInputs(
    500.0, 15.0, 450.0, 75.0, 500.0,          # drugs
    15.0,                                       # lab
    25000.0, 15200.0, 22500.0, 2100.0, 18000.0, 8500.0,  # acute
    1200.0, 1800.0, 5500.0, 12000.0, 15000.0, 8500.0,     # annual cardiac
    2500.0, 4500.0, 8000.0, 90000.0,           # annual renal
    240.0, 7, 30, 5, 0.20, 0.15,               # indirect
)

# UK costs (2024 GBP)
const UK_COSTS = CostInputs(
    400.0, 8.0, 35.0, 40.0, 300.0,
    3.0,
    8000.0, 6000.0, 9000.0, 850.0, 5500.0, 3500.0,
    350.0, 550.0, 2200.0, 5500.0, 6000.0, 2500.0,
    1200.0, 2200.0, 3500.0, 35000.0,
    160.0, 14, 60, 10, 0.30, 0.20,
)

"""
    get_costs(country::Int8, psa::PSAParameters) -> CostInputs

Get cost inputs, overriding with PSA-sampled values where applicable.
"""
function get_costs(country::Int8, psa::PSAParameters)
    base = country == Int8(0) ? US_COSTS : UK_COSTS
    # Override PSA-varied costs
    return CostInputs(
        psa.cost_ixa_monthly,
        base.spironolactone_monthly,
        base.sglt2_inhibitor_monthly,
        base.background_therapy_monthly,
        base.potassium_binder_monthly,
        base.lab_test_cost_k,
        psa.cost_mi_acute,
        psa.cost_ischemic_stroke_acute,
        psa.cost_hemorrhagic_stroke_acute,
        base.tia_acute,
        psa.cost_hf_acute,
        base.af_acute,
        base.controlled_htn_annual,
        base.uncontrolled_htn_annual,
        base.post_mi_annual,
        psa.cost_post_stroke_annual,
        psa.cost_hf_annual,
        base.af_annual,
        base.ckd_stage_3a_annual,
        base.ckd_stage_3b_annual,
        base.ckd_stage_4_annual,
        psa.cost_esrd_annual,
        base.daily_wage,
        base.absenteeism_acute_mi_days,
        base.absenteeism_stroke_days,
        base.absenteeism_hf_days,
        base.disability_multiplier_stroke,
        base.disability_multiplier_hf,
    )
end

# ============================================================================
# Cost functions (per-patient, per-cycle)
# ============================================================================

"""Monthly drug cost based on treatment and SGLT2i status."""
@inline function get_drug_cost(treatment::Int8, on_sglt2::Int8, costs::CostInputs)::Float64
    total = costs.background_therapy_monthly
    if treatment == TX_IXA_001
        total += costs.ixa_001_monthly
    elseif treatment == TX_SPIRONOLACTONE
        total += costs.spironolactone_monthly
    end
    if on_sglt2 == Int8(1)
        total += costs.sglt2_inhibitor_monthly
    end
    return total
end

"""Monthly state management cost (cardiac + renal)."""
@inline function get_monthly_state_cost(
    cardiac::Int8, renal::Int8, sbp::Float64,
    has_af::Int8, costs::CostInputs,
)::Float64
    annual = 0.0

    # Cardiac
    if cardiac == CS_NO_ACUTE_EVENT
        annual += sbp < 140.0 ? costs.controlled_htn_annual : costs.uncontrolled_htn_annual
    elseif cardiac == CS_POST_MI
        annual += costs.post_mi_annual
    elseif cardiac == CS_POST_STROKE
        annual += costs.post_stroke_annual
    elseif cardiac == CS_CHRONIC_HF || cardiac == CS_ACUTE_HF
        annual += costs.heart_failure_annual
    else
        # Acute events, TIA, death — use controlled HTN as placeholder
        annual += sbp < 140.0 ? costs.controlled_htn_annual : costs.uncontrolled_htn_annual
    end

    # AF (additive)
    if has_af == Int8(1)
        annual += costs.af_annual
    end

    # Renal (additive)
    if renal == RS_CKD_STAGE_3A
        annual += costs.ckd_stage_3a_annual
    elseif renal == RS_CKD_STAGE_3B
        annual += costs.ckd_stage_3b_annual
    elseif renal == RS_CKD_STAGE_4
        annual += costs.ckd_stage_4_annual
    elseif renal == RS_ESRD
        annual += costs.esrd_annual
    end

    return annual / 12.0
end

"""One-time acute event cost."""
@inline function get_event_cost(event::Int8, costs::CostInputs)::Float64
    if event == CS_ACUTE_MI
        return costs.mi_acute
    elseif event == CS_ACUTE_ISCHEMIC_STROKE
        return costs.ischemic_stroke_acute
    elseif event == CS_ACUTE_HEMORRHAGIC_STROKE
        return costs.hemorrhagic_stroke_acute
    elseif event == CS_TIA
        return costs.tia_acute
    elseif event == CS_ACUTE_HF
        return costs.hf_admission
    else
        return 0.0
    end
end

"""AF event cost (one-time)."""
@inline get_af_event_cost(costs::CostInputs)::Float64 = costs.af_acute

"""Monthly productivity loss (chronic disability, working age <65 only)."""
@inline function get_monthly_productivity_loss(
    cardiac::Int8, age::Float64, costs::CostInputs,
)::Float64
    age >= 65.0 && return 0.0
    annual_wage = costs.daily_wage * 250.0
    if cardiac == CS_POST_STROKE
        return (annual_wage * costs.disability_multiplier_stroke) / 12.0
    elseif cardiac == CS_CHRONIC_HF || cardiac == CS_ACUTE_HF
        return (annual_wage * costs.disability_multiplier_hf) / 12.0
    end
    return 0.0
end

"""One-time absenteeism cost for acute events (working age <65 only)."""
@inline function get_acute_absenteeism_cost(event::Int8, age::Float64, costs::CostInputs)::Float64
    age >= 65.0 && return 0.0
    days = 0
    if event == CS_ACUTE_MI
        days = costs.absenteeism_acute_mi_days
    elseif event == CS_ACUTE_ISCHEMIC_STROKE || event == CS_ACUTE_HEMORRHAGIC_STROKE
        days = costs.absenteeism_stroke_days
    elseif event == CS_TIA
        days = 3
    elseif event == CS_ACUTE_HF
        days = costs.absenteeism_hf_days
    end
    return days * costs.daily_wage
end
