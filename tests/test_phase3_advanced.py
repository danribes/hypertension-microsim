from src.patient import Patient, Sex, create_patient_from_params, NeuroState
from src.transitions import TransitionCalculator, TransitionProbabilities
from src.treatment import TreatmentManager, Treatment
import numpy as np

def test_white_coat_hypertension_impact():
    print("\nTest 1: White Coat Hypertension (WCH) Impact on Risk")
    
    # Create two identical patients in terms of demographics and OFFICE BP
    # Patient A: True Hypertension (Office 150, True 150)
    p_true_htn = create_patient_from_params(1, 65, 'M', 150)
    p_true_htn.white_coat_effect = 0.0
    p_true_htn.true_mean_sbp = 150.0  # Explicit set to be sure
    
    # Patient B: White Coat (Office 150, True 130) -> 20mmHg effect
    p_wch = create_patient_from_params(2, 65, 'M', 150)
    p_wch.white_coat_effect = 20.0
    p_wch.true_mean_sbp = 130.0 # Explicit set
    
    tc = TransitionCalculator(seed=42)
    
    # Calculate risks
    probs_true = tc.calculate_transitions(p_true_htn)
    probs_wch = tc.calculate_transitions(p_wch)
    
    # Monthly risk of MI
    print(f"  True HTN (150/150): Monthly MI Risk = {probs_true.to_mi:.6f}")
    print(f"  WCH      (150/130): Monthly MI Risk = {probs_wch.to_mi:.6f}")
    
    ratio = probs_wch.to_mi / probs_true.to_mi
    print(f"  Risk Ratio (WCH / True): {ratio:.2f}")
    
    # WCH patient should have lower risk
    assert probs_wch.to_mi < probs_true.to_mi
    assert ratio < 0.92 # Expecting ~10-15% reduction (ratio ~0.85-0.90)
    print("  ✅ WCH correctly lowers physiological risk despite same Office BP.")

def test_clinical_inertia():
    print("\nTest 2: Clinical Inertia (Provider Failure to Titrate)")
    tm = TreatmentManager(seed=42)
    
    # Patient with Uncontrolled BP (145 mmHg)
    p_uncontrolled = create_patient_from_params(3, 60, 'F', 145)
    
    # Run 1000 simulated visits
    intentions = 0
    failures = 0
    n_visits = 1000
    
    for _ in range(n_visits):
        intensify = tm.should_intensify_treatment(p_uncontrolled)
        if intensify:
            intentions += 1
        else:
            failures += 1
            
    inertia_rate = failures / n_visits
    print(f"  Visits: {n_visits}")
    print(f"  Intensifications: {intentions}")
    print(f"  Inertia (No Action): {failures}")
    print(f"  Observed Inertia Rate: {inertia_rate:.2f} (Target ~0.50)")
    
    assert 0.45 < inertia_rate < 0.55
    print("  ✅ Clinical Inertia probabilistic model verified.")

def test_control_vs_risk_disconnect():
    print("\nTest 3: Control Rate vs Risk Disconnect")
    # Verify that 'is_bp_controlled' property uses OFFICE BP (Standard of Care definition)
    # even if True BP is lower.
    
    # Patient C: Office 145 (Uncontrolled), True 125 (Controlled physiological)
    p_c = create_patient_from_params(4, 60, 'M', 145)
    p_c.white_coat_effect = 20.0
    p_c.true_mean_sbp = 125.0
    
    print(f"  Patient Office BP: {p_c.current_sbp}")
    print(f"  Patient True BP:   {p_c.true_mean_sbp}")
    print(f"  Is Controlled?     {p_c.is_bp_controlled}")
    
    # Standard of care guidelines definition: Based on OFFICE BP
    assert p_c.is_bp_controlled == False 
    print("  ✅ 'Controlled' status correctly reflects Office BP (Standard of Care).")


if __name__ == "__main__":
    test_white_coat_hypertension_impact()
    test_clinical_inertia()
    test_control_vs_risk_disconnect()
    print("\n✅ All Advanced Features (G & I) tests passed!")
