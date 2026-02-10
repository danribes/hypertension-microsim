# simulate.jl — Main simulation hot loop
# Direct translation of src/simulation.py lines 338-485

using Random

"""
    simulate_arm!(p, cfg, psa, treatment_code, seed) -> ArmResults

Run the monthly Markov microsimulation for one treatment arm.
Operates on `PatientArrays` in-place, returns aggregated `ArmResults`.
"""
function simulate_arm!(
    p::PatientArrays,
    cfg::SimConfig,
    psa::PSAParameters,
    treatment_code::Int8,
    seed::UInt64,
)::ArmResults
    rng = Random.Xoshiro(seed)
    n = p.n
    n_cycles = round(Int, cfg.time_horizon_months / cfg.cycle_length_months)
    results = ArmResults(n)
    costs_inputs = get_costs(cfg.cost_perspective, psa)

    # Assign initial treatment to all patients
    for i in 1:n
        assign_treatment!(p, i, treatment_code, psa, rng)
    end

    # Pre-allocate transition probabilities (reused per patient)
    tp = TransProbs()

    # ── Main simulation loop ──────────────────────────────────────────────
    for cycle in 1:n_cycles
        @inbounds for i in 1:n
            cs = p.cardiac_state[i]
            rs = p.renal_state[i]

            # Skip dead patients
            !is_alive(cs, rs) && continue

            # ── 0.5  Adherence change ──────────────────────────────────
            if check_adherence_change!(p, i, rng)
                update_effect_for_adherence!(p, i)
            end

            # ── 0.55 Hyperkalemia management (quarterly, spironolactone) ─
            is_quarterly = (round(Int, p.time_in_simulation[i]) % 3 == 0)
            if is_quarterly && p.treatment[i] == TX_SPIRONOLACTONE
                # Lab cost for potassium check
                lab_cost = costs_inputs.lab_test_cost_k
                df = get_discount_factor(
                    p.time_in_simulation[i], cfg.discount_rate,
                    cfg.cycle_length_months, cfg.use_half_cycle_correction,
                )
                p.cumulative_costs[i] += lab_cost * df
                results.total_costs += lab_cost * df

                if p.serum_potassium[i] > 5.0
                    action, addl_cost, stopped = manage_hyperkalemia!(p, i, costs_inputs, rng)

                    if addl_cost > 0.0
                        p.cumulative_costs[i] += addl_cost * df
                        results.total_costs += addl_cost * df
                    end

                    if action == Int8(4) || action == Int8(3)
                        # hyperkalemia_history already incremented inside manage_hyperkalemia!
                    end

                    if stopped
                        assign_treatment!(p, i, TX_STANDARD_CARE, psa, rng)
                    end
                end
            end

            # ── 0.6  Neuro progression ─────────────────────────────────
            old_neuro = p.neuro_state[i]
            check_neuro_progression!(p, i, rng)
            if p.neuro_state[i] != old_neuro && p.neuro_state[i] == NS_DEMENTIA
                results.dementia_cases += 1
            end

            # ── 0.7  AF onset ──────────────────────────────────────────
            if check_af_onset!(p, i, rng)
                results.new_af_events += 1
                af_cost = get_af_event_cost(costs_inputs)
                df = get_discount_factor(
                    p.time_in_simulation[i], cfg.discount_rate,
                    cfg.cycle_length_months, cfg.use_half_cycle_correction,
                )
                p.cumulative_costs[i] += af_cost * df
                results.total_costs += af_cost * df
            end

            # ── 1.0  Calculate & sample cardiac events / mortality ─────
            calculate_transitions!(tp, p, i, cfg, psa)
            new_event = sample_event(tp, p.cardiac_state[i], rng)

            if new_event != Int8(-1)
                if new_event == CS_NON_CV_DEATH
                    results.non_cv_deaths += 1
                    p.cardiac_state[i] = CS_NON_CV_DEATH
                else
                    # Record event in results
                    _record_event!(new_event, results)
                    # Transition cardiac state
                    transition_cardiac!(p, i, new_event)

                    # One-time event cost (direct)
                    event_cost = get_event_cost(new_event, costs_inputs)
                    # One-time absenteeism cost (indirect)
                    absent_cost = get_acute_absenteeism_cost(new_event, p.age[i], costs_inputs)

                    df = get_discount_factor(
                        p.time_in_simulation[i], cfg.discount_rate,
                        cfg.cycle_length_months, cfg.use_half_cycle_correction,
                    )
                    p.cumulative_costs[i] += event_cost * df
                    results.total_costs += event_cost * df
                    results.total_indirect_costs += absent_cost * df
                end
            end

            # Skip if died from event
            !is_alive(p.cardiac_state[i], p.renal_state[i]) && continue

            # ── 1.5  TIA → Stroke conversion ──────────────────────────
            if p.prior_tia_count[i] > 0 && !isnan(p.time_since_last_tia[i])
                if check_tia_to_stroke(
                    p.prior_tia_count[i], p.time_since_last_tia[i],
                    p.true_mean_sbp[i], p.has_diabetes[i],
                    p.has_atrial_fibrillation[i], rng,
                )
                    # TIA converts to ischemic stroke
                    tia_conv = CS_ACUTE_ISCHEMIC_STROKE
                    _record_event!(tia_conv, results)
                    transition_cardiac!(p, i, tia_conv)

                    event_cost = get_event_cost(tia_conv, costs_inputs)
                    absent_cost = get_acute_absenteeism_cost(tia_conv, p.age[i], costs_inputs)
                    df = get_discount_factor(
                        p.time_in_simulation[i], cfg.discount_rate,
                        cfg.cycle_length_months, cfg.use_half_cycle_correction,
                    )
                    p.cumulative_costs[i] += event_cost * df
                    results.total_costs += event_cost * df
                    results.total_indirect_costs += absent_cost * df
                end
            end

            !is_alive(p.cardiac_state[i], p.renal_state[i]) && continue

            # ── 2.0  Accrue monthly costs & QALYs ─────────────────────
            df = get_discount_factor(
                p.time_in_simulation[i], cfg.discount_rate,
                cfg.cycle_length_months, cfg.use_half_cycle_correction,
            )

            # Monthly state management cost (cardiac + renal)
            monthly_cost = get_monthly_state_cost(
                p.cardiac_state[i], p.renal_state[i],
                p.current_sbp[i], p.has_atrial_fibrillation[i],
                costs_inputs,
            )

            # Drug cost
            drug_cost = get_drug_cost(p.treatment[i], p.on_sglt2_inhibitor[i], costs_inputs)

            total_monthly = (monthly_cost + drug_cost) * df
            p.cumulative_costs[i] += total_monthly
            results.total_costs += total_monthly

            # Monthly productivity loss (indirect, societal perspective)
            if cfg.economic_perspective == Int8(1)
                monthly_indirect = get_monthly_productivity_loss(
                    p.cardiac_state[i], p.age[i], costs_inputs,
                )
                results.total_indirect_costs += monthly_indirect * df
            end

            # QALY
            utility = get_utility(
                p.age[i], p.cardiac_state[i], p.renal_state[i], p.neuro_state[i],
                p.current_sbp[i], p.has_diabetes[i], p.has_atrial_fibrillation[i],
                p.has_hyperkalemia[i], p.num_antihypertensives[i], psa,
            )
            qaly = calculate_monthly_qaly(
                utility, p.time_in_simulation[i],
                cfg.discount_rate, cfg.cycle_length_months,
                cfg.use_half_cycle_correction,
            )
            p.cumulative_qalys[i] += qaly
            results.total_qalys += qaly

            # Life years
            results.life_years += (1.0 / 12.0) * df

            # BP control tracking
            if p.current_sbp[i] < 140.0
                results.time_controlled += 1.0 / 12.0
            else
                results.time_uncontrolled += 1.0 / 12.0
            end

            # ── 2.5  Update SBP ────────────────────────────────────────
            update_sbp!(p, i, rng)

            # ── 3.0  Advance time (age, eGFR, K+, renal state) ────────
            old_renal = p.renal_state[i]
            advance_time!(p, i, cfg.cycle_length_months, rng)

            # Update TIA time tracking
            if !isnan(p.time_since_last_tia[i])
                p.time_since_last_tia[i] += cfg.cycle_length_months
            end

            # Check renal transitions
            if p.renal_state[i] != old_renal
                if p.renal_state[i] == RS_ESRD
                    results.esrd_events += 1
                elseif p.renal_state[i] == RS_CKD_STAGE_4
                    results.ckd_4_events += 1
                end
            end

            # ── 3.5  ESRD mortality ────────────────────────────────────
            if p.renal_state[i] == RS_ESRD
                if check_esrd_mortality(p.renal_state[i], p.age[i], p.has_diabetes[i], rng)
                    p.renal_state[i] = RS_RENAL_DEATH
                    results.renal_deaths += 1
                end
            end

            # ── 4.0  Treatment discontinuation ─────────────────────────
            if check_discontinuation(p, i, psa, rng)
                p.treatment[i] = TX_STANDARD_CARE
                p.mra_dose_reduced[i] = Int8(0)
            end
        end  # patient loop
    end  # cycle loop

    # Track SGLT2 users at end
    for i in 1:n
        if p.on_sglt2_inhibitor[i] == Int8(1)
            results.sglt2_users += 1
        end
    end

    return results
end

# ============================================================================
# Event recording helper
# ============================================================================
@inline function _record_event!(event::Int8, results::ArmResults)
    if event == CS_ACUTE_MI
        results.mi_events += 1
    elseif event == CS_ACUTE_ISCHEMIC_STROKE
        results.ischemic_stroke_events += 1
        results.stroke_events += 1
    elseif event == CS_ACUTE_HEMORRHAGIC_STROKE
        results.hemorrhagic_stroke_events += 1
        results.stroke_events += 1
    elseif event == CS_TIA
        results.tia_events += 1
    elseif event == CS_ACUTE_HF
        results.hf_events += 1
    elseif event == CS_CV_DEATH
        results.cv_deaths += 1
    end
end
