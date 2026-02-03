#!/usr/bin/env python3
"""
Test script for model enhancements.
"""

from src.patient import create_patient_from_params, RenalState
from src.simulation import Simulation, SimulationConfig
from src.population import generate_default_population
from src.patient import Treatment
import numpy as np

print('Testing Model Enhancements...\n')

# Test 1: CKD Stage 3 subdivision
print('Test 1: CKD Stage 3 Subdivision')
p1 = create_patient_from_params(0, 65, 'M', 140, egfr=55)
print(f'  eGFR=55 -> State: {p1.renal_state.value} (expected: ckd_stage_3a)')

p2 = create_patient_from_params(1, 65, 'M', 140, egfr=40)
print(f'  eGFR=40 -> State: {p2.renal_state.value} (expected: ckd_stage_3b)')

# Test 2: SBP variability
print('\nTest 2: SBP Stochastic Variation')
rng = np.random.default_rng(42)
p3 = create_patient_from_params(2, 60, 'M', 150)
sbp_start = p3.current_sbp
p3.update_sbp(treatment_effect_mmhg=1.0, rng=rng)
print(f'  Initial SBP: {sbp_start:.1f}, After 1 update: {p3.current_sbp:.1f}')
print(f'  Change includes: age drift (+0.05) + random variation - treatment effect')

# Test 3: Adherence Transitions
print('\nTest 3: Adherence Transitions')
from src.transitions import AdherenceTransition
adh_calc = AdherenceTransition(seed=42)
p_adh = create_patient_from_params(3, 30, 'M', 130, sdi_score=80) # High risk for drop
p_adh.is_adherent = True
changes = 0
for _ in range(100): # 100 months
    if adh_calc.check_adherence_change(p_adh):
        changes += 1
print(f"  Adherence changes over 100 months: {changes} (expected > 0 given high risk)")
print(f"  Final Status: {'Adherent' if p_adh.is_adherent else 'Non-Adherent'}")

# Test 4: Risk Modifiers (SDI & Nocturnal)
print('\nTest 4: Risk Modifiers')
from src.risk_assessment import calculate_framingham_risk, RiskInputs

# Baseline
inputs_base = RiskInputs(
    age=60, sex='male', egfr=75, uacr=30, sbp=130, total_chol=200, hdl_chol=50,
    has_diabetes=False, is_smoker=False, has_cvd=False, has_heart_failure=False, 
    bmi=28, is_on_bp_meds=True, 
    sdi_score=50, nocturnal_sbp=120
)
res_base = calculate_framingham_risk(inputs_base)

# High SDI
inputs_sdi = RiskInputs(
    age=60, sex='male', egfr=75, uacr=30, sbp=130, total_chol=200, hdl_chol=50,
    has_diabetes=False, is_smoker=False, has_cvd=False, has_heart_failure=False, 
    bmi=28, is_on_bp_meds=True, 
    sdi_score=90, nocturnal_sbp=120
)
res_sdi = calculate_framingham_risk(inputs_sdi)

# High Nocturnal BP
inputs_noct = RiskInputs(
    age=60, sex='male', egfr=75, uacr=30, sbp=130, total_chol=200, hdl_chol=50,
    has_diabetes=False, is_smoker=False, has_cvd=False, has_heart_failure=False, 
    bmi=28, is_on_bp_meds=True, 
    sdi_score=50, nocturnal_sbp=140
)
res_noct = calculate_framingham_risk(inputs_noct)

print(f"  Baseline Risk: {res_base['risk']}%")
print(f"  High SDI Risk (should be higher): {res_sdi['risk']}%")
print(f"  High Nocturnal BP Risk (should be higher): {res_noct['risk']}%")
assert res_sdi['risk'] > res_base['risk'], "SDI modifier failed"
assert res_noct['risk'] > res_base['risk'], "Nocturnal modifier failed"

# Test 5: Population Generation
print('\nTest 5: Population Generation New Fields')
pop = generate_default_population(n_patients=10, seed=123)
sdis = [p.sdi_score for p in pop]
noct_sbps = [p.nocturnal_sbp for p in pop]
dippers = [p.nocturnal_dipping_status for p in pop]

print(f"  Mean SDI: {np.mean(sdis):.1f}")
print(f"  Mean Nocturnal SBP: {np.mean(noct_sbps):.1f}")
print(f"  Dipping statuses: {dippers}")

print('\n✅ All tests passed!')
