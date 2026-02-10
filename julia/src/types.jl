# types.jl — Enums (Int8 constants), PatientArrays, SimConfig, PSAParameters, ArmResults

# ============================================================================
# Enum-like Int8 constants (avoid Julia Enum overhead in hot loop)
# ============================================================================

# CardiacState
const CS_NO_ACUTE_EVENT          = Int8(0)
const CS_ACUTE_MI                = Int8(1)
const CS_POST_MI                 = Int8(2)
const CS_ACUTE_ISCHEMIC_STROKE   = Int8(3)
const CS_ACUTE_HEMORRHAGIC_STROKE= Int8(4)
const CS_POST_STROKE             = Int8(5)
const CS_TIA                     = Int8(6)
const CS_ACUTE_HF                = Int8(7)
const CS_CHRONIC_HF              = Int8(8)
const CS_CV_DEATH                = Int8(9)
const CS_NON_CV_DEATH            = Int8(10)

# RenalState
const RS_CKD_STAGE_1_2 = Int8(0)
const RS_CKD_STAGE_3A  = Int8(1)
const RS_CKD_STAGE_3B  = Int8(2)
const RS_CKD_STAGE_4   = Int8(3)
const RS_ESRD          = Int8(4)
const RS_RENAL_DEATH   = Int8(5)

# NeuroState
const NS_NORMAL    = Int8(0)
const NS_MCI       = Int8(1)
const NS_DEMENTIA  = Int8(2)

# Treatment
const TX_IXA_001        = Int8(0)
const TX_SPIRONOLACTONE = Int8(1)
const TX_STANDARD_CARE  = Int8(2)

# Sex
const SEX_MALE   = Int8(0)
const SEX_FEMALE = Int8(1)

# ============================================================================
# Alive check helpers
# ============================================================================
@inline function is_alive(cardiac::Int8, renal::Int8)
    cardiac != CS_CV_DEATH && cardiac != CS_NON_CV_DEATH && renal != RS_RENAL_DEATH
end

# ============================================================================
# PatientArrays — Struct-of-Arrays for cache-friendly access
# ============================================================================
"""
    PatientArrays

Struct-of-Arrays layout for N patients. Every field is a `Vector` of length N.
Total memory ~220 KB for N=500 (fits in L2 cache).
"""
mutable struct PatientArrays
    n::Int

    # Demographics
    age::Vector{Float64}
    sex::Vector{Int8}               # SEX_MALE / SEX_FEMALE

    # Blood Pressure
    baseline_sbp::Vector{Float64}
    baseline_dbp::Vector{Float64}
    current_sbp::Vector{Float64}
    current_dbp::Vector{Float64}
    true_mean_sbp::Vector{Float64}
    white_coat_effect::Vector{Float64}

    # Renal
    egfr::Vector{Float64}
    uacr::Vector{Float64}

    # Lipids
    total_cholesterol::Vector{Float64}
    hdl_cholesterol::Vector{Float64}

    # Comorbidities (Bool encoded as Int8 for SoA)
    has_diabetes::Vector{Int8}
    is_smoker::Vector{Int8}
    bmi::Vector{Float64}
    has_atrial_fibrillation::Vector{Int8}
    has_heart_failure::Vector{Int8}
    on_sglt2_inhibitor::Vector{Int8}

    # Secondary HTN
    has_primary_aldosteronism::Vector{Int8}
    has_renal_artery_stenosis::Vector{Int8}
    has_pheochromocytoma::Vector{Int8}
    has_obstructive_sleep_apnea::Vector{Int8}

    # Hyperkalemia
    serum_potassium::Vector{Float64}
    has_hyperkalemia::Vector{Int8}
    hyperkalemia_history::Vector{Int32}
    on_potassium_binder::Vector{Int8}
    mra_dose_reduced::Vector{Int8}

    # Adherence
    is_adherent::Vector{Int8}
    sdi_score::Vector{Float64}
    nocturnal_dipping_status::Vector{Int8}  # 0=normal, 1=non_dipper, 2=reverse_dipper
    time_since_adherence_change::Vector{Float64}

    # State machines
    cardiac_state::Vector{Int8}
    renal_state::Vector{Int8}
    neuro_state::Vector{Int8}
    treatment::Vector{Int8}

    # Event history
    prior_mi_count::Vector{Int32}
    prior_stroke_count::Vector{Int32}
    prior_ischemic_stroke_count::Vector{Int32}
    prior_hemorrhagic_stroke_count::Vector{Int32}
    prior_tia_count::Vector{Int32}
    time_since_last_cv_event::Vector{Float64}    # NaN = never
    time_since_last_tia::Vector{Float64}         # NaN = never

    # Time tracking
    time_in_simulation::Vector{Float64}
    time_in_cardiac_state::Vector{Float64}
    time_in_renal_state::Vector{Float64}
    time_in_neuro_state::Vector{Float64}

    # Cumulative outcomes
    cumulative_costs::Vector{Float64}
    cumulative_qalys::Vector{Float64}

    # Treatment effect caching
    treatment_effect_mmhg::Vector{Float64}
    base_treatment_effect::Vector{Float64}

    # Baseline risk profile modifiers (pre-computed for hot loop)
    # Keys: MI, STROKE, HF, ESRD, DEATH
    mod_mi::Vector{Float64}
    mod_stroke::Vector{Float64}
    mod_hf::Vector{Float64}
    mod_esrd::Vector{Float64}
    mod_death::Vector{Float64}

    # Treatment response modifier (pre-computed)
    treatment_response_modifier::Vector{Float64}

    # Working-age flag (for indirect costs)
    num_antihypertensives::Vector{Int32}
    use_kfre_model::Vector{Int8}
end

function PatientArrays(n::Int)
    PatientArrays(
        n,
        zeros(Float64, n), zeros(Int8, n),                    # age, sex
        zeros(Float64, n), zeros(Float64, n),                  # baseline sbp/dbp
        zeros(Float64, n), zeros(Float64, n),                  # current sbp/dbp
        zeros(Float64, n), zeros(Float64, n),                  # true_mean_sbp, white_coat
        zeros(Float64, n), zeros(Float64, n),                  # egfr, uacr
        zeros(Float64, n), zeros(Float64, n),                  # tc, hdl
        zeros(Int8, n), zeros(Int8, n), zeros(Float64, n),     # dm, smoker, bmi
        zeros(Int8, n), zeros(Int8, n), zeros(Int8, n),        # af, hf, sglt2
        zeros(Int8, n), zeros(Int8, n), zeros(Int8, n), zeros(Int8, n), # PA, RAS, Pheo, OSA
        fill(4.2, n), zeros(Int8, n), zeros(Int32, n),         # K+, hyperK, hyperK hist
        zeros(Int8, n), zeros(Int8, n),                        # K+ binder, mra_dose_reduced
        ones(Int8, n), fill(50.0, n),                          # adherent, sdi
        zeros(Int8, n), zeros(Float64, n),                     # dipping, time_since_adh
        zeros(Int8, n), zeros(Int8, n), zeros(Int8, n),        # cardiac, renal, neuro
        fill(TX_STANDARD_CARE, n),                             # treatment
        zeros(Int32, n), zeros(Int32, n),                      # prior MI, stroke
        zeros(Int32, n), zeros(Int32, n), zeros(Int32, n),     # ischemic, hemorrhagic, tia
        fill(NaN, n), fill(NaN, n),                            # time_since_cv, time_since_tia
        zeros(Float64, n), zeros(Float64, n),                  # time_sim, time_cardiac
        zeros(Float64, n), zeros(Float64, n),                  # time_renal, time_neuro
        zeros(Float64, n), zeros(Float64, n),                  # costs, qalys
        zeros(Float64, n), zeros(Float64, n),                  # tx effect, base tx effect
        ones(Float64, n), ones(Float64, n), ones(Float64, n),  # mod mi/stroke/hf
        ones(Float64, n), ones(Float64, n),                    # mod esrd/death
        ones(Float64, n),                                      # treatment_response_modifier
        fill(Int32(3), n), ones(Int8, n),                      # num_antihtn, use_kfre
    )
end

# ============================================================================
# SimConfig
# ============================================================================
struct SimConfig
    n_patients::Int
    time_horizon_months::Int
    cycle_length_months::Float64
    discount_rate::Float64
    cost_perspective::Int8           # 0=US, 1=UK
    use_half_cycle_correction::Bool
    use_competing_risks::Bool
    use_dynamic_stroke_subtypes::Bool
    use_kfre_model::Bool
    life_table_country::Int8         # 0=US, 1=UK
    economic_perspective::Int8       # 0=healthcare_system, 1=societal
end

function SimConfig(;
    n_patients::Int=1000,
    time_horizon_months::Int=480,
    cycle_length_months::Float64=1.0,
    discount_rate::Float64=0.03,
    cost_perspective::Int8=Int8(0),
    use_half_cycle_correction::Bool=true,
    use_competing_risks::Bool=true,
    use_dynamic_stroke_subtypes::Bool=true,
    use_kfre_model::Bool=true,
    life_table_country::Int8=Int8(0),
    economic_perspective::Int8=Int8(1),
)
    SimConfig(
        n_patients, time_horizon_months, cycle_length_months, discount_rate,
        cost_perspective, use_half_cycle_correction, use_competing_risks,
        use_dynamic_stroke_subtypes, use_kfre_model, life_table_country,
        economic_perspective,
    )
end

# ============================================================================
# PSAParameters — explicit struct for thread safety
# ============================================================================
struct PSAParameters
    # Treatment effects
    ixa_sbp_mean::Float64
    ixa_sbp_sd::Float64
    spiro_sbp_mean::Float64
    spiro_sbp_sd::Float64

    # Discontinuation
    discontinuation_rate_ixa::Float64
    discontinuation_rate_spiro::Float64

    # Costs
    cost_mi_acute::Float64
    cost_ischemic_stroke_acute::Float64
    cost_hemorrhagic_stroke_acute::Float64
    cost_hf_acute::Float64
    cost_esrd_annual::Float64
    cost_post_stroke_annual::Float64
    cost_hf_annual::Float64
    cost_ixa_monthly::Float64

    # Disutilities
    disutility_post_mi::Float64
    disutility_post_stroke::Float64
    disutility_chronic_hf::Float64
    disutility_esrd::Float64
    disutility_dementia::Float64
end

function PSAParameters(;
    ixa_sbp_mean=20.0, ixa_sbp_sd=6.0,
    spiro_sbp_mean=9.0, spiro_sbp_sd=6.0,
    discontinuation_rate_ixa=0.08, discontinuation_rate_spiro=0.18,
    cost_mi_acute=25000.0, cost_ischemic_stroke_acute=15200.0,
    cost_hemorrhagic_stroke_acute=22500.0, cost_hf_acute=18000.0,
    cost_esrd_annual=90000.0, cost_post_stroke_annual=12000.0,
    cost_hf_annual=15000.0, cost_ixa_monthly=500.0,
    disutility_post_mi=0.12, disutility_post_stroke=0.18,
    disutility_chronic_hf=0.15, disutility_esrd=0.35,
    disutility_dementia=0.30,
)
    PSAParameters(
        ixa_sbp_mean, ixa_sbp_sd, spiro_sbp_mean, spiro_sbp_sd,
        discontinuation_rate_ixa, discontinuation_rate_spiro,
        cost_mi_acute, cost_ischemic_stroke_acute,
        cost_hemorrhagic_stroke_acute, cost_hf_acute,
        cost_esrd_annual, cost_post_stroke_annual,
        cost_hf_annual, cost_ixa_monthly,
        disutility_post_mi, disutility_post_stroke,
        disutility_chronic_hf, disutility_esrd,
        disutility_dementia,
    )
end

# ============================================================================
# ArmResults — aggregated results for one arm
# ============================================================================
mutable struct ArmResults
    n_patients::Int

    # Primary outcomes
    total_costs::Float64
    total_indirect_costs::Float64
    total_qalys::Float64
    life_years::Float64

    # Event counts
    mi_events::Int
    stroke_events::Int
    ischemic_stroke_events::Int
    hemorrhagic_stroke_events::Int
    tia_events::Int
    hf_events::Int
    cv_deaths::Int
    non_cv_deaths::Int

    # Renal
    esrd_events::Int
    ckd_4_events::Int
    renal_deaths::Int

    # Neuro
    dementia_cases::Int

    # AF
    new_af_events::Int

    # Medication
    sglt2_users::Int

    # BP control
    time_controlled::Float64
    time_uncontrolled::Float64
end

function ArmResults(n::Int)
    ArmResults(
        n,
        0.0, 0.0, 0.0, 0.0,           # costs, indirect, qalys, LY
        0, 0, 0, 0, 0, 0, 0, 0,        # cardiac events
        0, 0, 0,                        # renal
        0, 0, 0,                        # neuro, AF, sglt2
        0.0, 0.0,                       # BP control
    )
end

# Per-patient means (computed after simulation)
function calculate_means(r::ArmResults)
    n = r.n_patients
    return (
        mean_costs = r.total_costs / n,
        mean_indirect_costs = r.total_indirect_costs / n,
        mean_total_costs = (r.total_costs + r.total_indirect_costs) / n,
        mean_qalys = r.total_qalys / n,
        mean_life_years = r.life_years / n,
    )
end
