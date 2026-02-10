# utilities.jl — Health state utility values and QALY calculation

# Baseline utility by age bracket (resistant HTN population)
const BASELINE_UTILITY_AGES   = [40, 50, 60, 70, 80, 90]
const BASELINE_UTILITY_VALUES = [0.87, 0.84, 0.81, 0.77, 0.72, 0.67]

# State disutilities
const DISUTIL_CONTROLLED_HTN   = 0.00
const DISUTIL_UNCONTROLLED_HTN = 0.04
const DISUTIL_POST_MI          = 0.12
const DISUTIL_POST_STROKE      = 0.18
const DISUTIL_ACUTE_HF         = 0.25
const DISUTIL_CHRONIC_HF       = 0.15
const DISUTIL_CKD_3A           = 0.01
const DISUTIL_CKD_3B           = 0.03
const DISUTIL_CKD_4            = 0.06
const DISUTIL_ESRD             = 0.35
const DISUTIL_DIABETES         = 0.04
const DISUTIL_AF               = 0.05
const DISUTIL_HYPERKALEMIA     = 0.03
const DISUTIL_MCI              = 0.05
const DISUTIL_DEMENTIA         = 0.30

# Acute event disutilities (event month only)
const ACUTE_DISUTIL_MI              = 0.20
const ACUTE_DISUTIL_ISCHEMIC_STROKE = 0.35
const ACUTE_DISUTIL_HEMORRHAGIC_STROKE = 0.50
const ACUTE_DISUTIL_TIA             = 0.10
const ACUTE_DISUTIL_HF              = 0.25
const ACUTE_DISUTIL_AF              = 0.15

"""
    get_utility(age, cardiac, renal, neuro, sbp, has_dm, has_af, has_hyperK,
                num_antihtn, psa) -> Float64

Calculate utility value using additive disutility model.
"""
@inline function get_utility(
    age::Float64, cardiac::Int8, renal::Int8, neuro::Int8,
    sbp::Float64,
    has_dm::Int8, has_af::Int8, has_hyperK::Int8,
    num_antihtn::Int32,
    psa::PSAParameters,
)::Float64
    # Baseline utility by age
    baseline = 0.67  # default (90+)
    for i in eachindex(BASELINE_UTILITY_AGES)
        if age < BASELINE_UTILITY_AGES[i] + 10
            baseline = BASELINE_UTILITY_VALUES[i]
            break
        end
    end

    decrement = 0.0

    # Cardiac state
    if cardiac == CS_NO_ACUTE_EVENT
        # SBP gradient
        if sbp < 130.0
            # well controlled
        elseif sbp < 140.0
            decrement += 0.01 * (sbp - 130.0) / 10.0
        elseif sbp < 160.0
            decrement += 0.01 + 0.03 * (sbp - 140.0) / 20.0
        elseif sbp < 180.0
            decrement += 0.04 + 0.02 * (sbp - 160.0) / 20.0
        else
            decrement += min(0.08, 0.06 + 0.02 * (sbp - 180.0) / 20.0)
        end
    elseif cardiac == CS_ACUTE_MI
        decrement += ACUTE_DISUTIL_MI
    elseif cardiac == CS_POST_MI
        decrement += psa.disutility_post_mi
    elseif cardiac == CS_ACUTE_ISCHEMIC_STROKE
        decrement += ACUTE_DISUTIL_ISCHEMIC_STROKE
    elseif cardiac == CS_ACUTE_HEMORRHAGIC_STROKE
        decrement += ACUTE_DISUTIL_HEMORRHAGIC_STROKE
    elseif cardiac == CS_POST_STROKE
        decrement += psa.disutility_post_stroke
    elseif cardiac == CS_TIA
        decrement += ACUTE_DISUTIL_TIA
    elseif cardiac == CS_ACUTE_HF
        decrement += ACUTE_DISUTIL_HF
    elseif cardiac == CS_CHRONIC_HF
        decrement += psa.disutility_chronic_hf
    end

    # Renal state
    if renal == RS_CKD_STAGE_3A
        decrement += DISUTIL_CKD_3A
    elseif renal == RS_CKD_STAGE_3B
        decrement += DISUTIL_CKD_3B
    elseif renal == RS_CKD_STAGE_4
        decrement += DISUTIL_CKD_4
    elseif renal == RS_ESRD
        decrement += psa.disutility_esrd
    end

    # Neuro
    if neuro == NS_MCI
        decrement += DISUTIL_MCI
    elseif neuro == NS_DEMENTIA
        decrement += psa.disutility_dementia
    end

    # Comorbidities
    if has_dm == Int8(1)
        decrement += DISUTIL_DIABETES
    end
    if has_af == Int8(1)
        decrement += DISUTIL_AF
    end
    if has_hyperK == Int8(1)
        decrement += DISUTIL_HYPERKALEMIA
    end

    # Resistant HTN burden
    if num_antihtn >= 3 && sbp >= 140.0
        decrement += 0.01 + 0.01 * min(1.0, (sbp - 140.0) / 40.0)
    end

    return max(0.0, baseline - decrement)
end

"""
    calculate_monthly_qaly(utility, time_months, discount_rate, cycle_length, use_half_cycle) -> Float64
"""
@inline function calculate_monthly_qaly(
    utility::Float64,
    time_months::Float64,
    discount_rate::Float64,
    cycle_length::Float64,
    use_half_cycle::Bool,
)::Float64
    monthly_qaly = utility / 12.0

    adj_months = use_half_cycle ? time_months + 0.5 * cycle_length : time_months
    years = adj_months / 12.0
    df = 1.0 / (1.0 + discount_rate)^years

    return monthly_qaly * df
end

"""
    get_discount_factor(time_months, discount_rate, cycle_length, use_half_cycle) -> Float64
"""
@inline function get_discount_factor(
    time_months::Float64,
    discount_rate::Float64,
    cycle_length::Float64,
    use_half_cycle::Bool,
)::Float64
    adj = use_half_cycle ? time_months + 0.5 * cycle_length : time_months
    years = adj / 12.0
    return 1.0 / (1.0 + discount_rate)^years
end
