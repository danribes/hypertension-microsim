# kfre.jl — Kidney Failure Risk Equation
# Reference: Tangri N, et al. JAMA. 2011;305(15):1553-1559.

# 2-year KFRE coefficients (4-variable model)
const KFRE_2Y_INTERCEPT = -0.2201
const KFRE_2Y_FEMALE    = -0.2240
const KFRE_2Y_AGE       = -0.0128   # centered at 60
const KFRE_2Y_EGFR      = -0.0576   # centered at 40
const KFRE_2Y_LOG_UACR  =  0.3479   # centered at log(100)
const KFRE_2Y_S0        =  0.9832

# 5-year KFRE coefficients
const KFRE_5Y_INTERCEPT =  0.4775
const KFRE_5Y_FEMALE    = -0.2635
const KFRE_5Y_AGE       = -0.0087
const KFRE_5Y_EGFR      = -0.0535
const KFRE_5Y_LOG_UACR  =  0.3411
const KFRE_5Y_S0        =  0.9365

# Decline rate thresholds
const KFRE_RAPID_THRESHOLD    = 0.30
const KFRE_MODERATE_THRESHOLD = 0.15
const KFRE_SLOW_THRESHOLD     = 0.05
const KFRE_RAPID_DECLINE      = 5.0
const KFRE_MODERATE_DECLINE   = 3.5
const KFRE_SLOW_DECLINE       = 2.0
const KFRE_STABLE_DECLINE     = 1.0

"""
    calculate_kfre_risk(age, sex, egfr, uacr; two_year=true) -> Float64

Calculate KFRE kidney failure risk (4-variable model).
"""
@inline function calculate_kfre_risk(
    age::Float64, sex::Int8, egfr::Float64, uacr::Float64;
    two_year::Bool=true,
)::Float64
    egfr_c = clamp(egfr, 5.0, 120.0)
    uacr_c = clamp(uacr, 1.0, 5000.0)
    female_ind = sex == SEX_FEMALE ? 1.0 : 0.0
    log_uacr = log(max(uacr_c, 1.0))

    if two_year
        lp = KFRE_2Y_INTERCEPT +
             KFRE_2Y_FEMALE * female_ind +
             KFRE_2Y_AGE * (age - 60.0) +
             KFRE_2Y_EGFR * (egfr_c - 40.0) +
             KFRE_2Y_LOG_UACR * (log_uacr - log(100.0))
        s0 = KFRE_2Y_S0
    else
        lp = KFRE_5Y_INTERCEPT +
             KFRE_5Y_FEMALE * female_ind +
             KFRE_5Y_AGE * (age - 60.0) +
             KFRE_5Y_EGFR * (egfr_c - 40.0) +
             KFRE_5Y_LOG_UACR * (log_uacr - log(100.0))
        s0 = KFRE_5Y_S0
    end

    risk = 1.0 - s0^exp(lp)
    return clamp(risk, 0.0001, 0.9999)
end

"""
    get_annual_egfr_decline(age, sex, egfr, uacr; kwargs...) -> Float64

Calculate expected annual eGFR decline using KFRE-informed model.
"""
@inline function get_annual_egfr_decline(
    age::Float64, sex::Int8, egfr::Float64, uacr::Float64;
    has_diabetes::Bool=false,
    on_sglt2i::Bool=false,
    sbp::Float64=130.0,
)::Float64
    if egfr < 60.0
        kfre_2yr = calculate_kfre_risk(age, sex, egfr, uacr; two_year=true)
        if kfre_2yr > KFRE_RAPID_THRESHOLD
            base_decline = KFRE_RAPID_DECLINE
        elseif kfre_2yr > KFRE_MODERATE_THRESHOLD
            base_decline = KFRE_MODERATE_DECLINE
        elseif kfre_2yr > KFRE_SLOW_THRESHOLD
            base_decline = KFRE_SLOW_DECLINE
        else
            base_decline = KFRE_STABLE_DECLINE
        end
    else
        if age < 40.0
            base_decline = 0.0
        elseif age < 65.0
            base_decline = 1.0
        else
            base_decline = 1.5
        end
        # Albuminuria effect
        if uacr >= 300.0
            base_decline += 2.0
        elseif uacr >= 30.0
            base_decline += 0.8
        end
    end

    dm_mult = has_diabetes ? 1.5 : 1.0
    sglt2_mult = on_sglt2i ? 0.61 : 1.0
    sbp_excess = max(0.0, sbp - 130.0)
    sbp_effect = 0.08 * (sbp_excess / 10.0)

    total = (base_decline + sbp_effect) * dm_mult * sglt2_mult
    return min(total, 15.0)
end
