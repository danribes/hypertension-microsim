
import unittest
import numpy as np
from src.patient import Patient, Treatment, Sex
from src.treatment import TreatmentManager
from src.costs.costs import US_COSTS
from src.simulation import Simulation, SimulationConfig

class TestSafetyRules(unittest.TestCase):
    
    def setUp(self):
        self.rng = np.random.default_rng(42)
        # Create a patient with CKD (eGFR 25) who is prone to Hyperkalemia
        self.patient_mra = Patient(
            patient_id=1, age=70, sex=Sex.MALE, 
            baseline_sbp=140, baseline_dbp=80,
            current_sbp=140, current_dbp=80,
            egfr=25.0, uacr=300.0, # Stage 4 CKD
            total_cholesterol=200.0, hdl_cholesterol=50.0,
            has_diabetes=True, 
            treatment=Treatment.SPIRONOLACTONE
        )
        self.treatment_mgr = TreatmentManager(seed=42)

    def test_potassium_drift(self):
        print("\nTest 1: Potassium Drift & Hyperkalemia")
        # Baseline K+
        print(f"Start K+: {self.patient_mra.serum_potassium:.2f}")
        
        # Advance 12 months on Spironolactone with low eGFR
        # Should see trend upwards
        for i in range(12):
            self.patient_mra.advance_time(1.0)
            if i % 3 == 0:
                print(f"Month {i}: K+ {self.patient_mra.serum_potassium:.2f} (Hyperkalemia: {self.patient_mra.has_hyperkalemia})")
        
        self.assertGreater(self.patient_mra.serum_potassium, 4.2)
        
    def test_safety_stop_logic(self):
        print("\nTest 2: Safety Stop Rule")
        # Force Hyperkalemia
        self.patient_mra.serum_potassium = 5.8
        self.patient_mra.has_hyperkalemia = True
        
        # Check rule
        stop_needed = self.treatment_mgr.check_safety_stop_rules(self.patient_mra)
        print(f"K+ = 5.8, On MRA -> Stop Needed? {stop_needed}")
        
        self.assertTrue(stop_needed)
        
        # Check if NOT on MRA
        self.patient_mra.treatment = Treatment.STANDARD_CARE
        stop_needed_std = self.treatment_mgr.check_safety_stop_rules(self.patient_mra)
        print(f"K+ = 5.8, On Std Care -> Stop Needed? {stop_needed_std}")
        
        self.assertFalse(stop_needed_std)
        
    def test_cost_accrual(self):
        print("\nTest 3: Lab Cost Accrual")
        # Simulate 1 cycle (3 months)
        # We need to use Simulation class or mimic loop
        # Let's mimic loop logic for simplicity
        
        patient = self.patient_mra
        patient.treatment = Treatment.SPIRONOLACTONE
        patient.time_in_simulation = 0
        patient.cumulative_costs = 0
        
        # Cycle 0 (Month 0): 0 % 3 == 0 -> Check (Cost accrues)
        patient.accrue_costs(US_COSTS.lab_test_cost_k)
        
        print(f"Lab Cost Accrued: ${patient.cumulative_costs}")
        self.assertEqual(patient.cumulative_costs, 15.0)

if __name__ == '__main__':
    unittest.main()
