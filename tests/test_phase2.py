# import pytest
from src.patient import Patient, CardiacState, Sex, Treatment, create_patient_from_params
from src.costs.costs import US_COSTS, get_productivity_loss, get_acute_absenteeism_cost
from src.transitions import AdherenceTransition
from src.simulation import Simulation, SimulationConfig
import numpy as np

def test_indirect_costs():
    print("\nTest 1: Indirect Cost Calculation")
    
    # 1. Working age patient (50) with no events
    p_healthy = create_patient_from_params(1, 50, 'M', 130)
    loss = get_productivity_loss(p_healthy, US_COSTS)
    print(f"  Healthy (50yo): ${loss:.2f} (Expected: 0.0)")
    assert loss == 0.0
    
    # 2. Retired patient (70) with heart failure
    p_retired = create_patient_from_params(2, 70, 'M', 130)
    p_retired.cardiac_state = CardiacState.CHRONIC_HF
    loss = get_productivity_loss(p_retired, US_COSTS)
    print(f"  Retired (70yo) with HF: ${loss:.2f} (Expected: 0.0)")
    assert loss == 0.0
    
    # 3. Working age (50) with Stroke Disability
    p_stroke = create_patient_from_params(3, 50, 'M', 130)
    p_stroke.cardiac_state = CardiacState.POST_STROKE
    loss_annual = get_productivity_loss(p_stroke, US_COSTS, is_monthly=False)
    
    expected_wage = US_COSTS.daily_wage * 250 # $60k
    expected_loss = expected_wage * US_COSTS.disability_multiplier_stroke # 0.20 -> $12k
    print(f"  Stroke Disability (50yo): ${loss_annual:,.2f} (Expected: ${expected_loss:,.2f})")
    assert abs(loss_annual - expected_loss) < 1.0

def test_acute_absenteeism():
    print("\nTest 2: Acute Absenteeism")
    markup = get_acute_absenteeism_cost("acute_mi", US_COSTS, age=50)
    expected = US_COSTS.daily_wage * US_COSTS.absenteeism_acute_mi_days # 240 * 7 = 1680
    print(f"  Acute MI (50yo): ${markup:,.2f} (Expected: ${expected:,.2f})")
    assert markup == expected
    
    markup_retired = get_acute_absenteeism_cost("acute_mi", US_COSTS, age=70)
    print(f"  Acute MI (70yo): ${markup_retired:,.2f} (Expected: 0.0)")
    assert markup_retired == 0.0

def test_adherence_delivery_modifier():
    print("\nTest 3: Delivery Mechanism Adherence Effect")
    adc = AdherenceTransition(seed=42)
    
    # Create valid patient
    p = create_patient_from_params(1, 55, 'M', 130, sdi_score=50) # Neutral risk
    p.time_Since_adherence_change = 0
    p.is_adherent = True
    
    # 1. Test Spironolactone (Mono/Add-on) -> Base Rate
    p.treatment = Treatment.SPIRONOLACTONE
    drops_spi = 0
    n_trials = 10000
    for _ in range(n_trials):
        p.is_adherent = True # Reset
        if adc.check_adherence_change(p):
            drops_spi += 1
            
    prob_spi = drops_spi / n_trials
    print(f"  Spironolactone Drop Rate (Monthly approx): {prob_spi:.4f}")
    
    # 2. Test IXA-001 (FDC) -> Reduced Rate
    p.treatment = Treatment.IXA_001
    drops_ixa = 0
    for _ in range(n_trials):
        p.is_adherent = True # Reset
        if adc.check_adherence_change(p):
            drops_ixa += 1
            
    prob_ixa = drops_ixa / n_trials
    print(f"  IXA-001 Drop Rate (Monthly approx): {prob_ixa:.4f}")
    
    # Expectation: IXA < SPI
    ratio = prob_ixa / prob_spi
    print(f"  Ratio (IXA/SPI): {ratio:.2f} (Expected ~0.48)")
    assert prob_ixa < prob_spi
    assert 0.40 < ratio < 0.60 # Allow some stochastic wiggle room

def test_simulation_integration():
    print("\nTest 4: Simulation Integration")
    config = SimulationConfig(
        n_patients=50,
        time_horizon_months=24, # 2 years
        show_progress=False,
        seed=123
    )
    sim = Simulation(config)
    patients = [create_patient_from_params(i, 55, 'M', 130) for i in range(50)]
    
    # Force some disability? Hard to force in sim without events.
    # But check if indirect costs > 0 (some events might happen)
    results = sim.run(patients, Treatment.SPIRONOLACTONE)
    
    print(f"  Total Indirect Costs: ${results.total_indirect_costs:,.2f}")
    print(f"  Mean Indirect Costs: ${results.total_indirect_costs/50:,.2f}")
    
    # Check if object structure holds
    assert hasattr(results, 'total_indirect_costs')

if __name__ == "__main__":
    test_indirect_costs()
    test_acute_absenteeism()
    test_adherence_delivery_modifier()
    test_simulation_integration()
    print("\n✅ All Phase 2 tests passed!")
