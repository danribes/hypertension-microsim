# transitions.jl — CV event probability calculation, competing risks, event sampling

using Random

# Case fatality rates (30-day mortality)
const CF_MI                = 0.08
const CF_ISCHEMIC_STROKE   = 0.10
const CF_HEMORRHAGIC_STROKE= 0.25
const CF_HF                = 0.05

# Post-event annual mortality
const PM_POST_MI_YR1       = 0.05
const PM_POST_MI_AFTER     = 0.03
const PM_POST_STROKE_YR1   = 0.10
const PM_POST_STROKE_AFTER = 0.05
const PM_HF                = 0.08
const PM_ESRD              = 0.15

# Prior event multipliers
const PRIOR_MI_MULT     = 2.5
const PRIOR_STROKE_MULT = 3.0
const PRIOR_HF_MULT     = 2.0
const PRIOR_TIA_MULT    = 2.0

# Stroke subtype baseline
const BASE_HEMORRHAGIC_FRAC = 0.15

# ============================================================================
# Stroke subtype distribution
# ============================================================================
@inline function get_stroke_subtype_fractions(
    age::Float64, sbp::Float64, has_af::Int8, prior_tia::Int32,
    use_dynamic::Bool,
)::Tuple{Float64, Float64}
    !use_dynamic && return (0.85, 0.15)

    adj = 0.0
    if age >= 80.0
        adj += 0.05
    elseif age >= 70.0
        adj += 0.03
    elseif age >= 60.0
        adj += 0.01
    end

    if sbp >= 180.0
        adj += 0.10
    elseif sbp >= 160.0
        adj += 0.05
    elseif sbp >= 140.0
        adj += 0.02
    end

    if has_af == Int8(1)
        adj -= 0.05
    end
    if prior_tia > 0
        adj -= 0.03
    end

    hem = clamp(BASE_HEMORRHAGIC_FRAC + adj, 0.05, 0.40)
    return (1.0 - hem, hem)
end

# ============================================================================
# CV death calculation
# ============================================================================
@inline function calc_cv_death_monthly(
    cardiac::Int8, renal::Int8, has_hf::Int8,
    time_since_cv::Float64,
)::Float64
    base_annual = 0.01
    primary = base_annual

    if cardiac == CS_POST_MI
        primary = (!isnan(time_since_cv) && time_since_cv <= 12.0) ?
            max(primary, PM_POST_MI_YR1) : max(primary, PM_POST_MI_AFTER)
    elseif cardiac == CS_POST_STROKE
        primary = (!isnan(time_since_cv) && time_since_cv <= 12.0) ?
            max(primary, PM_POST_STROKE_YR1) : max(primary, PM_POST_STROKE_AFTER)
    elseif cardiac == CS_CHRONIC_HF
        primary = max(primary, PM_HF)
    end

    incr = 0.0
    if has_hf == Int8(1) && cardiac != CS_CHRONIC_HF
        incr += 0.03
    end
    if renal == RS_ESRD
        incr += PM_ESRD * 0.6  # CV component of ESRD mortality
    end

    annual = min(primary + incr, 0.20)
    return annual_to_monthly_prob(annual)
end

# ============================================================================
# Treatment risk factor (phenotype-based efficacy)
# ============================================================================
@inline function get_treatment_risk_factor(
    treatment_response_mod::Float64, outcome_coeff::Float64,
)::Float64
    effect = treatment_response_mod - 1.0
    factor = 1.0 - effect * outcome_coeff
    return clamp(factor, 0.50, 1.50)
end

# Efficacy coefficients by outcome
const EFFICACY_MI     = 0.30
const EFFICACY_STROKE = 0.40
const EFFICACY_HF     = 0.50
const EFFICACY_ESRD   = 0.55
const EFFICACY_DEATH  = 0.35

# ============================================================================
# Dipping status risk multiplier
# ============================================================================
@inline function dipping_risk_mult(dipping::Int8)::Float64
    dipping == Int8(2) && return 1.8   # reverse dipper
    dipping == Int8(1) && return 1.4   # non-dipper
    return 1.0
end

# ============================================================================
# Transition probability struct
# ============================================================================
mutable struct TransProbs
    to_mi::Float64
    to_ischemic_stroke::Float64
    to_hemorrhagic_stroke::Float64
    to_tia::Float64
    to_hf::Float64
    to_cv_death::Float64
    to_non_cv_death::Float64
end
TransProbs() = TransProbs(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

# ============================================================================
# Competing risks adjustment
# ============================================================================
@inline function prob_to_hazard(p::Float64)::Float64
    pc = clamp(p, 0.0, 0.9999)
    return pc > 0.0 ? -log(1.0 - pc) : 0.0
end

function apply_competing_risks!(tp::TransProbs, use_cr::Bool)
    if !use_cr
        # Legacy 95% cap
        total = tp.to_cv_death + tp.to_non_cv_death + tp.to_mi +
                tp.to_ischemic_stroke + tp.to_hemorrhagic_stroke +
                tp.to_tia + tp.to_hf
        if total > 0.95
            s = 0.95 / total
            tp.to_cv_death *= s
            tp.to_non_cv_death *= s
            tp.to_mi *= s
            tp.to_ischemic_stroke *= s
            tp.to_hemorrhagic_stroke *= s
            tp.to_tia *= s
            tp.to_hf *= s
        end
        return
    end

    h_cv  = prob_to_hazard(tp.to_cv_death)
    h_ncv = prob_to_hazard(tp.to_non_cv_death)
    h_mi  = prob_to_hazard(tp.to_mi)
    h_is  = prob_to_hazard(tp.to_ischemic_stroke)
    h_hs  = prob_to_hazard(tp.to_hemorrhagic_stroke)
    h_tia = prob_to_hazard(tp.to_tia)
    h_hf  = prob_to_hazard(tp.to_hf)

    H = h_cv + h_ncv + h_mi + h_is + h_hs + h_tia + h_hf
    H <= 0.0 && return

    event_prob = 1.0 - exp(-H)
    tp.to_cv_death = (h_cv / H) * event_prob
    tp.to_non_cv_death = (h_ncv / H) * event_prob
    tp.to_mi = (h_mi / H) * event_prob
    tp.to_ischemic_stroke = (h_is / H) * event_prob
    tp.to_hemorrhagic_stroke = (h_hs / H) * event_prob
    tp.to_tia = (h_tia / H) * event_prob
    tp.to_hf = (h_hf / H) * event_prob
end

# ============================================================================
# Full transition calculation for one patient
# ============================================================================
function calculate_transitions!(
    tp::TransProbs, p::PatientArrays, i::Int, cfg::SimConfig, psa::PSAParameters,
)
    tp.to_mi = 0.0; tp.to_ischemic_stroke = 0.0; tp.to_hemorrhagic_stroke = 0.0
    tp.to_tia = 0.0; tp.to_hf = 0.0; tp.to_cv_death = 0.0; tp.to_non_cv_death = 0.0

    cs = p.cardiac_state[i]

    # Acute state case fatality
    if cs == CS_ACUTE_MI
        tp.to_cv_death = CF_MI; return
    elseif cs == CS_ACUTE_ISCHEMIC_STROKE
        tp.to_cv_death = CF_ISCHEMIC_STROKE; return
    elseif cs == CS_ACUTE_HEMORRHAGIC_STROKE
        tp.to_cv_death = CF_HEMORRHAGIC_STROKE; return
    elseif cs == CS_ACUTE_HF
        tp.to_cv_death = CF_HF; return
    end

    # Prior event multipliers
    mi_mult = p.prior_mi_count[i] > 0 ? PRIOR_MI_MULT : 1.0
    stroke_mult = p.prior_stroke_count[i] > 0 ? PRIOR_STROKE_MULT : 1.0
    if p.prior_tia_count[i] > 0
        stroke_mult *= PRIOR_TIA_MULT
    end

    risk_sbp = p.true_mean_sbp[i]
    drm = dipping_risk_mult(p.nocturnal_dipping_status[i])

    # MI probability from PREVENT
    base_mi = get_monthly_event_prob(
        p.age[i], p.sex[i], risk_sbp, p.egfr[i], RISK_PROP_MI;
        has_diabetes = p.has_diabetes[i] == Int8(1),
        is_smoker = p.is_smoker[i] == Int8(1),
        total_cholesterol = p.total_cholesterol[i],
        hdl_cholesterol = p.hdl_cholesterol[i],
        bmi = p.bmi[i],
        prior_event_multiplier = mi_mult,
    )
    mi_pheno = p.mod_mi[i]
    mi_tx = get_treatment_risk_factor(p.treatment_response_modifier[i], EFFICACY_MI)
    tp.to_mi = base_mi * mi_pheno * drm * mi_tx

    # Stroke probability
    base_stroke = get_monthly_event_prob(
        p.age[i], p.sex[i], risk_sbp, p.egfr[i], RISK_PROP_STROKE;
        has_diabetes = p.has_diabetes[i] == Int8(1),
        is_smoker = p.is_smoker[i] == Int8(1),
        total_cholesterol = p.total_cholesterol[i],
        hdl_cholesterol = p.hdl_cholesterol[i],
        bmi = p.bmi[i],
        prior_event_multiplier = stroke_mult,
    )
    stroke_pheno = p.mod_stroke[i]
    stroke_drm = drm > 1.0 ? drm * 1.1 : 1.0
    stroke_tx = get_treatment_risk_factor(p.treatment_response_modifier[i], EFFICACY_STROKE)
    total_stroke = base_stroke * stroke_pheno * stroke_drm * stroke_tx

    isch_frac, hem_frac = get_stroke_subtype_fractions(
        p.age[i], risk_sbp, p.has_atrial_fibrillation[i],
        p.prior_tia_count[i], cfg.use_dynamic_stroke_subtypes,
    )
    tp.to_ischemic_stroke = total_stroke * isch_frac
    tp.to_hemorrhagic_stroke = total_stroke * hem_frac

    # TIA
    tia_base = tp.to_ischemic_stroke * 0.33
    if p.has_atrial_fibrillation[i] == Int8(1)
        tia_base *= 1.5
    end
    tp.to_tia = tia_base

    # HF
    if p.has_heart_failure[i] == Int8(0)
        sglt2_mult = p.on_sglt2_inhibitor[i] == Int8(1) ? 0.70 : 1.0
        base_hf = get_monthly_event_prob(
            p.age[i], p.sex[i], risk_sbp, p.egfr[i], RISK_PROP_HF;
            has_diabetes = p.has_diabetes[i] == Int8(1),
            is_smoker = p.is_smoker[i] == Int8(1),
            total_cholesterol = p.total_cholesterol[i],
            hdl_cholesterol = p.hdl_cholesterol[i],
            bmi = p.bmi[i],
        )
        hf_pheno = p.mod_hf[i]
        hf_tx = get_treatment_risk_factor(p.treatment_response_modifier[i], EFFICACY_HF)
        tp.to_hf = base_hf * hf_pheno * sglt2_mult * hf_tx
    end

    # CV Death
    base_cv = calc_cv_death_monthly(
        cs, p.renal_state[i], p.has_heart_failure[i], p.time_since_last_cv_event[i],
    )
    death_pheno = p.mod_death[i]
    death_tx = get_treatment_risk_factor(p.treatment_response_modifier[i], EFFICACY_DEATH)
    tp.to_cv_death = base_cv * death_pheno * death_tx

    # Non-CV Death from life tables
    bg_mort = get_annual_mortality(p.age[i], p.sex[i], cfg.life_table_country)
    tp.to_non_cv_death = annual_to_monthly_prob(bg_mort)

    # Competing risks
    apply_competing_risks!(tp, cfg.use_competing_risks)
end

# ============================================================================
# Event sampling (multinomial)
# ============================================================================
"""
    sample_event(tp, cardiac, rng) -> Int8

Sample next event. Returns new CardiacState, or -1 for no new event.
"""
@inline function sample_event(tp::TransProbs, cardiac::Int8, rng::AbstractRNG)::Int8

    # Cumulative sum sampling
    u = rand(rng)
    cum = tp.to_cv_death
    cum >= u && return CS_CV_DEATH
    cum += tp.to_non_cv_death
    cum >= u && return CS_NON_CV_DEATH
    cum += tp.to_mi
    cum >= u && return CS_ACUTE_MI
    cum += tp.to_hemorrhagic_stroke
    cum >= u && return CS_ACUTE_HEMORRHAGIC_STROKE
    cum += tp.to_ischemic_stroke
    cum >= u && return CS_ACUTE_ISCHEMIC_STROKE
    cum += tp.to_hf
    cum >= u && return CS_ACUTE_HF
    cum += tp.to_tia
    cum >= u && return CS_TIA

    # No event — check acute→chronic transitions
    if cardiac == CS_ACUTE_MI
        return CS_POST_MI
    elseif cardiac == CS_ACUTE_ISCHEMIC_STROKE || cardiac == CS_ACUTE_HEMORRHAGIC_STROKE
        return CS_POST_STROKE
    elseif cardiac == CS_ACUTE_HF
        return CS_CHRONIC_HF
    elseif cardiac == CS_TIA
        return CS_NO_ACUTE_EVENT
    end

    return Int8(-1)  # no change
end

# ============================================================================
# TIA → Stroke conversion
# ============================================================================
@inline function check_tia_to_stroke(
    prior_tia::Int32, time_since_tia::Float64,
    sbp::Float64, has_dm::Int8, has_af::Int8,
    rng::AbstractRNG,
)::Bool
    prior_tia == 0 && return false
    isnan(time_since_tia) && return false
    time_since_tia > 3.0 && return false

    prob = if time_since_tia <= 1.0
        0.05
    elseif time_since_tia <= 2.0
        0.03
    else
        0.02
    end

    sbp >= 140.0 && (prob *= 1.5)
    has_dm == Int8(1) && (prob *= 1.3)
    has_af == Int8(1) && (prob *= 1.4)
    prob = min(prob, 0.15)

    return rand(rng) < prob
end

# ============================================================================
# ESRD mortality
# ============================================================================
@inline function check_esrd_mortality(
    renal::Int8, age::Float64, has_dm::Int8, rng::AbstractRNG,
)::Bool
    renal != RS_ESRD && return false
    annual = PM_ESRD * 0.4  # non-CV component
    age >= 75.0 && (annual *= 1.5)
    age >= 65.0 && age < 75.0 && (annual *= 1.2)
    has_dm == Int8(1) && (annual *= 1.3)
    monthly = annual_to_monthly_prob(annual)
    return rand(rng) < monthly
end
