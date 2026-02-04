"""
Tests for the Probabilistic Sensitivity Analysis (PSA) module.
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.psa import (
    ParameterDistribution,
    CorrelationGroup,
    CholeskySampler,
    PSARunner,
    PSAResults,
    PSAIteration,
    get_default_parameter_distributions,
    get_default_correlation_groups,
    run_psa,
)
from src.simulation import SimulationConfig


class TestParameterDistribution:
    """Tests for ParameterDistribution class."""

    def test_normal_sampling(self):
        """Test normal distribution sampling."""
        dist = ParameterDistribution(
            name='test_normal',
            distribution='normal',
            params={'mean': 100.0, 'sd': 10.0}
        )
        rng = np.random.default_rng(42)
        samples = dist.sample(rng, n=10000)

        assert len(samples) == 10000
        assert abs(np.mean(samples) - 100.0) < 1.0  # Within 1 of mean
        assert abs(np.std(samples) - 10.0) < 1.0    # Within 1 of SD

    def test_gamma_sampling(self):
        """Test gamma distribution sampling."""
        dist = ParameterDistribution(
            name='test_gamma',
            distribution='gamma',
            params={'shape': 25.0, 'scale': 1000.0}
        )
        rng = np.random.default_rng(42)
        samples = dist.sample(rng, n=10000)

        assert len(samples) == 10000
        assert all(samples > 0)  # Gamma is positive
        # Mean of gamma(shape, scale) = shape * scale
        expected_mean = 25.0 * 1000.0
        assert abs(np.mean(samples) - expected_mean) < 1000  # Within 1000 of mean

    def test_beta_sampling(self):
        """Test beta distribution sampling (bounded 0-1)."""
        dist = ParameterDistribution(
            name='test_beta',
            distribution='beta',
            params={'alpha': 8.0, 'beta': 2.0}  # Mean = 0.8
        )
        rng = np.random.default_rng(42)
        samples = dist.sample(rng, n=10000)

        assert len(samples) == 10000
        assert all((samples >= 0) & (samples <= 1))  # Beta is bounded
        assert abs(np.mean(samples) - 0.8) < 0.05  # Mean should be ~0.8

    def test_lognormal_sampling(self):
        """Test lognormal distribution sampling."""
        # Lognormal with mu=log(1.3), sigma=0.1 should have mean close to 1.3
        dist = ParameterDistribution(
            name='test_lognormal',
            distribution='lognormal',
            params={'mu': np.log(1.3), 'sigma': 0.1}
        )
        rng = np.random.default_rng(42)
        samples = dist.sample(rng, n=10000)

        assert len(samples) == 10000
        assert all(samples > 0)  # Lognormal is positive
        # Mean of lognormal = exp(mu + sigma^2/2)
        expected_mean = np.exp(np.log(1.3) + 0.1**2 / 2)
        assert abs(np.mean(samples) - expected_mean) < 0.1


class TestCorrelationGroup:
    """Tests for CorrelationGroup class."""

    def test_cholesky_decomposition(self):
        """Test that Cholesky decomposition is computed correctly."""
        corr_matrix = np.array([
            [1.0, 0.7],
            [0.7, 1.0]
        ])
        group = CorrelationGroup(
            name='test_group',
            parameters=['param1', 'param2'],
            correlation_matrix=corr_matrix
        )

        # L @ L^T should equal original matrix
        reconstructed = group.cholesky_L @ group.cholesky_L.T
        np.testing.assert_array_almost_equal(reconstructed, corr_matrix)

    def test_invalid_correlation_matrix_shape(self):
        """Test that invalid matrix shape raises error."""
        corr_matrix = np.array([
            [1.0, 0.7, 0.5],
            [0.7, 1.0, 0.5],
            [0.5, 0.5, 1.0]
        ])

        with pytest.raises(ValueError):
            CorrelationGroup(
                name='test_group',
                parameters=['param1', 'param2'],  # 2 params but 3x3 matrix
                correlation_matrix=corr_matrix
            )


class TestCholeskySampler:
    """Tests for CholeskySampler class."""

    def test_correlated_sampling_preserves_correlation(self):
        """Test that Cholesky sampling preserves target correlations."""
        # Define two correlated parameters
        distributions = {
            'cost_a': ParameterDistribution(
                name='cost_a',
                distribution='gamma',
                params={'shape': 25.0, 'scale': 1000.0},
                correlation_group='costs'
            ),
            'cost_b': ParameterDistribution(
                name='cost_b',
                distribution='gamma',
                params={'shape': 15.0, 'scale': 1000.0},
                correlation_group='costs'
            ),
        }

        target_correlation = 0.7
        correlation_groups = {
            'costs': CorrelationGroup(
                name='costs',
                parameters=['cost_a', 'cost_b'],
                correlation_matrix=np.array([
                    [1.0, target_correlation],
                    [target_correlation, 1.0]
                ])
            )
        }

        sampler = CholeskySampler(distributions, correlation_groups, seed=42)
        samples = sampler.sample(n_samples=10000)

        # Check correlation is approximately correct
        actual_correlation = np.corrcoef(samples['cost_a'], samples['cost_b'])[0, 1]
        assert abs(actual_correlation - target_correlation) < 0.05

    def test_independent_parameters_uncorrelated(self):
        """Test that parameters not in correlation groups remain independent."""
        distributions = {
            'param_a': ParameterDistribution(
                name='param_a',
                distribution='normal',
                params={'mean': 100, 'sd': 10}
            ),
            'param_b': ParameterDistribution(
                name='param_b',
                distribution='normal',
                params={'mean': 50, 'sd': 5}
            ),
        }

        sampler = CholeskySampler(distributions, {}, seed=42)
        samples = sampler.sample(n_samples=10000)

        # Should be uncorrelated (close to 0)
        correlation = np.corrcoef(samples['param_a'], samples['param_b'])[0, 1]
        assert abs(correlation) < 0.05


class TestPSAIteration:
    """Tests for PSAIteration class."""

    def test_icer_calculation(self):
        """Test ICER is calculated correctly."""
        iteration = PSAIteration(
            iteration=0,
            parameters={},
            ixa_costs=100000,
            ixa_qalys=10.0,
            ixa_life_years=12.0,
            comparator_costs=80000,
            comparator_qalys=9.5,
            comparator_life_years=11.5
        )

        assert iteration.delta_costs == 20000
        assert iteration.delta_qalys == 0.5
        assert iteration.icer == 40000  # 20000 / 0.5

    def test_icer_none_when_negative_qalys(self):
        """Test ICER is None when QALY difference is zero or negative."""
        iteration = PSAIteration(
            iteration=0,
            parameters={},
            ixa_costs=100000,
            ixa_qalys=9.0,  # Lower than comparator
            ixa_life_years=12.0,
            comparator_costs=80000,
            comparator_qalys=9.5,
            comparator_life_years=11.5
        )

        assert iteration.delta_qalys == -0.5
        assert iteration.icer is None


class TestPSAResults:
    """Tests for PSAResults class."""

    @pytest.fixture
    def sample_results(self):
        """Create sample PSA results for testing."""
        iterations = []
        for i in range(100):
            iterations.append(PSAIteration(
                iteration=i,
                parameters={'param1': np.random.normal(100, 10)},
                ixa_costs=80000 + np.random.normal(0, 5000),
                ixa_qalys=9.5 + np.random.normal(0, 0.2),
                ixa_life_years=11.5,
                comparator_costs=60000 + np.random.normal(0, 3000),
                comparator_qalys=9.0 + np.random.normal(0, 0.2),
                comparator_life_years=11.0
            ))

        return PSAResults(
            iterations=iterations,
            n_patients_per_iteration=500
        )

    def test_probability_cost_effective(self, sample_results):
        """Test probability cost-effective calculation."""
        prob_50k = sample_results.probability_cost_effective(50000)
        prob_200k = sample_results.probability_cost_effective(200000)

        # Higher WTP should give higher probability CE
        assert 0 <= prob_50k <= 1
        assert 0 <= prob_200k <= 1
        assert prob_200k >= prob_50k

    def test_ceac_generation(self, sample_results):
        """Test CEAC data generation."""
        ceac = sample_results.generate_ceac(wtp_range=np.array([0, 50000, 100000]))

        assert len(ceac) == 3
        assert 'wtp' in ceac.columns
        assert 'probability_ce' in ceac.columns
        assert all(ceac['probability_ce'] >= 0)
        assert all(ceac['probability_ce'] <= 1)

    def test_evpi_calculation(self, sample_results):
        """Test EVPI calculation."""
        evpi = sample_results.calculate_evpi(100000)

        # EVPI should be non-negative
        assert evpi >= 0

    def test_summary_statistics(self, sample_results):
        """Test summary statistics generation."""
        summary = sample_results.get_summary_statistics()

        assert 'n_iterations' in summary
        assert summary['n_iterations'] == 100
        assert 'delta_costs_mean' in summary
        assert 'delta_qalys_mean' in summary
        assert 'prop_ce_100k' in summary


class TestDefaultDistributions:
    """Tests for default parameter distributions."""

    def test_default_distributions_complete(self):
        """Test that default distributions include all expected parameters."""
        distributions = get_default_parameter_distributions()

        # Check key parameters exist
        expected_params = [
            'ixa_sbp_mean',
            'spiro_sbp_mean',
            'cost_mi_acute',
            'utility_post_mi',
            'rr_stroke_per_10mmhg'
        ]

        for param in expected_params:
            assert param in distributions, f"Missing parameter: {param}"

    def test_default_correlation_groups_valid(self):
        """Test that default correlation groups have valid matrices."""
        groups = get_default_correlation_groups()

        for name, group in groups.items():
            # All correlation matrices should have 1s on diagonal
            np.testing.assert_array_equal(
                np.diag(group.correlation_matrix),
                np.ones(len(group.parameters))
            )

            # Should be symmetric
            np.testing.assert_array_almost_equal(
                group.correlation_matrix,
                group.correlation_matrix.T
            )


class TestPSARunner:
    """Integration tests for PSARunner."""

    def test_minimal_psa_run(self):
        """Test that PSA runs without errors (minimal configuration)."""
        config = SimulationConfig(
            n_patients=10,
            time_horizon_months=12,  # 1 year only
            seed=42,
            show_progress=False
        )

        runner = PSARunner(config, seed=42)

        # Run with very few iterations for speed
        results = runner.run(
            n_iterations=2,
            use_common_random_numbers=True,
            show_progress=False
        )

        assert results.n_iterations == 2
        assert len(results.iterations) == 2
        assert all(it.ixa_costs > 0 for it in results.iterations)
        assert all(it.comparator_costs > 0 for it in results.iterations)


class TestConvenienceFunction:
    """Tests for the run_psa convenience function."""

    def test_run_psa_basic(self):
        """Test basic run_psa execution."""
        # Very minimal run for testing
        results = run_psa(
            n_patients=10,
            n_iterations=2,
            time_horizon_years=1,
            seed=42,
            show_progress=False
        )

        assert isinstance(results, PSAResults)
        assert results.n_iterations == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
