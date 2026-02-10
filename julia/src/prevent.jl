# prevent.jl — PREVENT cardiovascular risk equations
# Reference: Khan SS, et al. Circulation. 2024;149(6):430-449.

# PREVENT coefficients — Female
const PREV_F_INTERCEPT        = -6.97
const PREV_F_LN_AGE           =  0.976
const PREV_F_LN_SBP           =  1.008
const PREV_F_BP_TREATED       =  0.162
const PREV_F_LN_SBP_X_BPT    = -0.094
const PREV_F_DIABETES         =  0.626
const PREV_F_SMOKER           =  0.499
const PREV_F_LN_EGFR          = -0.478
const PREV_F_LN_TC            =  0.252
const PREV_F_LN_HDL           = -0.436
const PREV_F_LN_BMI           =  0.327
const PREV_F_S0               =  0.9792

# PREVENT coefficients — Male
const PREV_M_INTERCEPT        = -5.85
const PREV_M_LN_AGE           =  0.847
const PREV_M_LN_SBP           =  0.982
const PREV_M_BP_TREATED       =  0.147
const PREV_M_LN_SBP_X_BPT    = -0.082
const PREV_M_DIABETES         =  0.671
const PREV_M_SMOKER           =  0.546
const PREV_M_LN_EGFR          = -0.395
const PREV_M_LN_TC            =  0.228
const PREV_M_LN_HDL           = -0.389
const PREV_M_LN_BMI           =  0.301
const PREV_M_S0               =  0.9712

# Risk proportions for event decomposition
const RISK_PROP_MI    = 0.30
const RISK_PROP_STROKE = 0.25
const RISK_PROP_HF    = 0.25

# RR per 10 mmHg SBP reduction (Ettehad et al. Lancet 2016)
const RR_STROKE_PER10 = 0.64
const RR_MI_PER10     = 0.78
const RR_HF_PER10     = 0.72
const RR_CVD_PER10    = 0.75

"""
    calculate_prevent_risk(age, sex, sbp, egfr; kwargs...) -> Float64

Calculate 10-year total CVD risk using PREVENT equations.
`sex`: SEX_MALE or SEX_FEMALE (Int8).
"""
@inline function calculate_prevent_risk(
    age::Float64, sex::Int8, sbp::Float64, egfr::Float64;
    bp_treated::Bool=true,
    has_diabetes::Bool=false,
    is_smoker::Bool=false,
    total_cholesterol::Float64=200.0,
    hdl_cholesterol::Float64=50.0,
    bmi::Float64=28.0,
    uacr::Float64=NaN,
)::Float64
    # Clamp age to valid PREVENT range
    age_c = clamp(age, 30.0, 79.0)

    ln_age = log(age_c)
    ln_sbp = log(clamp(sbp, 80.0, 220.0))
    ln_egfr = log(clamp(egfr, 15.0, 120.0))
    ln_tc = log(clamp(total_cholesterol, 100.0, 400.0))
    ln_hdl = log(clamp(hdl_cholesterol, 20.0, 100.0))
    ln_bmi = log(clamp(bmi, 15.0, 50.0))

    bp_val = bp_treated ? 1.0 : 0.0
    dm_val = has_diabetes ? 1.0 : 0.0
    sm_val = is_smoker ? 1.0 : 0.0

    if sex == SEX_FEMALE
        xb = PREV_F_INTERCEPT +
             PREV_F_LN_AGE * ln_age +
             PREV_F_LN_SBP * ln_sbp +
             PREV_F_BP_TREATED * bp_val +
             PREV_F_LN_SBP_X_BPT * ln_sbp * bp_val +
             PREV_F_DIABETES * dm_val +
             PREV_F_SMOKER * sm_val +
             PREV_F_LN_EGFR * ln_egfr +
             PREV_F_LN_TC * ln_tc +
             PREV_F_LN_HDL * ln_hdl +
             PREV_F_LN_BMI * ln_bmi
        s0 = PREV_F_S0
    else
        xb = PREV_M_INTERCEPT +
             PREV_M_LN_AGE * ln_age +
             PREV_M_LN_SBP * ln_sbp +
             PREV_M_BP_TREATED * bp_val +
             PREV_M_LN_SBP_X_BPT * ln_sbp * bp_val +
             PREV_M_DIABETES * dm_val +
             PREV_M_SMOKER * sm_val +
             PREV_M_LN_EGFR * ln_egfr +
             PREV_M_LN_TC * ln_tc +
             PREV_M_LN_HDL * ln_hdl +
             PREV_M_LN_BMI * ln_bmi
        s0 = PREV_M_S0
    end

    # Optional UACR enhancement
    if !isnan(uacr) && uacr > 30.0
        ln_uacr = log(clamp(uacr, 1.0, 5000.0))
        xb += 0.15 * (ln_uacr - log(30.0))
    end

    risk = 1.0 - s0^exp(xb)
    return clamp(risk, 0.001, 0.999)
end

# ============================================================================
# Probability conversion utilities
# ============================================================================

@inline function annual_to_monthly_prob(p::Float64)::Float64
    p_c = clamp(p, 0.0, 0.999)
    return 1.0 - (1.0 - p_c)^(1.0/12.0)
end

@inline function ten_year_to_annual_prob(p::Float64)::Float64
    p_c = clamp(p, 0.0, 0.999)
    return 1.0 - (1.0 - p_c)^0.1
end

@inline function ten_year_to_monthly_prob(p::Float64)::Float64
    return annual_to_monthly_prob(ten_year_to_annual_prob(p))
end

# ============================================================================
# Event-specific risk from PREVENT total CVD
# ============================================================================

@inline function calculate_event_specific_risk(total_cvd::Float64, proportion::Float64)::Float64
    return total_cvd * proportion
end

"""
    get_monthly_event_prob(age, sex, sbp, egfr, proportion; kwargs...) -> Float64

Get monthly probability of a specific CV event (MI, stroke, HF) from PREVENT.
"""
@inline function get_monthly_event_prob(
    age::Float64, sex::Int8, sbp::Float64, egfr::Float64,
    proportion::Float64;
    has_diabetes::Bool=false,
    is_smoker::Bool=false,
    total_cholesterol::Float64=200.0,
    hdl_cholesterol::Float64=50.0,
    bmi::Float64=28.0,
    prior_event_multiplier::Float64=1.0,
)::Float64
    ten_yr_cvd = calculate_prevent_risk(
        age, sex, sbp, egfr;
        has_diabetes=has_diabetes, is_smoker=is_smoker,
        total_cholesterol=total_cholesterol,
        hdl_cholesterol=hdl_cholesterol, bmi=bmi,
    )
    ten_yr_event = ten_yr_cvd * proportion * prior_event_multiplier
    return ten_year_to_monthly_prob(ten_yr_event)
end
