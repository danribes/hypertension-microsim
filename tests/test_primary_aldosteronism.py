"""
Test primary aldosteronism treatment response modifier integration.

Verifies that PA patients receive enhanced treatment response to
aldosterone-targeting therapies like IXA-001.

Option B modifiers (Feb 2026):
  - IXA-001: 1.70× (ASI provides complete aldosterone suppression)
  - Spironolactone: 1.40× (MRA blocks receptor, but aldosterone escape)
  - Standard care: 0.75× (largely ineffective in PA)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
try:
    import pytest
except ImportError:
    pytest = None
from src.patient import Patient, Treatment, Sex
from src.risk_assessment import BaselineRiskProfile
from src.treatment import TreatmentManager


def create_test_patient(patient_id: int, has_pa: bool) -> Patient:
    """Create a test patient with or without primary aldosteronism."""
    patient = Patient(
        patient_id=patient_id,
        age=55,
        sex=Sex.MALE,
        baseline_sbp=165,
        baseline_dbp=95,
        current_sbp=165,
        current_dbp=95,
        egfr=75,
        uacr=30,
        total_cholesterol=200,
        hdl_cholesterol=45,
        has_primary_aldosteronism=has_pa
    )
    patient.baseline_risk_profile = BaselineRiskProfile(
        has_primary_aldosteronism=has_pa
    )
    return patient


class TestPrimaryAldosteronismModifier:
    """Tests for primary aldosteronism treatment response modifier."""

    def test_treatment_response_modifier_pa_patient(self):
        """PA patients should have 1.70x modifier for IXA-001 (Option B)."""
        patient = create_test_patient(1, has_pa=True)
        modifier = patient.baseline_risk_profile.get_treatment_response_modifier("IXA_001")
        assert modifier == 1.70

    def test_treatment_response_modifier_non_pa_patient(self):
        """Non-PA patients should have 1.0x modifier for IXA-001."""
        patient = create_test_patient(1, has_pa=False)
        modifier = patient.baseline_risk_profile.get_treatment_response_modifier("IXA_001")
        assert modifier == 1.0

    def test_treatment_response_modifier_spironolactone(self):
        """PA patients should have 1.40x modifier for spironolactone (Option B)."""
        patient = create_test_patient(1, has_pa=True)
        modifier = patient.baseline_risk_profile.get_treatment_response_modifier("SPIRONOLACTONE")
        assert modifier == 1.40

    def test_treatment_response_modifier_standard_care(self):
        """PA patients should have 0.75x modifier for standard care (Option B)."""
        patient = create_test_patient(1, has_pa=True)
        modifier = patient.baseline_risk_profile.get_treatment_response_modifier("STANDARD_CARE")
        assert modifier == 0.75


class TestTreatmentAssignmentIntegration:
    """Tests for PA modifier integration in treatment assignment."""

    def test_pa_patients_get_enhanced_sbp_reduction(self):
        """PA patients should get ~70% better SBP reduction from IXA-001 (Option B)."""
        n_trials = 1000
        pa_reductions = []
        non_pa_reductions = []

        for i in range(n_trials):
            # PA patient
            mgr_pa = TreatmentManager(seed=i)
            p_pa = create_test_patient(1, has_pa=True)
            reduction_pa = mgr_pa.assign_treatment(p_pa, Treatment.IXA_001)
            pa_reductions.append(reduction_pa)

            # Non-PA patient with same seed
            mgr_no_pa = TreatmentManager(seed=i)
            p_no_pa = create_test_patient(2, has_pa=False)
            reduction_no_pa = mgr_no_pa.assign_treatment(p_no_pa, Treatment.IXA_001)
            non_pa_reductions.append(reduction_no_pa)

        mean_pa = np.mean(pa_reductions)
        mean_no_pa = np.mean(non_pa_reductions)
        ratio = mean_pa / mean_no_pa

        # Allow 5% tolerance for randomness
        assert abs(ratio - 1.70) < 0.05, f"Expected ratio ~1.70, got {ratio:.2f}"

    def test_sbp_reduction_magnitude(self):
        """Verify SBP reductions are in expected clinical range."""
        mgr = TreatmentManager(seed=42)
        patient = create_test_patient(1, has_pa=False)
        reduction = mgr.assign_treatment(patient, Treatment.IXA_001)

        # IXA-001 has mean 20 mmHg reduction, SD 8
        # 99% of values should be between 0 and 44 mmHg
        assert 0 <= reduction <= 50, f"SBP reduction {reduction} outside expected range"


if __name__ == "__main__":
    # Run quick verification
    print("=" * 50)
    print("Testing get_treatment_response_modifier()")
    print("=" * 50)

    p_pa = create_test_patient(1, has_pa=True)
    p_no_pa = create_test_patient(2, has_pa=False)

    mod_pa = p_pa.baseline_risk_profile.get_treatment_response_modifier("IXA_001")
    mod_no_pa = p_no_pa.baseline_risk_profile.get_treatment_response_modifier("IXA_001")

    print(f"PA patient IXA-001 modifier:     {mod_pa:.2f}x")
    print(f"Non-PA patient IXA-001 modifier: {mod_no_pa:.2f}x")
    print(f"Expected: PA=1.70x, Non-PA=1.00x")

    print("\n" + "=" * 50)
    print("Testing assign_treatment() integration")
    print("=" * 50)

    n_trials = 1000
    pa_reductions = []
    non_pa_reductions = []

    for i in range(n_trials):
        mgr = TreatmentManager(seed=i)
        p_pa = create_test_patient(1, has_pa=True)
        reduction_pa = mgr.assign_treatment(p_pa, Treatment.IXA_001)
        pa_reductions.append(reduction_pa)

        mgr2 = TreatmentManager(seed=i)
        p_no_pa = create_test_patient(2, has_pa=False)
        reduction_no_pa = mgr2.assign_treatment(p_no_pa, Treatment.IXA_001)
        non_pa_reductions.append(reduction_no_pa)

    mean_pa = np.mean(pa_reductions)
    mean_no_pa = np.mean(non_pa_reductions)
    ratio = mean_pa / mean_no_pa

    print(f"Mean SBP reduction (PA patients):     {mean_pa:.2f} mmHg")
    print(f"Mean SBP reduction (non-PA patients): {mean_no_pa:.2f} mmHg")
    print(f"Ratio (PA/non-PA):                    {ratio:.2f}x")
    print(f"Expected ratio:                       1.70x")

    if abs(ratio - 1.70) < 0.05:
        print("\n✓ SUCCESS: PA treatment response modifier is working correctly!")
    else:
        print(f"\n✗ FAILED: Expected ratio ~1.70, got {ratio:.2f}")
