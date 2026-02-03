from src.patient import Patient, Sex, create_patient_from_params, NeuroState
from src.transitions import NeuroTransition
from src.simulation import Simulation, SimulationConfig, Treatment
import numpy as np

def test_neuro_transition_rates():
    print("\nTest 1: Neuro Transition Rates (Normal -> MCI -> Dementia)")
    nt = NeuroTransition(seed=42)
    
    # 1. Healthy Baseline (Age 60, BP 120) -> Should match base rates approx
    p_base = create_patient_from_params(1, 60, 'M', 120)
    p_base.neuro_state = NeuroState.NORMAL_COGNITION
    
    # Run Monte Carlo for annual prob
    n_trials = 10000
    mci_events = 0
    dem_events = 0
    for _ in range(n_trials):
        p_base.neuro_state = NeuroState.NORMAL_COGNITION
        # Run 12 months
        for _ in range(12):
            nt.check_neuro_progression(p_base)
            if p_base.neuro_state != NeuroState.NORMAL_COGNITION:
                break
        
        if p_base.neuro_state == NeuroState.MILD_COGNITIVE_IMPAIRMENT:
            mci_events += 1
        elif p_base.neuro_state == NeuroState.DEMENTIA:
            dem_events += 1
            
    rate_mci = mci_events / n_trials
    print(f"  Base Rate to MCI (Age 60, BP 120): {rate_mci:.4f} (Expected ~0.02)")
    assert 0.015 < rate_mci < 0.025
    
    # 2. High Risk (Age 80, BP 160)
    # Age factor (80): (80-65)/5 = 3 steps -> 2^3 = 8x multiplier
    # BP factor (160): (160-120)/10 = 4 steps -> 1 + (4*0.15) = 1.6x multiplier
    # Total Mult = 8 * 1.6 = 12.8x risk
    
    p_risk = create_patient_from_params(2, 80, 'M', 160)
    mci_events_risk = 0
    for _ in range(n_trials):
        p_risk.neuro_state = NeuroState.NORMAL_COGNITION
        for _ in range(12):
            nt.check_neuro_progression(p_risk)
            if p_risk.neuro_state != NeuroState.NORMAL_COGNITION:
                break
        if p_risk.neuro_state == NeuroState.MILD_COGNITIVE_IMPAIRMENT:
            mci_events_risk += 1
            
    rate_mci_risk = mci_events_risk / n_trials
    print(f"  High Risk Rate to MCI (Age 80, BP 160): {rate_mci_risk:.4f} (Expected ~0.02 * 12.8 = 0.25)")
    # Allow wide range due to compounding monthly probs vs simple annual mult
    assert 0.20 < rate_mci_risk < 0.35 

def test_simulation_integration_neuro():
    print("\nTest 2: Simulation Integration (Dementia Cases)")
    # Run small sim for 10 years with old population
    config = SimulationConfig(
        n_patients=100,
        time_horizon_months=120, # 10 years
        show_progress=False,
        seed=123
    )
    sim = Simulation(config)
    # Create elderly cohort to ensure events
    patients = [create_patient_from_params(i, 80, 'F', 150) for i in range(100)]
    
    results = sim.run(patients, Treatment.STANDARD_CARE)
    
    print(f"  Dementia Cases (N=100, 10yrs, Age 80 start): {results.dementia_cases}")
    assert results.dementia_cases > 0
    assert hasattr(results, 'dementia_cases')

if __name__ == "__main__":
    test_neuro_transition_rates()
    test_simulation_integration_neuro()
    print("\n✅ All Phase 3 (Dementia) tests passed!")
