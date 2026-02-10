# bridge.jl — Python-facing entry points for juliacall

# ============================================================================
# Shared helpers: dict → Julia types
# ============================================================================

function _unpack_patients!(p::PatientArrays, d::Dict)
    p.age .= Float64.(d["age"])
    p.sex .= Int8.(d["sex"])
    p.baseline_sbp .= Float64.(d["baseline_sbp"])
    p.baseline_dbp .= Float64.(d["baseline_dbp"])
    p.current_sbp .= Float64.(d["current_sbp"])
    p.current_dbp .= Float64.(d["current_dbp"])
    p.true_mean_sbp .= Float64.(d["true_mean_sbp"])
    p.white_coat_effect .= Float64.(d["white_coat_effect"])
    p.egfr .= Float64.(d["egfr"])
    p.uacr .= Float64.(d["uacr"])
    p.total_cholesterol .= Float64.(d["total_cholesterol"])
    p.hdl_cholesterol .= Float64.(d["hdl_cholesterol"])
    p.has_diabetes .= Int8.(d["has_diabetes"])
    p.is_smoker .= Int8.(d["is_smoker"])
    p.bmi .= Float64.(d["bmi"])
    p.has_atrial_fibrillation .= Int8.(d["has_atrial_fibrillation"])
    p.has_heart_failure .= Int8.(d["has_heart_failure"])
    p.on_sglt2_inhibitor .= Int8.(d["on_sglt2_inhibitor"])
    p.has_primary_aldosteronism .= Int8.(d["has_primary_aldosteronism"])
    p.has_renal_artery_stenosis .= Int8.(d["has_renal_artery_stenosis"])
    p.has_pheochromocytoma .= Int8.(d["has_pheochromocytoma"])
    p.has_obstructive_sleep_apnea .= Int8.(d["has_obstructive_sleep_apnea"])
    p.serum_potassium .= Float64.(d["serum_potassium"])
    p.has_hyperkalemia .= Int8.(d["has_hyperkalemia"])
    p.hyperkalemia_history .= Int32.(d["hyperkalemia_history"])
    p.on_potassium_binder .= Int8.(d["on_potassium_binder"])
    p.mra_dose_reduced .= Int8.(d["mra_dose_reduced"])
    p.is_adherent .= Int8.(d["is_adherent"])
    p.sdi_score .= Float64.(d["sdi_score"])
    p.nocturnal_dipping_status .= Int8.(d["nocturnal_dipping_status"])
    p.time_since_adherence_change .= Float64.(d["time_since_adherence_change"])
    p.cardiac_state .= Int8.(d["cardiac_state"])
    p.renal_state .= Int8.(d["renal_state"])
    p.neuro_state .= Int8.(d["neuro_state"])
    p.treatment .= Int8.(d["treatment"])
    p.prior_mi_count .= Int32.(d["prior_mi_count"])
    p.prior_stroke_count .= Int32.(d["prior_stroke_count"])
    p.prior_ischemic_stroke_count .= Int32.(d["prior_ischemic_stroke_count"])
    p.prior_hemorrhagic_stroke_count .= Int32.(d["prior_hemorrhagic_stroke_count"])
    p.prior_tia_count .= Int32.(d["prior_tia_count"])
    p.time_since_last_cv_event .= Float64.(d["time_since_last_cv_event"])
    p.time_since_last_tia .= Float64.(d["time_since_last_tia"])
    p.time_in_simulation .= Float64.(d["time_in_simulation"])
    p.time_in_cardiac_state .= Float64.(d["time_in_cardiac_state"])
    p.time_in_renal_state .= Float64.(d["time_in_renal_state"])
    p.time_in_neuro_state .= Float64.(d["time_in_neuro_state"])
    p.cumulative_costs .= Float64.(d["cumulative_costs"])
    p.cumulative_qalys .= Float64.(d["cumulative_qalys"])
    p.treatment_effect_mmhg .= Float64.(d["treatment_effect_mmhg"])
    p.base_treatment_effect .= Float64.(d["base_treatment_effect"])
    p.mod_mi .= Float64.(d["mod_mi"])
    p.mod_stroke .= Float64.(d["mod_stroke"])
    p.mod_hf .= Float64.(d["mod_hf"])
    p.mod_esrd .= Float64.(d["mod_esrd"])
    p.mod_death .= Float64.(d["mod_death"])
    p.treatment_response_modifier .= Float64.(d["treatment_response_modifier"])
    p.num_antihypertensives .= Int32.(d["num_antihypertensives"])
    p.use_kfre_model .= Int8.(d["use_kfre_model"])
    return p
end

function _make_config(d::Dict, n::Int)::SimConfig
    SimConfig(;
        n_patients = n,
        time_horizon_months = Int(d["time_horizon_months"]),
        cycle_length_months = Float64(d["cycle_length_months"]),
        discount_rate = Float64(d["discount_rate"]),
        cost_perspective = Int8(d["cost_perspective"]),
        use_half_cycle_correction = Bool(d["use_half_cycle_correction"]),
        use_competing_risks = Bool(d["use_competing_risks"]),
        use_dynamic_stroke_subtypes = Bool(d["use_dynamic_stroke_subtypes"]),
        use_kfre_model = Bool(d["use_kfre_model"]),
        life_table_country = Int8(d["life_table_country"]),
        economic_perspective = Int8(d["economic_perspective"]),
    )
end

function _make_psa(d::Dict)::PSAParameters
    PSAParameters(;
        ixa_sbp_mean = Float64(d["ixa_sbp_mean"]),
        ixa_sbp_sd = Float64(d["ixa_sbp_sd"]),
        spiro_sbp_mean = Float64(d["spiro_sbp_mean"]),
        spiro_sbp_sd = Float64(d["spiro_sbp_sd"]),
        discontinuation_rate_ixa = Float64(d["discontinuation_rate_ixa"]),
        discontinuation_rate_spiro = Float64(d["discontinuation_rate_spiro"]),
        cost_mi_acute = Float64(d["cost_mi_acute"]),
        cost_ischemic_stroke_acute = Float64(d["cost_ischemic_stroke_acute"]),
        cost_hemorrhagic_stroke_acute = Float64(d["cost_hemorrhagic_stroke_acute"]),
        cost_hf_acute = Float64(d["cost_hf_acute"]),
        cost_esrd_annual = Float64(d["cost_esrd_annual"]),
        cost_post_stroke_annual = Float64(d["cost_post_stroke_annual"]),
        cost_hf_annual = Float64(d["cost_hf_annual"]),
        cost_ixa_monthly = Float64(d["cost_ixa_monthly"]),
        disutility_post_mi = Float64(d["disutility_post_mi"]),
        disutility_post_stroke = Float64(d["disutility_post_stroke"]),
        disutility_chronic_hf = Float64(d["disutility_chronic_hf"]),
        disutility_esrd = Float64(d["disutility_esrd"]),
        disutility_dementia = Float64(d["disutility_dementia"]),
    )
end

function _results_to_dict(results::ArmResults)::Dict{String, Any}
    means = calculate_means(results)
    Dict{String, Any}(
        "n_patients" => results.n_patients,
        "total_costs" => results.total_costs,
        "total_indirect_costs" => results.total_indirect_costs,
        "total_qalys" => results.total_qalys,
        "life_years" => results.life_years,
        "mi_events" => results.mi_events,
        "stroke_events" => results.stroke_events,
        "ischemic_stroke_events" => results.ischemic_stroke_events,
        "hemorrhagic_stroke_events" => results.hemorrhagic_stroke_events,
        "tia_events" => results.tia_events,
        "hf_events" => results.hf_events,
        "cv_deaths" => results.cv_deaths,
        "non_cv_deaths" => results.non_cv_deaths,
        "esrd_events" => results.esrd_events,
        "ckd_4_events" => results.ckd_4_events,
        "renal_deaths" => results.renal_deaths,
        "dementia_cases" => results.dementia_cases,
        "new_af_events" => results.new_af_events,
        "sglt2_users" => results.sglt2_users,
        "time_controlled" => results.time_controlled,
        "time_uncontrolled" => results.time_uncontrolled,
        "mean_costs" => means.mean_costs,
        "mean_indirect_costs" => means.mean_indirect_costs,
        "mean_total_costs" => means.mean_total_costs,
        "mean_qalys" => means.mean_qalys,
        "mean_life_years" => means.mean_life_years,
    )
end

# ============================================================================
# Single-arm entry point
# ============================================================================

"""
    simulate_arm_from_python(patient_dict, treatment_code, config_dict, psa_dict, seed) -> Dict

Entry point called from Python via juliacall for a single arm.
"""
# Convert any dict-like (including PyDict) to Dict{String,Any}
_to_dict(d::Dict{String,Any}) = d
_to_dict(d::Dict) = Dict{String,Any}(String(k) => v for (k,v) in d)
_to_dict(d) = Dict{String,Any}(String(k) => d[k] for k in keys(d))

function simulate_arm_from_python(
    patient_dict_raw,
    treatment_code,
    config_dict_raw,
    psa_dict_raw,
    seed,
)::Dict{String, Any}
    patient_dict = _to_dict(patient_dict_raw)
    config_dict = _to_dict(config_dict_raw)
    psa_dict = _to_dict(psa_dict_raw)
    n = length(patient_dict["age"])
    p = PatientArrays(n)
    _unpack_patients!(p, patient_dict)
    cfg = _make_config(config_dict, n)
    psa = _make_psa(psa_dict)
    results = simulate_arm!(p, cfg, psa, Int8(Int(treatment_code)), UInt64(Int(seed)))
    return _results_to_dict(results)
end

# ============================================================================
# Parallel PSA entry point
# ============================================================================

"""
    run_psa_parallel(patient_dict, config_dict, all_psa_dicts, base_seed, use_crn) -> Vector{Dict}

Run multiple PSA iterations in parallel using Julia threads.

Optimizations:
- **Dynamic scheduling**: `@threads :dynamic` lets idle threads steal work
  from slower iterations instead of static partitioning.
- **Thread-local buffers**: Each thread pre-allocates 2 PatientArrays (one per
  arm) at startup and reuses them across iterations, eliminating all per-iteration
  allocation and GC pressure (~440 KB × N_iterations avoided).
- **Zero-copy template reset**: `_reset_patients!` copies template data into
  the existing buffer without allocating new vectors.

With `JULIA_NUM_THREADS=auto` (or set to core count), all available cores
are utilized. On a 16-core machine with 1000 iterations, each core processes
~62 iterations with dynamic load balancing.
"""
function run_psa_parallel(
    patient_dict_raw,
    config_dict_raw,
    all_psa_dicts_raw,
    base_seed,
    use_crn::Bool,
)::Vector{Dict{String, Any}}
    # Convert Python types to Julia types
    patient_dict = _to_dict(patient_dict_raw)
    config_dict = _to_dict(config_dict_raw)
    all_psa_dicts = [_to_dict(d) for d in all_psa_dicts_raw]
    base_seed = Int(base_seed)

    n_iter = length(all_psa_dicts)
    n = length(patient_dict["age"])
    cfg = _make_config(config_dict, n)

    # Pre-build a read-only template
    template = PatientArrays(n)
    _unpack_patients!(template, patient_dict)

    # Output array (one dict per iteration)
    out = Vector{Dict{String, Any}}(undef, n_iter)

    # Buffer pool: pre-allocate enough buffer pairs for max concurrency.
    # With :dynamic scheduling, Julia may use more OS threads than nthreads()
    # reports, so we size the pool to the iteration count (capped at a
    # reasonable max) and use a channel as a thread-safe free-list.
    pool_size = min(n_iter, max(Threads.nthreads(), 2) * 2)
    pool = Channel{Tuple{PatientArrays, PatientArrays}}(pool_size)
    for _ in 1:pool_size
        put!(pool, (PatientArrays(n), PatientArrays(n)))
    end

    Threads.@threads :dynamic for k in 1:n_iter
        # Acquire a buffer pair from the pool (blocks if all in use)
        buf_ixa, buf_comp = take!(pool)

        psa = _make_psa(all_psa_dicts[k])

        # Seeds: same as Python PSA runner convention
        iter_base = base_seed + (k - 1) * 1000000
        sim_seed = UInt64(iter_base + 1)
        sim_seed_comp = use_crn ? sim_seed : UInt64(iter_base + 2)

        # Reset buffers from template (no allocation)
        _reset_patients!(buf_ixa, template)
        r_ixa = simulate_arm!(buf_ixa, cfg, psa, TX_IXA_001, sim_seed)
        m_ixa = calculate_means(r_ixa)

        _reset_patients!(buf_comp, template)
        r_comp = simulate_arm!(buf_comp, cfg, psa, TX_SPIRONOLACTONE, sim_seed_comp)
        m_comp = calculate_means(r_comp)

        out[k] = Dict{String, Any}(
            "ixa_mean_costs" => m_ixa.mean_costs,
            "ixa_mean_qalys" => m_ixa.mean_qalys,
            "ixa_mean_life_years" => m_ixa.mean_life_years,
            "comp_mean_costs" => m_comp.mean_costs,
            "comp_mean_qalys" => m_comp.mean_qalys,
            "comp_mean_life_years" => m_comp.mean_life_years,
        )

        # Return buffers to the pool
        put!(pool, (buf_ixa, buf_comp))
    end

    close(pool)
    return out
end

# Copy all vector fields from src into pre-allocated dst (zero allocation)
function _reset_patients!(dst::PatientArrays, src::PatientArrays)
    @assert dst.n == src.n
    for fname in fieldnames(PatientArrays)
        fname == :n && continue
        src_field = getfield(src, fname)
        if src_field isa Vector
            copy!(getfield(dst, fname), src_field)
        end
    end
end

# Deep copy (used by single-arm entry point and tests)
function _copy_patients(src::PatientArrays)::PatientArrays
    dst = PatientArrays(src.n)
    _reset_patients!(dst, src)
    return dst
end
