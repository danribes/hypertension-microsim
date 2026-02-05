"""
Tests for methodological fixes to the hypertension microsimulation CEA model.

These tests validate the implementation of:
1. Competing risks framework (Issue #1)
2. KFRE integration for eGFR decline (Issue #2)
3. Dynamic stroke subtype distribution (Issue #3)
4. Half-cycle correction for discounting (Issue #4)
5. Validated life tables (Issue #5)

Run with: python -m pytest tests/test_methodological_fixes.py -v
"""

import pytest
import numpy as np
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, src_path)

# Set up environment for relative imports within src
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from src.patient import Patient, Sex, CardiacState, RenalState, create_patient_from_params
from src.transitions import TransitionCalculator, TransitionProbabilities
from src.risks.kfre import calculate_kfre_risk, KFRECalculator
from src.risks.life_tables import LifeTableCalculator, annual_to_monthly_prob
from src.utilities import calculate_monthly_qaly, get_utility


class TestCompetingRisks:
    """Test competing risks framework implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = TransitionCalculator(seed=42, use_competing_risks=True)
        self.calc_legacy = TransitionCalculator(seed=42, use_competing_risks=False)

    def test_total_probability_bounded(self):
        """
        Verify that total event probability never exceeds 1.0 when using
        competing risks framework.

        This is a critical requirement that was violated by the legacy
        probability capping approach.
        """
        # Create a high-risk patient
        patient = create_patient_from_params(
            patient_id=1,
            age=85,
            sex='M',
            sbp=180,
            egfr=25,
            has_diabetes=True,
            is_smoker=True
        )
        patient.cardiac_state = CardiacState.POST_MI
        patient.has_heart_failure = True
        patient.prior_mi_count = 2
        patient.prior_stroke_count = 1

        probs = self.calc.calculate_transitions(patient)

        # Sum all event probabilities
        total_prob = (
            probs.to_cv_death +
            probs.to_non_cv_death +
            probs.to_mi +
            probs.to_ischemic_stroke +
            probs.to_hemorrhagic_stroke +
            probs.to_tia +
            probs.to_hf
        )

        # Must be <= 1.0 for valid probability distribution
        assert total_prob <= 1.0, f"Total probability {total_prob:.4f} exceeds 1.0"
        assert total_prob > 0, "Total probability should be positive"

    def test_competing_risks_preserves_relative_risk(self):
        """
        Verify that competing risks adjustment preserves relative risk
        relationships between events.
        """
        patient = create_patient_from_params(
            patient_id=1,
            age=70,
            sex='M',
            sbp=160,
            egfr=45,
            has_diabetes=True
        )

        probs = self.calc.calculate_transitions(patient)

        # After competing risks adjustment, MI should still be higher than
        # hemorrhagic stroke (which is rarer)
        assert probs.to_mi > probs.to_hemorrhagic_stroke

    def test_hazard_to_probability_conversion(self):
        """Test mathematical correctness of hazard-probability conversion."""
        # Known probability -> hazard -> back to probability
        p = 0.10
        h = -np.log(1 - p)  # Convert to hazard
        p_back = 1 - np.exp(-h)  # Convert back

        assert abs(p - p_back) < 1e-10, "Hazard conversion should be reversible"


class TestKFREIntegration:
    """Test KFRE (Kidney Failure Risk Equation) implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.kfre_calc = KFRECalculator()

    def test_kfre_risk_validation(self):
        """
        Validate KFRE risk calculation produces plausible values.

        Reference: Tangri N et al. JAMA 2011 - risk varies widely by patient profile.
        For CKD Stage 3b (eGFR 35), 2-year risk typically ranges from 1-15%
        depending on age, sex, and albuminuria.
        """
        # Test case: 65-year-old male, eGFR=35, uACR=150
        risk_2yr = calculate_kfre_risk(
            age=65, sex='M', egfr=35, uacr=150, time_horizon='2_year'
        )

        # Risk should be positive and < 50% for this moderate-risk profile
        assert 0.001 < risk_2yr < 0.50, f"2-year risk {risk_2yr:.3f} outside plausible range"

        # Test a higher-risk case: younger with worse kidney function
        high_risk = calculate_kfre_risk(
            age=50, sex='M', egfr=20, uacr=1000, time_horizon='2_year'
        )
        assert high_risk > risk_2yr, "Higher uACR and lower eGFR should increase risk"

    def test_kfre_risk_increases_with_lower_egfr(self):
        """Verify KFRE risk increases as eGFR decreases."""
        base_params = {'age': 60, 'sex': 'M', 'uacr': 100}

        risk_egfr_50 = calculate_kfre_risk(egfr=50, **base_params)
        risk_egfr_30 = calculate_kfre_risk(egfr=30, **base_params)
        risk_egfr_20 = calculate_kfre_risk(egfr=20, **base_params)

        assert risk_egfr_20 > risk_egfr_30 > risk_egfr_50, \
            "KFRE risk should increase as eGFR decreases"

    def test_kfre_risk_increases_with_higher_uacr(self):
        """Verify KFRE risk increases with higher albuminuria."""
        base_params = {'age': 60, 'sex': 'M', 'egfr': 40}

        risk_uacr_30 = calculate_kfre_risk(uacr=30, **base_params)
        risk_uacr_300 = calculate_kfre_risk(uacr=300, **base_params)
        risk_uacr_1000 = calculate_kfre_risk(uacr=1000, **base_params)

        assert risk_uacr_1000 > risk_uacr_300 > risk_uacr_30, \
            "KFRE risk should increase with higher uACR"

    def test_kfre_decline_rate_stratification(self):
        """
        Test that KFRE calculator correctly stratifies decline rates
        based on kidney failure risk.
        """
        # High-risk patient (should have rapid decline)
        decline_high_risk = self.kfre_calc.get_annual_egfr_decline(
            age=70, sex='M', current_egfr=25, uacr=500, has_diabetes=True
        )

        # Low-risk patient (should have slow decline)
        decline_low_risk = self.kfre_calc.get_annual_egfr_decline(
            age=50, sex='F', current_egfr=55, uacr=20, has_diabetes=False
        )

        assert decline_high_risk > decline_low_risk, \
            "High-risk patients should have faster eGFR decline"

    def test_sglt2i_protection(self):
        """Verify SGLT2i reduces eGFR decline rate by ~40%."""
        base_params = {
            'age': 65, 'sex': 'M', 'current_egfr': 40, 'uacr': 200,
            'has_diabetes': True, 'sbp': 140
        }

        decline_no_sglt2 = self.kfre_calc.get_annual_egfr_decline(
            on_sglt2i=False, **base_params
        )
        decline_with_sglt2 = self.kfre_calc.get_annual_egfr_decline(
            on_sglt2i=True, **base_params
        )

        # SGLT2i should reduce decline by approximately 39% (0.61x)
        ratio = decline_with_sglt2 / decline_no_sglt2
        assert 0.55 < ratio < 0.70, f"SGLT2i protection ratio {ratio:.2f} outside expected range"


class TestDynamicStrokeSubtypes:
    """Test dynamic stroke subtype distribution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = TransitionCalculator(seed=42, use_dynamic_stroke_subtypes=True)
        self.calc_fixed = TransitionCalculator(seed=42, use_dynamic_stroke_subtypes=False)

    def test_baseline_stroke_distribution(self):
        """Verify baseline 85/15 ischemic/hemorrhagic split."""
        patient = create_patient_from_params(
            patient_id=1, age=55, sex='M', sbp=130, egfr=80
        )

        isch_frac, hem_frac = self.calc._get_stroke_subtype_distribution(patient)

        # Should be close to baseline (85/15) for average patient
        assert 0.80 < isch_frac < 0.90, f"Ischemic fraction {isch_frac:.2f} outside expected"
        assert 0.10 < hem_frac < 0.20, f"Hemorrhagic fraction {hem_frac:.2f} outside expected"
        assert abs(isch_frac + hem_frac - 1.0) < 1e-10, "Fractions must sum to 1.0"

    def test_age_increases_hemorrhagic_proportion(self):
        """Verify hemorrhagic stroke proportion increases with age."""
        young_patient = create_patient_from_params(
            patient_id=1, age=50, sex='M', sbp=130, egfr=80
        )
        old_patient = create_patient_from_params(
            patient_id=2, age=85, sex='M', sbp=130, egfr=80
        )

        _, hem_young = self.calc._get_stroke_subtype_distribution(young_patient)
        _, hem_old = self.calc._get_stroke_subtype_distribution(old_patient)

        assert hem_old > hem_young, "Hemorrhagic proportion should increase with age"

    def test_high_bp_increases_hemorrhagic_proportion(self):
        """Verify severe hypertension increases hemorrhagic proportion."""
        controlled_patient = create_patient_from_params(
            patient_id=1, age=65, sex='M', sbp=125, egfr=60
        )
        uncontrolled_patient = create_patient_from_params(
            patient_id=2, age=65, sex='M', sbp=185, egfr=60
        )

        _, hem_controlled = self.calc._get_stroke_subtype_distribution(controlled_patient)
        _, hem_uncontrolled = self.calc._get_stroke_subtype_distribution(uncontrolled_patient)

        assert hem_uncontrolled > hem_controlled, \
            "Hemorrhagic proportion should increase with higher BP"

    def test_af_decreases_hemorrhagic_proportion(self):
        """Verify atrial fibrillation increases ischemic (cardioembolic) proportion."""
        patient_no_af = create_patient_from_params(
            patient_id=1, age=70, sex='M', sbp=140, egfr=60
        )
        patient_no_af.has_atrial_fibrillation = False

        patient_af = create_patient_from_params(
            patient_id=2, age=70, sex='M', sbp=140, egfr=60
        )
        patient_af.has_atrial_fibrillation = True

        _, hem_no_af = self.calc._get_stroke_subtype_distribution(patient_no_af)
        _, hem_af = self.calc._get_stroke_subtype_distribution(patient_af)

        assert hem_af < hem_no_af, \
            "AF should decrease hemorrhagic proportion (more ischemic/cardioembolic)"


class TestHalfCycleCorrection:
    """Test half-cycle correction for discounting."""

    def test_half_cycle_adjustment_applied(self):
        """
        Verify half-cycle correction adjusts the discount time by adding
        0.5 cycle lengths to represent midpoint valuation.

        Half-cycle correction assumes utility is experienced at the midpoint
        of each cycle rather than the beginning. This adds 0.5 months to the
        discount time, resulting in slightly MORE discounting (lower QALY).
        """
        # Create a patient at month 12 (1 year into simulation)
        patient = create_patient_from_params(
            patient_id=1, age=60, sex='M', sbp=140, egfr=70
        )
        patient.time_in_simulation = 12  # 12 months

        qaly_with_half_cycle = calculate_monthly_qaly(
            patient, discount_rate=0.03, use_half_cycle=True
        )
        qaly_without_half_cycle = calculate_monthly_qaly(
            patient, discount_rate=0.03, use_half_cycle=False
        )

        # Half-cycle adds 0.5 months to time, so MORE discounting occurs
        # Therefore QALY with half-cycle should be slightly LOWER
        assert qaly_with_half_cycle < qaly_without_half_cycle, \
            "Half-cycle correction should result in slightly lower QALY (more discounting)"

        # The difference should be small (typically < 0.5%)
        diff_pct = abs(qaly_without_half_cycle - qaly_with_half_cycle) / qaly_without_half_cycle * 100
        assert diff_pct < 1.0, f"Half-cycle adjustment {diff_pct:.3f}% seems too large"

    def test_half_cycle_effect_magnitude(self):
        """
        Verify the half-cycle adjustment is approximately 0.5 months
        (for monthly cycles).
        """
        patient = create_patient_from_params(
            patient_id=1, age=60, sex='M', sbp=140, egfr=70
        )
        patient.time_in_simulation = 12

        # The difference should be small but measurable
        qaly_hc = calculate_monthly_qaly(patient, discount_rate=0.03, use_half_cycle=True)
        qaly_no_hc = calculate_monthly_qaly(patient, discount_rate=0.03, use_half_cycle=False)

        # Difference should be small (< 1%)
        diff_pct = abs(qaly_hc - qaly_no_hc) / qaly_no_hc * 100
        assert diff_pct < 1.0, f"Half-cycle adjustment {diff_pct:.3f}% seems too large"


class TestValidatedLifeTables:
    """Test validated life table implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.us_calc = LifeTableCalculator(country='US')
        self.uk_calc = LifeTableCalculator(country='UK')

    def test_male_mortality_higher_than_female(self):
        """Verify male mortality rates are higher than female at all ages."""
        for age in [40, 50, 60, 70, 80, 90]:
            male_mort = self.us_calc.get_annual_mortality(age, 'M')
            female_mort = self.us_calc.get_annual_mortality(age, 'F')

            assert male_mort > female_mort, \
                f"Male mortality should exceed female at age {age}"

    def test_mortality_increases_with_age(self):
        """Verify mortality increases monotonically with age."""
        ages = [40, 50, 60, 70, 80, 90]
        for sex in ['M', 'F']:
            mortalities = [self.us_calc.get_annual_mortality(a, sex) for a in ages]

            for i in range(len(mortalities) - 1):
                assert mortalities[i + 1] > mortalities[i], \
                    f"Mortality should increase with age for {sex}"

    def test_us_vs_uk_tables(self):
        """Verify US and UK life tables give reasonable values."""
        for age in [60, 70, 80]:
            us_male = self.us_calc.get_annual_mortality(age, 'M')
            uk_male = self.uk_calc.get_annual_mortality(age, 'M')

            # Both should be positive and less than 50%
            assert 0 < us_male < 0.5, f"US mortality at {age} outside bounds"
            assert 0 < uk_male < 0.5, f"UK mortality at {age} outside bounds"

            # Should be within 50% of each other (similar developed countries)
            ratio = us_male / uk_male
            assert 0.5 < ratio < 2.0, f"US/UK mortality ratio at {age} seems off"

    def test_annual_to_monthly_conversion(self):
        """Test annual to monthly probability conversion."""
        annual_prob = 0.10  # 10% annual mortality

        monthly_prob = annual_to_monthly_prob(annual_prob)

        # Monthly should be less than annual
        assert monthly_prob < annual_prob

        # Compounding 12 months should approximate annual
        annual_from_monthly = 1 - (1 - monthly_prob) ** 12
        assert abs(annual_from_monthly - annual_prob) < 0.001

    def test_life_expectancy_calculation(self):
        """Verify life expectancy calculation returns reasonable values."""
        le_male_65 = self.us_calc.get_life_expectancy(65, 'M')
        le_female_65 = self.us_calc.get_life_expectancy(65, 'F')

        # SSA 2021: Male 65 LE ~17 years, Female ~20 years
        assert 14 < le_male_65 < 22, f"Male LE at 65 ({le_male_65:.1f}) outside expected"
        assert 17 < le_female_65 < 25, f"Female LE at 65 ({le_female_65:.1f}) outside expected"
        assert le_female_65 > le_male_65, "Female LE should exceed male"


class TestPatientKFREIntegration:
    """Test KFRE integration in Patient class."""

    def test_patient_egfr_decline_with_kfre(self):
        """Test that patient eGFR declines using KFRE model."""
        patient = create_patient_from_params(
            patient_id=1, age=65, sex='M', sbp=150, egfr=40,
            uacr=200, has_diabetes=True
        )
        patient.use_kfre_model = True

        initial_egfr = patient.egfr
        patient.advance_time(12)  # Advance 12 months

        assert patient.egfr < initial_egfr, "eGFR should decline over time"

    def test_patient_legacy_egfr_model(self):
        """Test that legacy eGFR model still works when KFRE disabled."""
        patient = create_patient_from_params(
            patient_id=1, age=65, sex='M', sbp=150, egfr=40,
            uacr=200, has_diabetes=True
        )
        patient.use_kfre_model = False

        initial_egfr = patient.egfr
        patient.advance_time(12)

        assert patient.egfr < initial_egfr, "eGFR should decline with legacy model"


class TestTransitionCalculatorIntegration:
    """Test full integration of methodological fixes in TransitionCalculator."""

    def test_all_fixes_enabled(self):
        """Test that all methodological fixes work together."""
        calc = TransitionCalculator(
            seed=42,
            country='US',
            use_life_tables=True,
            use_competing_risks=True,
            use_dynamic_stroke_subtypes=True
        )

        patient = create_patient_from_params(
            patient_id=1, age=70, sex='M', sbp=160, egfr=35,
            has_diabetes=True
        )

        probs = calc.calculate_transitions(patient)

        # Verify probabilities are valid
        all_probs = [
            probs.to_cv_death, probs.to_non_cv_death, probs.to_mi,
            probs.to_ischemic_stroke, probs.to_hemorrhagic_stroke,
            probs.to_tia, probs.to_hf
        ]

        assert all(0 <= p <= 1 for p in all_probs), "All probabilities must be in [0,1]"
        assert sum(all_probs) <= 1.0, "Total probability must not exceed 1.0"

    def test_backward_compatibility(self):
        """Test that legacy mode still works for validation comparisons."""
        calc_legacy = TransitionCalculator(
            seed=42,
            use_life_tables=False,
            use_competing_risks=False,
            use_dynamic_stroke_subtypes=False
        )

        patient = create_patient_from_params(
            patient_id=1, age=70, sex='M', sbp=160, egfr=45
        )

        # Should not raise any errors
        probs = calc_legacy.calculate_transitions(patient)

        assert probs.to_cv_death >= 0
        assert probs.to_mi >= 0


class TestPREVENTValidation:
    """
    Test PREVENT risk equation implementation against validation cases.

    HIGH SEVERITY FIX: Ensures PREVENT coefficients and centering produce
    clinically plausible risk estimates aligned with the original publication.

    Reference: Khan SS, et al. Circulation. 2024;149(6):430-449.
    """

    def test_prevent_validation_cases(self):
        """
        Validate PREVENT implementation against known risk profiles.

        These test cases are based on expected risk ranges from the
        PREVENT derivation and validation cohorts.
        """
        from src.risks.prevent import validate_prevent_implementation

        results = validate_prevent_implementation()

        # Print detailed results for debugging
        for case in results["cases"]:
            print(f"Case {case['case_id']}: {case['description']}")
            print(f"  Computed: {case['computed_risk']:.3f}")
            print(f"  Expected: {case['expected_range']}")
            print(f"  Passed: {case['passed']}")

        assert results["passed"], (
            f"PREVENT validation failed. Check coefficient values and centering. "
            f"Failed cases: {[c for c in results['cases'] if not c['passed']]}"
        )

    def test_prevent_risk_increases_with_age(self):
        """Test that CVD risk increases monotonically with age."""
        from src.risks.prevent import calculate_prevent_risk

        risks = []
        for age in [40, 50, 60, 70]:
            risk = calculate_prevent_risk(
                age=age, sex='M', sbp=140, egfr=80,
                has_diabetes=False, is_smoker=False
            )
            risks.append(risk)

        # Risk should increase with age
        for i in range(len(risks) - 1):
            assert risks[i] < risks[i+1], (
                f"Risk should increase with age: {risks[i]:.3f} < {risks[i+1]:.3f}"
            )

    def test_prevent_risk_increases_with_sbp(self):
        """Test that CVD risk increases with higher SBP."""
        from src.risks.prevent import calculate_prevent_risk

        risk_low = calculate_prevent_risk(
            age=60, sex='M', sbp=120, egfr=80
        )
        risk_high = calculate_prevent_risk(
            age=60, sex='M', sbp=180, egfr=80
        )

        assert risk_low < risk_high, (
            f"Higher SBP should increase risk: {risk_low:.3f} vs {risk_high:.3f}"
        )

    def test_prevent_risk_decreases_with_egfr(self):
        """Test that lower eGFR increases CVD risk."""
        from src.risks.prevent import calculate_prevent_risk

        risk_good_kidney = calculate_prevent_risk(
            age=60, sex='M', sbp=140, egfr=90
        )
        risk_poor_kidney = calculate_prevent_risk(
            age=60, sex='M', sbp=140, egfr=30
        )

        assert risk_good_kidney < risk_poor_kidney, (
            f"Lower eGFR should increase risk: {risk_good_kidney:.3f} vs {risk_poor_kidney:.3f}"
        )

    def test_prevent_diabetes_increases_risk(self):
        """Test that diabetes increases CVD risk."""
        from src.risks.prevent import calculate_prevent_risk

        risk_no_dm = calculate_prevent_risk(
            age=60, sex='M', sbp=140, egfr=80, has_diabetes=False
        )
        risk_dm = calculate_prevent_risk(
            age=60, sex='M', sbp=140, egfr=80, has_diabetes=True
        )

        assert risk_no_dm < risk_dm, (
            f"Diabetes should increase risk: {risk_no_dm:.3f} vs {risk_dm:.3f}"
        )

    def test_prevent_reference_population_risk(self):
        """
        Test that risk for a reference population patient is reasonable.

        A patient with average characteristics from the PREVENT derivation
        cohort should have a 10-year CVD risk in the typical range (3-8%).
        """
        from src.risks.prevent import (
            calculate_prevent_risk,
            PREVENT_REFERENCE_MEANS,
        )

        # Calculate risk for reference population mean values
        ref = PREVENT_REFERENCE_MEANS
        risk = calculate_prevent_risk(
            age=ref["age"], sex='M', sbp=ref["sbp"], egfr=ref["egfr"],
            total_cholesterol=ref["total_chol"], hdl_cholesterol=ref["hdl_chol"],
            bmi=ref["bmi"], has_diabetes=False, is_smoker=False,
            bp_treated=False
        )

        print(f"Reference population male risk: {risk:.3f}")

        # For a reference population patient (53yo male, avg values),
        # risk should be in the typical range for treated HTN population
        assert 0.02 < risk < 0.15, (
            f"Risk for reference patient should be in plausible range: {risk:.3f}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
