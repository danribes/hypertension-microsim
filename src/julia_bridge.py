"""
julia_bridge.py — Python-Julia bridge for the hypertension microsimulation.

Initializes Julia via juliacall, converts Patient lists to SoA numpy arrays,
calls the Julia simulate_arm_from_python() entry point, and converts results
back to Python SimulationResults-compatible dicts.
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional

# Lazy import to avoid startup cost when not using Julia backend
_jl = None
_jl_sim = None


def _init_julia():
    """Initialize Julia runtime and load HypertensionSim module."""
    global _jl, _jl_sim

    if _jl is not None:
        return

    from juliacall import Main as jl

    _jl = jl

    # Activate the Julia project
    julia_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "julia",
    )
    _jl.seval(f'using Pkg; Pkg.activate("{julia_dir}"; io=devnull)')
    _jl.seval("using HypertensionSim")
    _jl_sim = _jl.HypertensionSim


# ──────────────────────────────────────────────────────────────────────────────
# Patient → SoA conversion
# ──────────────────────────────────────────────────────────────────────────────

# Enum value → Int8 mappings
_SEX_MAP = {"M": 0, "F": 1}
_CARDIAC_MAP = {
    "no_acute_event": 0,
    "acute_mi": 1,
    "post_mi": 2,
    "acute_ischemic_stroke": 3,
    "acute_hemorrhagic_stroke": 4,
    "post_stroke": 5,
    "tia": 6,
    "acute_hf": 7,
    "chronic_hf": 8,
    "cv_death": 9,
    "non_cv_death": 10,
}
_RENAL_MAP = {
    "ckd_stage_1_2": 0,
    "ckd_stage_3a": 1,
    "ckd_stage_3b": 2,
    "ckd_stage_4": 3,
    "esrd": 4,
    "renal_death": 5,
}
_NEURO_MAP = {
    "normal_cognition": 0,
    "mci": 1,
    "dementia": 2,
}
_TREATMENT_MAP = {
    "ixa_001": 0,
    "spironolactone": 1,
    "standard_care": 2,
}
_DIPPING_MAP = {
    "normal": 0,
    "non_dipper": 1,
    "reverse_dipper": 2,
}


def patients_to_soa(patients) -> Dict[str, np.ndarray]:
    """Convert a list of Patient objects to a dict of numpy arrays (SoA layout)."""
    n = len(patients)

    soa = {
        # Demographics
        "age": np.array([p.age for p in patients], dtype=np.float64),
        "sex": np.array([_SEX_MAP[p.sex.value] for p in patients], dtype=np.int8),

        # Blood pressure
        "baseline_sbp": np.array([p.baseline_sbp for p in patients], dtype=np.float64),
        "baseline_dbp": np.array([p.baseline_dbp for p in patients], dtype=np.float64),
        "current_sbp": np.array([p.current_sbp for p in patients], dtype=np.float64),
        "current_dbp": np.array([p.current_dbp for p in patients], dtype=np.float64),
        "true_mean_sbp": np.array([p.true_mean_sbp for p in patients], dtype=np.float64),
        "white_coat_effect": np.array([p.white_coat_effect for p in patients], dtype=np.float64),

        # Renal
        "egfr": np.array([p.egfr for p in patients], dtype=np.float64),
        "uacr": np.array([p.uacr for p in patients], dtype=np.float64),

        # Lipids
        "total_cholesterol": np.array([p.total_cholesterol for p in patients], dtype=np.float64),
        "hdl_cholesterol": np.array([p.hdl_cholesterol for p in patients], dtype=np.float64),

        # Comorbidities
        "has_diabetes": np.array([int(p.has_diabetes) for p in patients], dtype=np.int8),
        "is_smoker": np.array([int(p.is_smoker) for p in patients], dtype=np.int8),
        "bmi": np.array([p.bmi for p in patients], dtype=np.float64),
        "has_atrial_fibrillation": np.array([int(p.has_atrial_fibrillation) for p in patients], dtype=np.int8),
        "has_heart_failure": np.array([int(p.has_heart_failure) for p in patients], dtype=np.int8),
        "on_sglt2_inhibitor": np.array([int(p.on_sglt2_inhibitor) for p in patients], dtype=np.int8),

        # Secondary HTN
        "has_primary_aldosteronism": np.array([int(p.has_primary_aldosteronism) for p in patients], dtype=np.int8),
        "has_renal_artery_stenosis": np.array([int(p.has_renal_artery_stenosis) for p in patients], dtype=np.int8),
        "has_pheochromocytoma": np.array([int(p.has_pheochromocytoma) for p in patients], dtype=np.int8),
        "has_obstructive_sleep_apnea": np.array([int(p.has_obstructive_sleep_apnea) for p in patients], dtype=np.int8),

        # Hyperkalemia
        "serum_potassium": np.array([p.serum_potassium for p in patients], dtype=np.float64),
        "has_hyperkalemia": np.array([int(p.has_hyperkalemia) for p in patients], dtype=np.int8),
        "hyperkalemia_history": np.array([p.hyperkalemia_history for p in patients], dtype=np.int32),
        "on_potassium_binder": np.array([int(p.on_potassium_binder) for p in patients], dtype=np.int8),
        "mra_dose_reduced": np.array([int(p.mra_dose_reduced) for p in patients], dtype=np.int8),

        # Adherence
        "is_adherent": np.array([int(p.is_adherent) for p in patients], dtype=np.int8),
        "sdi_score": np.array([p.sdi_score for p in patients], dtype=np.float64),
        "nocturnal_dipping_status": np.array([_DIPPING_MAP.get(p.nocturnal_dipping_status, 0) for p in patients], dtype=np.int8),
        "time_since_adherence_change": np.array([p.time_since_adherence_change for p in patients], dtype=np.float64),

        # State machines
        "cardiac_state": np.array([_CARDIAC_MAP[p.cardiac_state.value] for p in patients], dtype=np.int8),
        "renal_state": np.array([_RENAL_MAP[p.renal_state.value] for p in patients], dtype=np.int8),
        "neuro_state": np.array([_NEURO_MAP[p.neuro_state.value] for p in patients], dtype=np.int8),
        "treatment": np.array([_TREATMENT_MAP[p.treatment.value] for p in patients], dtype=np.int8),

        # Event history
        "prior_mi_count": np.array([p.prior_mi_count for p in patients], dtype=np.int32),
        "prior_stroke_count": np.array([p.prior_stroke_count for p in patients], dtype=np.int32),
        "prior_ischemic_stroke_count": np.array([p.prior_ischemic_stroke_count for p in patients], dtype=np.int32),
        "prior_hemorrhagic_stroke_count": np.array([p.prior_hemorrhagic_stroke_count for p in patients], dtype=np.int32),
        "prior_tia_count": np.array([p.prior_tia_count for p in patients], dtype=np.int32),
        "time_since_last_cv_event": np.array(
            [p.time_since_last_cv_event if p.time_since_last_cv_event is not None else np.nan for p in patients],
            dtype=np.float64,
        ),
        "time_since_last_tia": np.array(
            [p.time_since_last_tia if p.time_since_last_tia is not None else np.nan for p in patients],
            dtype=np.float64,
        ),

        # Time tracking
        "time_in_simulation": np.array([p.time_in_simulation for p in patients], dtype=np.float64),
        "time_in_cardiac_state": np.array([p.time_in_cardiac_state for p in patients], dtype=np.float64),
        "time_in_renal_state": np.array([p.time_in_renal_state for p in patients], dtype=np.float64),
        "time_in_neuro_state": np.array([p.time_in_neuro_state for p in patients], dtype=np.float64),

        # Cumulative outcomes
        "cumulative_costs": np.zeros(n, dtype=np.float64),
        "cumulative_qalys": np.zeros(n, dtype=np.float64),

        # Treatment effects (will be set by Julia's assign_treatment!)
        "treatment_effect_mmhg": np.zeros(n, dtype=np.float64),
        "base_treatment_effect": np.zeros(n, dtype=np.float64),

        # Risk modifiers (from baseline risk profile)
        "mod_mi": np.array([p.baseline_risk_profile.get_dynamic_modifier("mi") for p in patients], dtype=np.float64),
        "mod_stroke": np.array([p.baseline_risk_profile.get_dynamic_modifier("stroke") for p in patients], dtype=np.float64),
        "mod_hf": np.array([p.baseline_risk_profile.get_dynamic_modifier("hf") for p in patients], dtype=np.float64),
        "mod_esrd": np.array([p.baseline_risk_profile.get_dynamic_modifier("esrd") for p in patients], dtype=np.float64),
        "mod_death": np.array([p.baseline_risk_profile.get_dynamic_modifier("death") for p in patients], dtype=np.float64),
        "treatment_response_modifier": np.ones(n, dtype=np.float64),

        # Misc
        "num_antihypertensives": np.array([p.num_antihypertensives for p in patients], dtype=np.int32),
        "use_kfre_model": np.array([int(p.use_kfre_model) for p in patients], dtype=np.int8),
    }

    return soa


# ──────────────────────────────────────────────────────────────────────────────
# Config conversion
# ──────────────────────────────────────────────────────────────────────────────

_PERSPECTIVE_MAP = {"US": 0, "UK": 1}
_ECON_MAP = {"healthcare_system": 0, "societal": 1}


def config_to_dict(config) -> Dict[str, Any]:
    """Convert SimulationConfig to a dict for Julia."""
    country = _PERSPECTIVE_MAP.get(getattr(config, "cost_perspective", "US"), 0)
    econ = _ECON_MAP.get(getattr(config, "economic_perspective", "societal"), 1)

    return {
        "time_horizon_months": int(config.time_horizon_months),
        "cycle_length_months": float(config.cycle_length_months),
        "discount_rate": float(config.discount_rate),
        "cost_perspective": int(country),
        "use_half_cycle_correction": bool(getattr(config, "use_half_cycle_correction", True)),
        "use_competing_risks": bool(getattr(config, "use_competing_risks", True)),
        "use_dynamic_stroke_subtypes": bool(getattr(config, "use_dynamic_stroke_subtypes", True)),
        "use_kfre_model": bool(getattr(config, "use_kfre_model", True)),
        "life_table_country": int(country),
        "economic_perspective": int(econ),
    }


def psa_params_to_dict(parameters: Dict[str, float]) -> Dict[str, Any]:
    """Convert PSA parameter dict to Julia-compatible dict with defaults."""
    defaults = {
        "ixa_sbp_mean": 20.0,
        "ixa_sbp_sd": 6.0,
        "spiro_sbp_mean": 9.0,
        "spiro_sbp_sd": 6.0,
        "discontinuation_rate_ixa": 0.08,
        "discontinuation_rate_spiro": 0.18,
        "cost_mi_acute": 25000.0,
        "cost_ischemic_stroke_acute": 15200.0,
        "cost_hemorrhagic_stroke_acute": 22500.0,
        "cost_hf_acute": 18000.0,
        "cost_esrd_annual": 90000.0,
        "cost_post_stroke_annual": 12000.0,
        "cost_hf_annual": 15000.0,
        "cost_ixa_monthly": 500.0,
        "disutility_post_mi": 0.12,
        "disutility_post_stroke": 0.18,
        "disutility_chronic_hf": 0.15,
        "disutility_esrd": 0.35,
        "disutility_dementia": 0.30,
    }
    result = {**defaults}
    for k, v in parameters.items():
        if k in result:
            result[k] = float(v)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def run_arm_julia(
    patients,
    treatment_code: int,
    config,
    psa_parameters: Dict[str, float],
    seed: int,
) -> Dict[str, Any]:
    """
    Run one treatment arm using the Julia backend.

    Args:
        patients: List of Patient objects
        treatment_code: 0=IXA_001, 1=SPIRONOLACTONE, 2=STANDARD_CARE
        config: SimulationConfig object
        psa_parameters: Dict of PSA-sampled parameter values
        seed: RNG seed (int)

    Returns:
        Dict with simulation result fields.
    """
    _init_julia()

    patient_dict = patients_to_soa(patients)
    config_dict = config_to_dict(config)
    psa_dict = psa_params_to_dict(psa_parameters)

    result = _jl_sim.simulate_arm_from_python(
        patient_dict, treatment_code, config_dict, psa_dict, seed,
    )

    # Convert Julia Dict to Python dict
    return dict(result)


def run_psa_parallel_julia(
    patients,
    config,
    all_psa_params: List[Dict[str, float]],
    base_seed: int,
    use_crn: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run all PSA iterations in parallel using Julia threads.

    Args:
        patients: Reference population (List[Patient])
        config: SimulationConfig object
        all_psa_params: List of PSA parameter dicts, one per iteration
        base_seed: Base RNG seed
        use_crn: Use common random numbers

    Returns:
        List of dicts, each with ixa_mean_costs/qalys/ly + comp_mean_costs/qalys/ly
    """
    _init_julia()

    patient_dict = patients_to_soa(patients)
    config_dict = config_to_dict(config)
    psa_dicts = [psa_params_to_dict(p) for p in all_psa_params]

    results = _jl_sim.run_psa_parallel(
        patient_dict, config_dict, psa_dicts, base_seed, use_crn,
    )

    return [dict(r) for r in results]
