
import unittest
import numpy as np
from src.patient import Patient, Treatment, Sex
from src.transitions import TransitionCalculator
from src.population import PopulationGenerator, PopulationParams

class TestSGLT2Logic(unittest.TestCase):
    
    def setUp(self):
        self.rng = np.random.default_rng(42)
        # Create a patient with CKD (eGFR 45) and Heart Failure
        # Using correct positional/keyword arguments matching Patient.__init__
        self.patient_control = Patient(
            patient_id=1, 
            age=65, 
            sex=Sex.MALE, 
            baseline_sbp=140, baseline_dbp=80,
            current_sbp=140, current_dbp=80,
            egfr=45.0, 
            uacr=30.0,
            total_cholesterol=200.0, 
            hdl_cholesterol=50.0,
            has_diabetes=True, 
            has_heart_failure=True,
            on_sglt2_inhibitor=False,
            treatment=Treatment.STANDARD_CARE
        )
        # Clone for SGLT2 (Intervention Arm)
        self.patient_sglt2 = Patient(
            patient_id=2, 
            age=65, 
            sex=Sex.MALE, 
            baseline_sbp=140, baseline_dbp=80,
            current_sbp=140, current_dbp=80,
            egfr=45.0, 
            uacr=30.0,
            total_cholesterol=200.0, 
            hdl_cholesterol=50.0,
            has_diabetes=True, 
            has_heart_failure=True,
            on_sglt2_inhibitor=True,
            treatment=Treatment.STANDARD_CARE
        )
        self.t_calc = TransitionCalculator(seed=42)

    def test_hf_risk_reduction(self):
        print("\nTest 1: Heart Failure Risk Reduction")
        
        # We need patients NOT to have HF to calculate incidence risk
        self.patient_control.has_heart_failure = False
        self.patient_sglt2.has_heart_failure = False
        
        # Calculate monthly probability of NEW HF event
        probs_ctrl = self.t_calc.calculate_transitions(self.patient_control)
        probs_sglt2 = self.t_calc.calculate_transitions(self.patient_sglt2)
        
        print(f"Control Monthly HF Prob (New Onset): {probs_ctrl.to_hf:.6f}")
        print(f"SGLT2   Monthly HF Prob (New Onset): {probs_sglt2.to_hf:.6f}")
        
        ratio = probs_sglt2.to_hf / probs_ctrl.to_hf
        print(f"Risk Ratio: {ratio:.2f}")
        
        # Expect ~0.70 ratio
        self.assertLess(ratio, 0.71)
        self.assertGreater(ratio, 0.69)
        
    def test_renal_protection(self):
        # Verify eGFR decline is slower
        
        # Reset eGFR to same baseline
        self.patient_control.egfr = 60.0
        self.patient_sglt2.egfr = 60.0
        
        print("\nTest 2: Renal Protection (eGFR Decline)")
        print(f"Start eGFR: 60.0")
        
        # Simulate 5 years (60 months)
        months = 60
        step_size = 1.0
        
        for _ in range(months):
            # Advance time by 1 month, which calls _update_egfr(1.0) internally
            # We call the internal method directly to isolate eGFR logic if preferred,
            # but advance_time handles age updates too which affect eGFR.
            # Let's call the internal method to be precise about what we are testing (logic only)
            self.patient_control._update_egfr(step_size)
            self.patient_sglt2._update_egfr(step_size)
            
        print(f"Control End eGFR (5y): {self.patient_control.egfr:.2f}")
        print(f"SGLT2   End eGFR (5y): {self.patient_sglt2.egfr:.2f}")
        
        decline_ctrl = 60.0 - self.patient_control.egfr
        decline_sglt2 = 60.0 - self.patient_sglt2.egfr
        
        print(f"Control Decline: {decline_ctrl:.2f}")
        print(f"SGLT2   Decline: {decline_sglt2:.2f}")
        
        ratio = decline_sglt2 / decline_ctrl
        print(f"Decline Ratio: {ratio:.2f}")
        
        # SGLT2 logic applies 0.60 multiplier to decline
        self.assertLess(ratio, 0.70)
        self.assertGreater(ratio, 0.50)
    
    def test_population_assignment(self):
        # Verify ~40% uptake in eligible patients
        params = PopulationParams(n_patients=1000, seed=123)
        gen = PopulationGenerator(params)
        pop = gen.generate()
        
        # Identify eligible (CKD < 60 or HF)
        eligible = [p for p in pop if p.egfr < 60 or p.has_heart_failure]
        on_drug = [p for p in eligible if p.on_sglt2_inhibitor]
        
        uptake = len(on_drug) / len(eligible) if eligible else 0
        print("\nTest 3: Population Uptake")
        print(f"Eligible Patients: {len(eligible)}")
        print(f"On SGLT2i: {len(on_drug)}")
        print(f"Uptake Rate: {uptake:.2f}")
        
        self.assertGreater(uptake, 0.35)
        self.assertLess(uptake, 0.45)

if __name__ == '__main__':
    unittest.main()
