# treatment.jl — Treatment assignment, adherence, discontinuation, hyperkalemia, AF, neuro

using Random

# Treatment effect parameters (defaults — overridden by PSA)
const TX_IXA_SBP_MEAN  = 20.0
const TX_IXA_SBP_SD    = 6.0
const TX_IXA_DISC_RATE = 0.08
const TX_SPIRO_SBP_MEAN  = 9.0
const TX_SPIRO_SBP_SD    = 6.0
const TX_SPIRO_DISC_RATE = 0.18
const TX_SC_SBP_MEAN   = 3.0
const TX_SC_SBP_SD     = 5.0
const TX_SC_DISC_RATE  = 0.10

# AF base incidence by age
const AF_AGE_BRACKETS = [40, 50, 60, 70, 80]
const AF_BASE_RATES   = [0.002, 0.004, 0.010, 0.025, 0.050]

# Neuro base rates
const NEURO_NORMAL_TO_MCI = 0.02
const NEURO_MCI_TO_DEM    = 0.10
const NEURO_NORMAL_TO_DEM = 0.005

# ============================================================================
# Treatment assignment (for a single patient)
# ============================================================================
@inline function assign_treatment!(
    p::PatientArrays, i::Int, tx::Int8, psa::PSAParameters, rng::AbstractRNG,
)
    p.treatment[i] = tx

    # Determine effect parameters
    if tx == TX_IXA_001
        mean_eff = psa.ixa_sbp_mean
        sd_eff = psa.ixa_sbp_sd
    elseif tx == TX_SPIRONOLACTONE
        mean_eff = psa.spiro_sbp_mean
        sd_eff = psa.spiro_sbp_sd
    else
        mean_eff = TX_SC_SBP_MEAN
        sd_eff = TX_SC_SBP_SD
    end

    # Sample individual response
    reduction = max(0.0, mean_eff + sd_eff * randn(rng))

    # Apply treatment response modifier (PA, RAS, etc.)
    reduction *= p.treatment_response_modifier[i]

    # Store base effect
    p.base_treatment_effect[i] = reduction

    # Apply adherence
    if p.is_adherent[i] == Int8(0)
        reduction *= 0.3
    end

    p.treatment_effect_mmhg[i] = reduction
end

# ============================================================================
# Update effect for adherence change
# ============================================================================
@inline function update_effect_for_adherence!(p::PatientArrays, i::Int)
    eff = p.base_treatment_effect[i]
    if p.is_adherent[i] == Int8(0)
        eff *= 0.3
    end
    p.treatment_effect_mmhg[i] = eff
end

# ============================================================================
# Adherence transitions
# ============================================================================
@inline function check_adherence_change!(p::PatientArrays, i::Int, rng::AbstractRNG)::Bool
    if p.is_adherent[i] == Int8(1)
        # Adherent → Non-adherent
        time_on = p.time_in_simulation[i]
        base_annual = time_on <= 6.0 ? 0.20 : (time_on <= 12.0 ? 0.12 : 0.08)

        demo_mult = 1.0
        age = p.age[i]
        age < 40.0 && (demo_mult *= 1.5)
        age >= 40.0 && age < 50.0 && (demo_mult *= 1.3)
        age > 75.0 && (demo_mult *= 1.2)

        sdi = p.sdi_score[i]
        sdi > 75.0 && (demo_mult *= 1.4)
        sdi > 50.0 && sdi <= 75.0 && (demo_mult *= 1.2)
        age < 50.0 && sdi > 75.0 && (demo_mult *= 1.2)

        tx_mult = 1.0
        tx = p.treatment[i]
        if tx == TX_IXA_001
            tx_mult = 0.48
        elseif tx == TX_SPIRONOLACTONE
            tx_mult = p.sex[i] == SEX_MALE ? 1.4 : 1.2
            p.hyperkalemia_history[i] > 0 && (tx_mult *= 1.3)
        end

        # Post-event boost
        tscv = p.time_since_last_cv_event[i]
        if !isnan(tscv) && tscv < 12.0
            demo_mult *= 0.7
        end

        annual_prob = min(base_annual * demo_mult * tx_mult, 0.50)
        monthly = annual_to_monthly_prob(annual_prob)

        if rand(rng) < monthly
            p.is_adherent[i] = Int8(0)
            p.time_since_adherence_change[i] = 0.0
            return true
        end
    else
        # Non-adherent → Adherent
        annual_prob = 0.05
        tscv = p.time_since_last_cv_event[i]
        if !isnan(tscv) && tscv < 6.0
            annual_prob = 0.30
        end
        p.current_sbp[i] >= 180.0 && (annual_prob += 0.10)

        monthly = annual_to_monthly_prob(annual_prob)
        if rand(rng) < monthly
            p.is_adherent[i] = Int8(1)
            p.time_since_adherence_change[i] = 0.0
            return true
        end
    end

    p.time_since_adherence_change[i] += 1.0 / 12.0
    return false
end

# ============================================================================
# Hyperkalemia management
# ============================================================================
"""Returns (action_code, additional_cost, treatment_stopped)
action_code: 0=none, 1=monitor, 2=reduce_dose, 3=start_binder, 4=stop_treatment"""
@inline function manage_hyperkalemia!(
    p::PatientArrays, i::Int, costs::CostInputs, rng::AbstractRNG,
)::Tuple{Int8, Float64, Bool}
    p.treatment[i] != TX_SPIRONOLACTONE && return (Int8(0), 0.0, false)

    k = p.serum_potassium[i]

    # Severe (K+ > 6.0): stop
    if k > 6.0
        p.hyperkalemia_history[i] += 1
        return (Int8(4), 0.0, true)
    end

    # Moderate (5.5-6.0): binder or dose reduction
    if k > 5.5
        if p.on_potassium_binder[i] == Int8(0)
            p.on_potassium_binder[i] = Int8(1)
            p.serum_potassium[i] -= 0.3
            p.hyperkalemia_history[i] += 1
            return (Int8(3), costs.potassium_binder_monthly, false)
        elseif p.mra_dose_reduced[i] == Int8(0)
            p.mra_dose_reduced[i] = Int8(1)
            p.treatment_effect_mmhg[i] *= 0.5
            p.base_treatment_effect[i] *= 0.5
            return (Int8(2), 0.0, false)
        else
            p.hyperkalemia_history[i] += 1
            return (Int8(4), 0.0, true)
        end
    end

    # Mild (5.0-5.5): maybe reduce dose
    if k > 5.0 && p.mra_dose_reduced[i] == Int8(0)
        if rand(rng) < 0.3
            p.mra_dose_reduced[i] = Int8(1)
            p.treatment_effect_mmhg[i] *= 0.5
            p.base_treatment_effect[i] *= 0.5
            return (Int8(2), 0.0, false)
        end
        return (Int8(1), 0.0, false)
    end

    return (Int8(0), 0.0, false)
end

# ============================================================================
# Treatment discontinuation
# ============================================================================
@inline function check_discontinuation(
    p::PatientArrays, i::Int, psa::PSAParameters, rng::AbstractRNG,
)::Bool
    tx = p.treatment[i]
    tx == TX_STANDARD_CARE && return false

    base_rate = tx == TX_IXA_001 ? psa.discontinuation_rate_ixa : psa.discontinuation_rate_spiro

    # Responder adjustment
    sbp_red = p.treatment_effect_mmhg[i]
    resp_mult = if sbp_red >= 15.0
        0.6
    elseif sbp_red >= 10.0
        0.8
    elseif sbp_red < 5.0
        1.3
    else
        1.0
    end

    # Time on treatment
    tot = p.time_in_simulation[i]
    time_mult = if tot <= 3.0
        1.5
    elseif tot <= 6.0
        1.2
    elseif tot >= 24.0
        0.8
    else
        1.0
    end

    # Treatment-specific
    tx_mult = 1.0
    if tx == TX_SPIRONOLACTONE
        if p.sex[i] == SEX_MALE && rand(rng) < 0.30
            tx_mult = 1.5
        end
        if p.has_hyperkalemia[i] == Int8(1)
            tx_mult = 2.0
        end
    elseif tx == TX_IXA_001
        p.sdi_score[i] > 75.0 && (tx_mult = 1.3)
    end

    adj_annual = min(base_rate * resp_mult * time_mult * tx_mult, 0.40)
    monthly = 1.0 - (1.0 - adj_annual)^(1.0/12.0)

    return rand(rng) < monthly
end

# ============================================================================
# Neuro progression
# ============================================================================
@inline function check_neuro_progression!(p::PatientArrays, i::Int, rng::AbstractRNG)
    ns = p.neuro_state[i]
    ns == NS_DEMENTIA && return

    age = p.age[i]
    age_mult = age > 65.0 ? 2.0^((age - 65.0) / 5.0) : 1.0
    risk_sbp = p.true_mean_sbp[i]
    bp_mult = risk_sbp > 120.0 ? 1.0 + ((risk_sbp - 120.0) / 10.0) * 0.15 : 1.0
    total_mult = age_mult * bp_mult

    if ns == NS_NORMAL
        prob_dem = annual_to_monthly_prob(NEURO_NORMAL_TO_DEM * total_mult)
        if rand(rng) < prob_dem
            p.neuro_state[i] = NS_DEMENTIA
            p.time_in_neuro_state[i] = 0.0
            return
        end
        prob_mci = annual_to_monthly_prob(NEURO_NORMAL_TO_MCI * total_mult)
        if rand(rng) < prob_mci
            p.neuro_state[i] = NS_MCI
            p.time_in_neuro_state[i] = 0.0
        end
    elseif ns == NS_MCI
        prob_dem = annual_to_monthly_prob(NEURO_MCI_TO_DEM * total_mult)
        if rand(rng) < prob_dem
            p.neuro_state[i] = NS_DEMENTIA
            p.time_in_neuro_state[i] = 0.0
        end
    end
end

# ============================================================================
# AF onset
# ============================================================================
@inline function check_af_onset!(p::PatientArrays, i::Int, rng::AbstractRNG)::Bool
    p.has_atrial_fibrillation[i] == Int8(1) && return false

    age = p.age[i]
    base_annual = AF_BASE_RATES[1]
    for j in eachindex(AF_AGE_BRACKETS)
        age >= AF_AGE_BRACKETS[j] && (base_annual = AF_BASE_RATES[j])
    end

    risk_mult = 1.0

    # PA: 12x risk
    if p.has_primary_aldosteronism[i] == Int8(1)
        risk_mult *= 12.0
        tx = p.treatment[i]
        if tx == TX_IXA_001 && p.is_adherent[i] == Int8(1)
            risk_mult *= 0.40
        elseif tx == TX_SPIRONOLACTONE && p.is_adherent[i] == Int8(1)
            risk_mult *= 0.60
        end
    end

    p.has_heart_failure[i] == Int8(1) && (risk_mult *= 4.0)

    risk_sbp = p.true_mean_sbp[i]
    if risk_sbp > 140.0
        excess = (risk_sbp - 140.0) / 10.0
        risk_mult *= (1.0 + 0.15 * excess)
    end

    p.has_diabetes[i] == Int8(1) && (risk_mult *= 1.4)
    p.bmi[i] >= 30.0 && (risk_mult *= 1.5)

    annual_prob = min(0.25, base_annual * risk_mult)
    monthly = annual_to_monthly_prob(annual_prob)

    if rand(rng) < monthly
        p.has_atrial_fibrillation[i] = Int8(1)
        return true
    end
    return false
end

# ============================================================================
# SBP update
# ============================================================================
@inline function update_sbp!(p::PatientArrays, i::Int, rng::AbstractRNG)
    age_drift = 0.05
    epsilon = randn(rng) * 2.0
    p.current_sbp[i] = p.current_sbp[i] + age_drift + epsilon - p.treatment_effect_mmhg[i]
    p.true_mean_sbp[i] = p.current_sbp[i] - p.white_coat_effect[i]
    p.current_sbp[i] = clamp(p.current_sbp[i], 90.0, 220.0)
    p.true_mean_sbp[i] = clamp(p.true_mean_sbp[i], 80.0, 210.0)
    p.current_dbp[i] = p.current_sbp[i] * 0.6
end

# ============================================================================
# eGFR update + potassium + renal state
# ============================================================================
@inline function advance_time!(p::PatientArrays, i::Int, months::Float64, rng::AbstractRNG)
    p.time_in_simulation[i] += months
    p.time_in_cardiac_state[i] += months
    p.time_in_renal_state[i] += months
    p.time_in_neuro_state[i] += months

    if !isnan(p.time_since_last_cv_event[i])
        p.time_since_last_cv_event[i] += months
    end

    p.age[i] += months / 12.0

    # eGFR decline
    if p.use_kfre_model[i] == Int8(1)
        annual_decline = get_annual_egfr_decline(
            p.age[i], p.sex[i], p.egfr[i], p.uacr[i];
            has_diabetes = p.has_diabetes[i] == Int8(1),
            on_sglt2i = p.on_sglt2_inhibitor[i] == Int8(1),
            sbp = p.current_sbp[i],
        )
        annual_decline *= p.mod_esrd[i]  # phenotype modifier
    else
        age = p.age[i]
        base = age < 40.0 ? 0.0 : (age < 65.0 ? 1.0 : 1.5)
        sbp_excess = max(0.0, p.current_sbp[i] - 140.0)
        sbp_decline = 0.05 * sbp_excess
        dm_mult = p.has_diabetes[i] == Int8(1) ? 1.5 : 1.0
        sglt2_mult = p.on_sglt2_inhibitor[i] == Int8(1) ? 0.60 : 1.0
        annual_decline = (base + sbp_decline) * dm_mult * sglt2_mult * p.mod_esrd[i]
    end
    monthly_decline = annual_decline * (months / 12.0)
    p.egfr[i] = max(5.0, p.egfr[i] - monthly_decline)

    # Potassium update
    drift_sd = p.egfr[i] > 60.0 ? 0.1 : 0.2
    noise = randn(rng) * drift_sd
    target_k = 4.2
    p.egfr[i] < 45.0 && (target_k = 4.5)
    p.egfr[i] < 30.0 && (target_k = 4.8)
    p.egfr[i] < 15.0 && (target_k = 5.2)
    p.treatment[i] == TX_SPIRONOLACTONE && (target_k += 0.4)
    p.serum_potassium[i] += 0.2 * (target_k - p.serum_potassium[i]) + noise
    p.serum_potassium[i] = clamp(p.serum_potassium[i], 2.5, 7.0)
    p.has_hyperkalemia[i] = p.serum_potassium[i] > 5.5 ? Int8(1) : Int8(0)

    # Renal state update
    _update_renal_state!(p, i)
end

@inline function _update_renal_state!(p::PatientArrays, i::Int)
    rs = p.renal_state[i]
    (rs == RS_ESRD || rs == RS_RENAL_DEATH) && return

    egfr = p.egfr[i]
    new_rs = if egfr < 15.0
        RS_ESRD
    elseif egfr < 30.0
        RS_CKD_STAGE_4
    elseif egfr < 45.0
        RS_CKD_STAGE_3B
    elseif egfr < 60.0
        RS_CKD_STAGE_3A
    else
        RS_CKD_STAGE_1_2
    end

    if new_rs != rs
        p.renal_state[i] = new_rs
        p.time_in_renal_state[i] = 0.0
    end
end

# ============================================================================
# Cardiac state transition helper
# ============================================================================
@inline function transition_cardiac!(p::PatientArrays, i::Int, new_state::Int8)
    if new_state == CS_ACUTE_MI
        p.prior_mi_count[i] += 1
        p.time_since_last_cv_event[i] = 0.0
    elseif new_state == CS_ACUTE_ISCHEMIC_STROKE
        p.prior_stroke_count[i] += 1
        p.prior_ischemic_stroke_count[i] += 1
        p.time_since_last_cv_event[i] = 0.0
    elseif new_state == CS_ACUTE_HEMORRHAGIC_STROKE
        p.prior_stroke_count[i] += 1
        p.prior_hemorrhagic_stroke_count[i] += 1
        p.time_since_last_cv_event[i] = 0.0
    elseif new_state == CS_TIA
        p.prior_tia_count[i] += 1
        p.time_since_last_tia[i] = 0.0
    elseif new_state == CS_ACUTE_HF
        p.has_heart_failure[i] = Int8(1)
    end

    p.cardiac_state[i] = new_state
    p.time_in_cardiac_state[i] = 0.0
end
