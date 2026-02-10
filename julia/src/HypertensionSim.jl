# HypertensionSim.jl — Top-level module for hypertension microsimulation

module HypertensionSim

using Random

# Source files (order matters for dependencies)
include("types.jl")
include("prevent.jl")
include("kfre.jl")
include("life_tables.jl")
include("transitions.jl")
include("costs.jl")
include("utilities.jl")
include("treatment.jl")
include("simulate.jl")
include("bridge.jl")

# Public API — types and functions
export simulate_arm!, simulate_arm_from_python, run_psa_parallel,
       PatientArrays, SimConfig, PSAParameters, ArmResults, calculate_means

# Export Int8 constants so tests and callers can use them unqualified
export CS_NO_ACUTE_EVENT, CS_ACUTE_MI, CS_POST_MI,
       CS_ACUTE_ISCHEMIC_STROKE, CS_ACUTE_HEMORRHAGIC_STROKE, CS_POST_STROKE,
       CS_TIA, CS_ACUTE_HF, CS_CHRONIC_HF, CS_CV_DEATH, CS_NON_CV_DEATH
export RS_CKD_STAGE_1_2, RS_CKD_STAGE_3A, RS_CKD_STAGE_3B,
       RS_CKD_STAGE_4, RS_ESRD, RS_RENAL_DEATH
export NS_NORMAL, NS_MCI, NS_DEMENTIA
export TX_IXA_001, TX_SPIRONOLACTONE, TX_STANDARD_CARE
export SEX_MALE, SEX_FEMALE
export RISK_PROP_MI, RISK_PROP_STROKE, RISK_PROP_HF

end # module
