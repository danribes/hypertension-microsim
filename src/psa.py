"""
Probabilistic Sensitivity Analysis (PSA) module for hypertension microsimulation.

This module implements a complete PSA workflow including:
1. Parameter distributions with appropriate distribution types
2. Cholesky decomposition for correlated parameters
3. Nested loop PSA with Common Random Numbers (CRN)
4. Output generation (CE plane, CEAC, EVPI)

Key Concepts:
- First-order uncertainty: Stochastic patient-level variation (inherent in microsimulation)
- Second-order uncertainty: Parameter uncertainty (addressed by PSA)

Author: Generated for Atlantis Pharmaceuticals IXA-001 CEA
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from copy import deepcopy
from tqdm import tqdm
import warnings

from .patient import Patient, Treatment
from .population import PopulationGenerator, PopulationParams
from .simulation import Simulation, SimulationConfig, SimulationResults
from .costs.costs import CostInputs, US_COSTS, UK_COSTS


# =============================================================================
# PARAMETER DISTRIBUTION DEFINITIONS
# =============================================================================

@dataclass
class ParameterDistribution:
    """
    Defines a single parameter's uncertainty distribution.

    Attributes:
        name: Parameter identifier
        distribution: Type of distribution ('normal', 'lognormal', 'gamma', 'beta', 'uniform')
        params: Distribution-specific parameters
        description: Human-readable description
        correlation_group: Group ID for correlated parameters (optional)
    """
    name: str
    distribution: str
    params: Dict[str, float]
    description: str = ""
    correlation_group: Optional[str] = None

    def sample(self, rng: np.random.Generator, n: int = 1) -> np.ndarray:
        """Sample from the distribution."""
        if self.distribution == 'normal':
            return rng.normal(self.params['mean'], self.params['sd'], n)
        elif self.distribution == 'lognormal':
            # Parameterized by underlying normal mean/sd
            return rng.lognormal(self.params['mu'], self.params['sigma'], n)
        elif self.distribution == 'gamma':
            return rng.gamma(self.params['shape'], self.params['scale'], n)
        elif self.distribution == 'beta':
            return rng.beta(self.params['alpha'], self.params['beta'], n)
        elif self.distribution == 'uniform':
            return rng.uniform(self.params['low'], self.params['high'], n)
        else:
            raise ValueError(f"Unknown distribution: {self.distribution}")


@dataclass
class CorrelationGroup:
    """
    Defines a group of correlated parameters.

    Attributes:
        name: Group identifier
        parameters: List of parameter names in this group
        correlation_matrix: Correlation matrix (must be positive semi-definite)
    """
    name: str
    parameters: List[str]
    correlation_matrix: np.ndarray

    def __post_init__(self):
        """Validate and compute Cholesky decomposition."""
        n = len(self.parameters)
        if self.correlation_matrix.shape != (n, n):
            raise ValueError(f"Correlation matrix must be {n}x{n}")

        # Ensure positive semi-definite
        try:
            self.cholesky_L = np.linalg.cholesky(self.correlation_matrix)
        except np.linalg.LinAlgError:
            warnings.warn(f"Correlation matrix for {self.name} is not positive definite. "
                         "Using nearest positive definite approximation.")
            self.cholesky_L = self._nearest_positive_definite()

    def _nearest_positive_definite(self) -> np.ndarray:
        """Find nearest positive definite matrix using Higham algorithm."""
        A = self.correlation_matrix
        B = (A + A.T) / 2
        _, s, V = np.linalg.svd(B)
        H = np.dot(V.T, np.dot(np.diag(s), V))
        A2 = (B + H) / 2
        A3 = (A2 + A2.T) / 2

        # Add small diagonal to ensure positive definite
        spacing = np.spacing(np.linalg.norm(A3))
        I = np.eye(A3.shape[0])
        k = 1
        while not self._is_positive_definite(A3):
            mineig = np.min(np.real(np.linalg.eigvals(A3)))
            A3 += I * (-mineig * k**2 + spacing)
            k += 1

        return np.linalg.cholesky(A3)

    @staticmethod
    def _is_positive_definite(A: np.ndarray) -> bool:
        try:
            np.linalg.cholesky(A)
            return True
        except np.linalg.LinAlgError:
            return False


# =============================================================================
# DEFAULT PARAMETER DISTRIBUTIONS
# =============================================================================

def get_default_parameter_distributions() -> Dict[str, ParameterDistribution]:
    """
    Returns default parameter distributions for PSA.

    Distribution choice rationale:
    - Normal: Treatment effects (can be negative in theory)
    - Lognormal: Risk ratios, hazard ratios (must be positive)
    - Gamma: Costs (positive, right-skewed)
    - Beta: Utilities, probabilities (bounded 0-1)
    """

    distributions = {}

    # =========================================================================
    # TREATMENT EFFECTS
    # =========================================================================

    # IXA-001 SBP reduction
    distributions['ixa_sbp_mean'] = ParameterDistribution(
        name='ixa_sbp_mean',
        distribution='normal',
        params={'mean': 20.0, 'sd': 2.0},  # SE from trial
        description='IXA-001 mean SBP reduction (mmHg)',
        correlation_group='treatment_effects'
    )

    distributions['ixa_sbp_sd'] = ParameterDistribution(
        name='ixa_sbp_sd',
        distribution='gamma',
        params={'shape': 16.0, 'scale': 0.5},  # Mean=8, reasonable SD
        description='IXA-001 SBP reduction SD (individual variation)'
    )

    # Spironolactone SBP reduction
    distributions['spiro_sbp_mean'] = ParameterDistribution(
        name='spiro_sbp_mean',
        distribution='normal',
        params={'mean': 9.0, 'sd': 1.5},
        description='Spironolactone mean SBP reduction (mmHg)',
        correlation_group='treatment_effects'
    )

    distributions['spiro_sbp_sd'] = ParameterDistribution(
        name='spiro_sbp_sd',
        distribution='gamma',
        params={'shape': 9.0, 'scale': 0.67},  # Mean=6
        description='Spironolactone SBP reduction SD'
    )

    # PA treatment response modifier
    distributions['pa_response_modifier'] = ParameterDistribution(
        name='pa_response_modifier',
        distribution='lognormal',
        params={'mu': np.log(1.30), 'sigma': 0.1},  # Mean≈1.30
        description='PA patient enhanced response to IXA-001'
    )

    # =========================================================================
    # RELATIVE RISKS (per 10 mmHg SBP reduction)
    # =========================================================================

    distributions['rr_mi_per_10mmhg'] = ParameterDistribution(
        name='rr_mi_per_10mmhg',
        distribution='lognormal',
        params={'mu': np.log(0.78), 'sigma': 0.05},
        description='RR of MI per 10 mmHg SBP reduction',
        correlation_group='risk_ratios'
    )

    distributions['rr_stroke_per_10mmhg'] = ParameterDistribution(
        name='rr_stroke_per_10mmhg',
        distribution='lognormal',
        params={'mu': np.log(0.64), 'sigma': 0.06},
        description='RR of Stroke per 10 mmHg SBP reduction',
        correlation_group='risk_ratios'
    )

    distributions['rr_hf_per_10mmhg'] = ParameterDistribution(
        name='rr_hf_per_10mmhg',
        distribution='lognormal',
        params={'mu': np.log(0.72), 'sigma': 0.05},
        description='RR of HF per 10 mmHg SBP reduction',
        correlation_group='risk_ratios'
    )

    # =========================================================================
    # ACUTE EVENT COSTS (Correlated - same cost drivers)
    # =========================================================================

    distributions['cost_mi_acute'] = ParameterDistribution(
        name='cost_mi_acute',
        distribution='gamma',
        params={'shape': 25.0, 'scale': 1000.0},  # Mean=$25,000
        description='Acute MI cost (USD)',
        correlation_group='acute_costs'
    )

    distributions['cost_ischemic_stroke_acute'] = ParameterDistribution(
        name='cost_ischemic_stroke_acute',
        distribution='gamma',
        params={'shape': 15.2, 'scale': 1000.0},  # Mean=$15,200
        description='Acute ischemic stroke cost (USD)',
        correlation_group='acute_costs'
    )

    distributions['cost_hemorrhagic_stroke_acute'] = ParameterDistribution(
        name='cost_hemorrhagic_stroke_acute',
        distribution='gamma',
        params={'shape': 22.5, 'scale': 1000.0},  # Mean=$22,500
        description='Acute hemorrhagic stroke cost (USD)',
        correlation_group='acute_costs'
    )

    distributions['cost_hf_acute'] = ParameterDistribution(
        name='cost_hf_acute',
        distribution='gamma',
        params={'shape': 18.0, 'scale': 1000.0},  # Mean=$18,000
        description='Acute HF admission cost (USD)',
        correlation_group='acute_costs'
    )

    # =========================================================================
    # ANNUAL MANAGEMENT COSTS
    # =========================================================================

    distributions['cost_esrd_annual'] = ParameterDistribution(
        name='cost_esrd_annual',
        distribution='gamma',
        params={'shape': 90.0, 'scale': 1000.0},  # Mean=$90,000
        description='Annual ESRD cost (USD)'
    )

    distributions['cost_post_stroke_annual'] = ParameterDistribution(
        name='cost_post_stroke_annual',
        distribution='gamma',
        params={'shape': 12.0, 'scale': 1000.0},  # Mean=$12,000
        description='Annual post-stroke management cost (USD)'
    )

    distributions['cost_hf_annual'] = ParameterDistribution(
        name='cost_hf_annual',
        distribution='gamma',
        params={'shape': 15.0, 'scale': 1000.0},  # Mean=$15,000
        description='Annual HF management cost (USD)'
    )

    # Drug costs
    distributions['cost_ixa_monthly'] = ParameterDistribution(
        name='cost_ixa_monthly',
        distribution='gamma',
        params={'shape': 50.0, 'scale': 10.0},  # Mean=$500
        description='IXA-001 monthly cost (USD)'
    )

    # =========================================================================
    # UTILITIES (Correlated - same measurement approach)
    # =========================================================================

    distributions['utility_post_mi'] = ParameterDistribution(
        name='utility_post_mi',
        distribution='beta',
        params={'alpha': 70.4, 'beta': 9.6},  # Mean=0.88, concentrated
        description='Utility after MI',
        correlation_group='utilities'
    )

    distributions['utility_post_stroke'] = ParameterDistribution(
        name='utility_post_stroke',
        distribution='beta',
        params={'alpha': 65.6, 'beta': 14.4},  # Mean=0.82
        description='Utility after stroke',
        correlation_group='utilities'
    )

    distributions['utility_chronic_hf'] = ParameterDistribution(
        name='utility_chronic_hf',
        distribution='beta',
        params={'alpha': 68.0, 'beta': 12.0},  # Mean=0.85
        description='Utility with chronic HF',
        correlation_group='utilities'
    )

    distributions['utility_esrd'] = ParameterDistribution(
        name='utility_esrd',
        distribution='beta',
        params={'alpha': 52.0, 'beta': 28.0},  # Mean=0.65
        description='Utility on dialysis (ESRD)',
        correlation_group='utilities'
    )

    # =========================================================================
    # PHENOTYPE RISK MODIFIERS
    # =========================================================================

    distributions['gcua_ii_esrd_modifier'] = ParameterDistribution(
        name='gcua_ii_esrd_modifier',
        distribution='lognormal',
        params={'mu': np.log(1.4), 'sigma': 0.15},
        description='GCUA Type II (Silent Renal) ESRD risk modifier'
    )

    distributions['eocri_b_esrd_modifier'] = ParameterDistribution(
        name='eocri_b_esrd_modifier',
        distribution='lognormal',
        params={'mu': np.log(2.0), 'sigma': 0.2},
        description='EOCRI Type B (Silent Renal) ESRD risk modifier'
    )

    # =========================================================================
    # DISCONTINUATION & ADHERENCE
    # =========================================================================

    distributions['discontinuation_rate_ixa'] = ParameterDistribution(
        name='discontinuation_rate_ixa',
        distribution='beta',
        params={'alpha': 12.0, 'beta': 88.0},  # Mean=0.12
        description='Annual discontinuation rate IXA-001'
    )

    distributions['discontinuation_rate_spiro'] = ParameterDistribution(
        name='discontinuation_rate_spiro',
        distribution='beta',
        params={'alpha': 15.0, 'beta': 85.0},  # Mean=0.15
        description='Annual discontinuation rate spironolactone'
    )

    distributions['adherence_effect'] = ParameterDistribution(
        name='adherence_effect',
        distribution='beta',
        params={'alpha': 3.0, 'beta': 7.0},  # Mean=0.30
        description='Treatment effect retained when non-adherent'
    )

    return distributions


def get_default_correlation_groups() -> Dict[str, CorrelationGroup]:
    """
    Returns default correlation groups for PSA.

    Rationale for correlations:
    - Acute costs: Hospital cost inflation affects all acute events similarly
    - Utilities: Measurement methodology introduces systematic bias
    - Risk ratios: Common evidence base from BP trials
    """

    groups = {}

    # Acute costs correlation (hospital cost drivers)
    groups['acute_costs'] = CorrelationGroup(
        name='acute_costs',
        parameters=['cost_mi_acute', 'cost_ischemic_stroke_acute',
                   'cost_hemorrhagic_stroke_acute', 'cost_hf_acute'],
        correlation_matrix=np.array([
            [1.0,  0.7,  0.7,  0.6],   # MI
            [0.7,  1.0,  0.8,  0.5],   # Ischemic Stroke
            [0.7,  0.8,  1.0,  0.5],   # Hemorrhagic Stroke
            [0.6,  0.5,  0.5,  1.0],   # HF
        ])
    )

    # Utilities correlation (EQ-5D measurement approach)
    groups['utilities'] = CorrelationGroup(
        name='utilities',
        parameters=['utility_post_mi', 'utility_post_stroke',
                   'utility_chronic_hf', 'utility_esrd'],
        correlation_matrix=np.array([
            [1.0,  0.6,  0.5,  0.4],   # Post-MI
            [0.6,  1.0,  0.5,  0.5],   # Post-Stroke
            [0.5,  0.5,  1.0,  0.4],   # Chronic HF
            [0.4,  0.5,  0.4,  1.0],   # ESRD
        ])
    )

    # Risk ratios correlation (shared evidence from meta-analyses)
    groups['risk_ratios'] = CorrelationGroup(
        name='risk_ratios',
        parameters=['rr_mi_per_10mmhg', 'rr_stroke_per_10mmhg', 'rr_hf_per_10mmhg'],
        correlation_matrix=np.array([
            [1.0,  0.5,  0.4],   # MI
            [0.5,  1.0,  0.4],   # Stroke
            [0.4,  0.4,  1.0],   # HF
        ])
    )

    return groups


# =============================================================================
# CHOLESKY SAMPLER
# =============================================================================

class CholeskySampler:
    """
    Samples correlated parameters using Cholesky decomposition.

    Process:
    1. Generate independent standard normal samples
    2. Transform using Cholesky factor: X = L @ Z
    3. Transform marginals to target distributions using inverse CDF
    """

    def __init__(
        self,
        distributions: Dict[str, ParameterDistribution],
        correlation_groups: Dict[str, CorrelationGroup],
        seed: Optional[int] = None
    ):
        self.distributions = distributions
        self.correlation_groups = correlation_groups
        self.rng = np.random.default_rng(seed)

        # Build mapping of parameters to their groups
        self._param_to_group: Dict[str, str] = {}
        for group_name, group in correlation_groups.items():
            for param in group.parameters:
                self._param_to_group[param] = group_name

    def sample(self, n_samples: int = 1) -> Dict[str, np.ndarray]:
        """
        Sample all parameters, respecting correlations.

        Args:
            n_samples: Number of parameter sets to sample

        Returns:
            Dictionary mapping parameter names to arrays of sampled values
        """
        samples = {}

        # Sample correlated groups using Cholesky
        for group_name, group in self.correlation_groups.items():
            group_samples = self._sample_correlated_group(group, n_samples)
            samples.update(group_samples)

        # Sample independent parameters
        for param_name, dist in self.distributions.items():
            if param_name not in samples:  # Not in any correlation group
                samples[param_name] = dist.sample(self.rng, n_samples)

        return samples

    def _sample_correlated_group(
        self,
        group: CorrelationGroup,
        n_samples: int
    ) -> Dict[str, np.ndarray]:
        """
        Sample a group of correlated parameters using Cholesky decomposition.

        Steps:
        1. Generate independent standard normals Z ~ N(0, I)
        2. Transform to correlated normals: X = L @ Z where Σ = L @ L^T
        3. Transform each marginal to its target distribution
        """
        n_params = len(group.parameters)

        # Step 1: Generate independent standard normals
        Z = self.rng.standard_normal((n_samples, n_params))

        # Step 2: Transform to correlated normals using Cholesky
        # X = Z @ L^T gives correlated normals with correlation matrix Σ
        X = Z @ group.cholesky_L.T

        # Step 3: Transform each marginal to target distribution
        # Using probability integral transform: F^{-1}(Φ(x))
        samples = {}
        from scipy import stats

        for i, param_name in enumerate(group.parameters):
            if param_name not in self.distributions:
                warnings.warn(f"Parameter {param_name} in correlation group but no distribution defined")
                continue

            dist = self.distributions[param_name]

            # Convert correlated normal to uniform via standard normal CDF
            u = stats.norm.cdf(X[:, i])

            # Transform uniform to target distribution via inverse CDF
            samples[param_name] = self._inverse_cdf(dist, u)

        return samples

    def _inverse_cdf(self, dist: ParameterDistribution, u: np.ndarray) -> np.ndarray:
        """Apply inverse CDF transformation."""
        from scipy import stats

        if dist.distribution == 'normal':
            return stats.norm.ppf(u, loc=dist.params['mean'], scale=dist.params['sd'])
        elif dist.distribution == 'lognormal':
            return stats.lognorm.ppf(u, s=dist.params['sigma'],
                                     scale=np.exp(dist.params['mu']))
        elif dist.distribution == 'gamma':
            return stats.gamma.ppf(u, a=dist.params['shape'],
                                   scale=dist.params['scale'])
        elif dist.distribution == 'beta':
            return stats.beta.ppf(u, a=dist.params['alpha'],
                                  b=dist.params['beta'])
        elif dist.distribution == 'uniform':
            return stats.uniform.ppf(u, loc=dist.params['low'],
                                     scale=dist.params['high'] - dist.params['low'])
        else:
            raise ValueError(f"Unknown distribution: {dist.distribution}")


# =============================================================================
# PSA RESULTS
# =============================================================================

@dataclass
class PSAIteration:
    """Results from a single PSA iteration."""
    iteration: int
    parameters: Dict[str, float]

    # Intervention arm
    ixa_costs: float
    ixa_qalys: float
    ixa_life_years: float

    # Comparator arm
    comparator_costs: float
    comparator_qalys: float
    comparator_life_years: float

    # Incremental
    delta_costs: float = field(init=False)
    delta_qalys: float = field(init=False)
    delta_life_years: float = field(init=False)
    icer: Optional[float] = field(init=False)

    def __post_init__(self):
        self.delta_costs = self.ixa_costs - self.comparator_costs
        self.delta_qalys = self.ixa_qalys - self.comparator_qalys
        self.delta_life_years = self.ixa_life_years - self.comparator_life_years

        if self.delta_qalys > 0.001:  # Avoid division by near-zero
            self.icer = self.delta_costs / self.delta_qalys
        else:
            self.icer = None


@dataclass
class PSAResults:
    """
    Complete PSA results with analysis methods.
    """
    iterations: List[PSAIteration]
    n_patients_per_iteration: int
    intervention_name: str = "IXA-001"
    comparator_name: str = "Spironolactone"

    def __post_init__(self):
        """Compute summary statistics."""
        self._compute_summaries()

    def _compute_summaries(self):
        """Compute summary statistics across iterations."""
        self.delta_costs = np.array([it.delta_costs for it in self.iterations])
        self.delta_qalys = np.array([it.delta_qalys for it in self.iterations])

        # Valid ICERs (where QALY gain > 0)
        valid_icers = [it.icer for it in self.iterations if it.icer is not None]
        self.valid_icers = np.array(valid_icers) if valid_icers else np.array([])

    @property
    def n_iterations(self) -> int:
        return len(self.iterations)

    # =========================================================================
    # SUMMARY STATISTICS
    # =========================================================================

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Return summary statistics for PSA."""
        return {
            'n_iterations': self.n_iterations,
            'n_patients_per_iteration': self.n_patients_per_iteration,

            # Incremental costs
            'delta_costs_mean': np.mean(self.delta_costs),
            'delta_costs_sd': np.std(self.delta_costs),
            'delta_costs_95ci': (np.percentile(self.delta_costs, 2.5),
                                 np.percentile(self.delta_costs, 97.5)),

            # Incremental QALYs
            'delta_qalys_mean': np.mean(self.delta_qalys),
            'delta_qalys_sd': np.std(self.delta_qalys),
            'delta_qalys_95ci': (np.percentile(self.delta_qalys, 2.5),
                                 np.percentile(self.delta_qalys, 97.5)),

            # ICER
            'icer_mean': np.mean(self.valid_icers) if len(self.valid_icers) > 0 else None,
            'icer_median': np.median(self.valid_icers) if len(self.valid_icers) > 0 else None,
            'icer_95ci': (np.percentile(self.valid_icers, 2.5),
                         np.percentile(self.valid_icers, 97.5)) if len(self.valid_icers) > 0 else (None, None),

            # Proportion with positive QALY gain
            'prop_qaly_gain': np.mean(self.delta_qalys > 0),

            # Proportion cost-effective at various thresholds
            'prop_ce_50k': self.probability_cost_effective(50000),
            'prop_ce_100k': self.probability_cost_effective(100000),
            'prop_ce_150k': self.probability_cost_effective(150000),
        }

    # =========================================================================
    # COST-EFFECTIVENESS ACCEPTABILITY
    # =========================================================================

    def probability_cost_effective(self, wtp_threshold: float) -> float:
        """
        Calculate probability of being cost-effective at given WTP threshold.

        P(CE) = P(ICER < λ) = P(ΔC - λ × ΔQ < 0)

        This formulation avoids issues with ICER when ΔQALY crosses zero.
        """
        nmb = wtp_threshold * self.delta_qalys - self.delta_costs
        return np.mean(nmb > 0)

    def generate_ceac(
        self,
        wtp_range: Optional[np.ndarray] = None
    ) -> pd.DataFrame:
        """
        Generate Cost-Effectiveness Acceptability Curve data.

        Args:
            wtp_range: Array of WTP thresholds (default: $0 to $200,000)

        Returns:
            DataFrame with columns ['wtp', 'probability_ce']
        """
        if wtp_range is None:
            wtp_range = np.linspace(0, 200000, 201)

        probs = [self.probability_cost_effective(wtp) for wtp in wtp_range]

        return pd.DataFrame({
            'wtp': wtp_range,
            'probability_ce': probs
        })

    # =========================================================================
    # EXPECTED VALUE OF PERFECT INFORMATION (EVPI)
    # =========================================================================

    def calculate_evpi(self, wtp_threshold: float, population_size: float = 1.0) -> float:
        """
        Calculate Expected Value of Perfect Information.

        EVPI = E[max(NMB_intervention, NMB_comparator)] - max(E[NMB_intervention], E[NMB_comparator])

        Args:
            wtp_threshold: Willingness-to-pay threshold ($/QALY)
            population_size: Effective population for value calculation

        Returns:
            EVPI in dollars
        """
        # Net Monetary Benefit for each iteration
        # NMB_intervention = λ * Q_int - C_int
        # NMB_comparator = λ * Q_comp - C_comp

        nmb_intervention = np.array([
            wtp_threshold * it.ixa_qalys - it.ixa_costs
            for it in self.iterations
        ])

        nmb_comparator = np.array([
            wtp_threshold * it.comparator_qalys - it.comparator_costs
            for it in self.iterations
        ])

        # Expected value with perfect information (choose best for each iteration)
        ev_perfect = np.mean(np.maximum(nmb_intervention, nmb_comparator))

        # Expected value with current information (choose based on expected NMB)
        if np.mean(nmb_intervention) > np.mean(nmb_comparator):
            ev_current = np.mean(nmb_intervention)
        else:
            ev_current = np.mean(nmb_comparator)

        # EVPI per patient
        evpi_per_patient = ev_perfect - ev_current

        return evpi_per_patient * population_size

    def generate_evpi_curve(
        self,
        wtp_range: Optional[np.ndarray] = None,
        population_size: float = 1.0
    ) -> pd.DataFrame:
        """Generate EVPI across WTP thresholds."""
        if wtp_range is None:
            wtp_range = np.linspace(0, 200000, 201)

        evpi_values = [self.calculate_evpi(wtp, population_size) for wtp in wtp_range]

        return pd.DataFrame({
            'wtp': wtp_range,
            'evpi': evpi_values
        })

    # =========================================================================
    # COST-EFFECTIVENESS PLANE DATA
    # =========================================================================

    def get_ce_plane_data(self) -> pd.DataFrame:
        """Return data for cost-effectiveness plane scatter plot."""
        return pd.DataFrame({
            'delta_costs': self.delta_costs,
            'delta_qalys': self.delta_qalys,
            'icer': [it.icer for it in self.iterations]
        })

    # =========================================================================
    # PARAMETER IMPORTANCE (SIMPLIFIED EVPPI APPROXIMATION)
    # =========================================================================

    def parameter_importance(self, wtp_threshold: float = 100000) -> pd.DataFrame:
        """
        Estimate parameter importance using correlation with NMB.

        This is a simplified approximation - full EVPPI requires regression methods.

        Returns:
            DataFrame with parameters ranked by |correlation with NMB|
        """
        # Calculate NMB for each iteration
        nmb = wtp_threshold * self.delta_qalys - self.delta_costs

        # Extract parameter values
        param_names = list(self.iterations[0].parameters.keys())

        correlations = {}
        for param in param_names:
            values = np.array([it.parameters[param] for it in self.iterations])
            corr = np.corrcoef(values, nmb)[0, 1]
            correlations[param] = corr

        df = pd.DataFrame({
            'parameter': list(correlations.keys()),
            'correlation_with_nmb': list(correlations.values()),
            'abs_correlation': [abs(c) for c in correlations.values()]
        }).sort_values('abs_correlation', ascending=False)

        return df

    # =========================================================================
    # EXPORT
    # =========================================================================

    def to_dataframe(self) -> pd.DataFrame:
        """Export all iteration results to DataFrame."""
        records = []
        for it in self.iterations:
            record = {
                'iteration': it.iteration,
                'ixa_costs': it.ixa_costs,
                'ixa_qalys': it.ixa_qalys,
                'comparator_costs': it.comparator_costs,
                'comparator_qalys': it.comparator_qalys,
                'delta_costs': it.delta_costs,
                'delta_qalys': it.delta_qalys,
                'icer': it.icer,
                **{f'param_{k}': v for k, v in it.parameters.items()}
            }
            records.append(record)

        return pd.DataFrame(records)


# =============================================================================
# PSA RUNNER
# =============================================================================

class PSARunner:
    """
    Orchestrates the complete PSA workflow.

    Implements nested-loop PSA with:
    - Outer loop: Sample parameters from distributions (K iterations)
    - Inner loop: Simulate patients with sampled parameters (N patients per arm)
    - Common Random Numbers: Same patient seeds for both treatment arms
    """

    def __init__(
        self,
        base_config: SimulationConfig,
        distributions: Optional[Dict[str, ParameterDistribution]] = None,
        correlation_groups: Optional[Dict[str, CorrelationGroup]] = None,
        seed: Optional[int] = None
    ):
        """
        Initialize PSA runner.

        Args:
            base_config: Base simulation configuration
            distributions: Parameter distributions (default: get_default_parameter_distributions())
            correlation_groups: Correlation groups (default: get_default_correlation_groups())
            seed: Random seed for reproducibility
        """
        self.base_config = base_config
        self.distributions = distributions or get_default_parameter_distributions()
        self.correlation_groups = correlation_groups or get_default_correlation_groups()
        self.seed = seed

        # Initialize sampler
        self.sampler = CholeskySampler(
            self.distributions,
            self.correlation_groups,
            seed=seed
        )

    def run(
        self,
        n_iterations: int = 1000,
        use_common_random_numbers: bool = True,
        show_progress: bool = True,
        parallel: bool = False
    ) -> PSAResults:
        """
        Run the complete PSA.

        Args:
            n_iterations: Number of parameter samples (outer loop)
            use_common_random_numbers: Use same patient seeds for both arms
            show_progress: Show progress bar
            parallel: Use parallel processing (not implemented yet)

        Returns:
            PSAResults object with all iteration data
        """
        # Sample all parameter sets upfront
        parameter_samples = self.sampler.sample(n_iterations)

        iterations = []

        iterator = range(n_iterations)
        if show_progress:
            iterator = tqdm(iterator, desc="PSA Iterations")

        for k in iterator:
            # Extract parameters for this iteration
            params_k = {name: values[k] for name, values in parameter_samples.items()}

            # Run simulation with these parameters
            result = self._run_single_iteration(
                iteration=k,
                parameters=params_k,
                use_crn=use_common_random_numbers
            )

            iterations.append(result)

        return PSAResults(
            iterations=iterations,
            n_patients_per_iteration=self.base_config.n_patients,
            intervention_name="IXA-001",
            comparator_name="Spironolactone"
        )

    def _run_single_iteration(
        self,
        iteration: int,
        parameters: Dict[str, float],
        use_crn: bool = True
    ) -> PSAIteration:
        """
        Run a single PSA iteration with sampled parameters.

        Args:
            iteration: Iteration number
            parameters: Sampled parameter values
            use_crn: Use common random numbers

        Returns:
            PSAIteration with results
        """
        # Create modified configuration with sampled parameters
        config = self._apply_parameters(parameters)

        # Determine seeds for CRN
        if use_crn:
            base_seed = (self.seed or 0) + iteration * 1000000
            population_seed = base_seed
            sim_seed_ixa = base_seed + 1
            sim_seed_comp = base_seed + 1  # Same seed for CRN
        else:
            population_seed = None
            sim_seed_ixa = None
            sim_seed_comp = None

        # Generate population (same for both arms when using CRN)
        pop_params = PopulationParams(
            n_patients=config.n_patients,
            seed=population_seed
        )

        # IXA-001 arm
        generator_ixa = PopulationGenerator(pop_params)
        patients_ixa = generator_ixa.generate()

        config_ixa = deepcopy(config)
        config_ixa.seed = sim_seed_ixa
        config_ixa.show_progress = False

        sim_ixa = Simulation(config_ixa)
        results_ixa = sim_ixa.run(patients_ixa, Treatment.IXA_001)

        # Comparator arm (regenerate population with same seed for identical patients)
        generator_comp = PopulationGenerator(pop_params)
        patients_comp = generator_comp.generate()

        config_comp = deepcopy(config)
        config_comp.seed = sim_seed_comp
        config_comp.show_progress = False

        sim_comp = Simulation(config_comp)
        results_comp = sim_comp.run(patients_comp, Treatment.SPIRONOLACTONE)

        return PSAIteration(
            iteration=iteration,
            parameters=parameters,
            ixa_costs=results_ixa.mean_costs,
            ixa_qalys=results_ixa.mean_qalys,
            ixa_life_years=results_ixa.mean_life_years,
            comparator_costs=results_comp.mean_costs,
            comparator_qalys=results_comp.mean_qalys,
            comparator_life_years=results_comp.mean_life_years
        )

    def _apply_parameters(self, parameters: Dict[str, float]) -> SimulationConfig:
        """
        Apply sampled parameters to create modified simulation configuration.

        Note: This modifies global module-level variables for treatment effects and costs.
        A more elegant approach would use dependency injection, but this works for now.
        """
        from . import treatment as treatment_module
        from .costs import costs as costs_module

        config = deepcopy(self.base_config)

        # Apply treatment effect parameters
        if 'ixa_sbp_mean' in parameters:
            treatment_module.TREATMENT_EFFECTS[Treatment.IXA_001].sbp_reduction = parameters['ixa_sbp_mean']
        if 'ixa_sbp_sd' in parameters:
            treatment_module.TREATMENT_EFFECTS[Treatment.IXA_001].sbp_reduction_sd = parameters['ixa_sbp_sd']
        if 'spiro_sbp_mean' in parameters:
            treatment_module.TREATMENT_EFFECTS[Treatment.SPIRONOLACTONE].sbp_reduction = parameters['spiro_sbp_mean']
        if 'spiro_sbp_sd' in parameters:
            treatment_module.TREATMENT_EFFECTS[Treatment.SPIRONOLACTONE].sbp_reduction_sd = parameters['spiro_sbp_sd']

        # Apply discontinuation rates
        if 'discontinuation_rate_ixa' in parameters:
            treatment_module.TREATMENT_EFFECTS[Treatment.IXA_001].discontinuation_rate = parameters['discontinuation_rate_ixa']
        if 'discontinuation_rate_spiro' in parameters:
            treatment_module.TREATMENT_EFFECTS[Treatment.SPIRONOLACTONE].discontinuation_rate = parameters['discontinuation_rate_spiro']

        # Apply cost parameters (to current cost perspective)
        costs = costs_module.US_COSTS if config.cost_perspective == "US" else costs_module.UK_COSTS

        if 'cost_mi_acute' in parameters:
            costs.mi_acute = parameters['cost_mi_acute']
        if 'cost_ischemic_stroke_acute' in parameters:
            costs.ischemic_stroke_acute = parameters['cost_ischemic_stroke_acute']
        if 'cost_hemorrhagic_stroke_acute' in parameters:
            costs.hemorrhagic_stroke_acute = parameters['cost_hemorrhagic_stroke_acute']
        if 'cost_hf_acute' in parameters:
            costs.hf_admission = parameters['cost_hf_acute']
        if 'cost_esrd_annual' in parameters:
            costs.esrd_annual = parameters['cost_esrd_annual']
        if 'cost_post_stroke_annual' in parameters:
            costs.post_stroke_annual = parameters['cost_post_stroke_annual']
        if 'cost_hf_annual' in parameters:
            costs.heart_failure_annual = parameters['cost_hf_annual']
        if 'cost_ixa_monthly' in parameters:
            costs.ixa_001_monthly = parameters['cost_ixa_monthly']

        # Note: Utility parameters would need similar treatment
        # but require modifying the utilities module

        return config


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_psa(
    n_patients: int = 500,
    n_iterations: int = 1000,
    time_horizon_years: int = 40,
    seed: Optional[int] = 42,
    perspective: str = "US",
    show_progress: bool = True
) -> PSAResults:
    """
    Convenience function to run PSA with default settings.

    Args:
        n_patients: Patients per iteration (inner loop)
        n_iterations: Parameter samples (outer loop)
        time_horizon_years: Simulation time horizon
        seed: Random seed for reproducibility
        perspective: Cost perspective ("US" or "UK")
        show_progress: Show progress bar

    Returns:
        PSAResults object
    """
    config = SimulationConfig(
        n_patients=n_patients,
        time_horizon_months=time_horizon_years * 12,
        seed=seed,
        cost_perspective=perspective,
        show_progress=False
    )

    runner = PSARunner(config, seed=seed)

    return runner.run(
        n_iterations=n_iterations,
        use_common_random_numbers=True,
        show_progress=show_progress
    )


def print_psa_summary(results: PSAResults):
    """Print formatted PSA summary."""
    summary = results.get_summary_statistics()

    print("\n" + "="*70)
    print("PROBABILISTIC SENSITIVITY ANALYSIS RESULTS")
    print("="*70)

    print(f"\nConfiguration:")
    print(f"  Iterations (parameter samples): {summary['n_iterations']:,}")
    print(f"  Patients per iteration: {summary['n_patients_per_iteration']:,}")

    print(f"\nIncremental Costs (IXA-001 vs Spironolactone):")
    print(f"  Mean: ${summary['delta_costs_mean']:,.0f}")
    print(f"  SD: ${summary['delta_costs_sd']:,.0f}")
    print(f"  95% CI: (${summary['delta_costs_95ci'][0]:,.0f}, ${summary['delta_costs_95ci'][1]:,.0f})")

    print(f"\nIncremental QALYs:")
    print(f"  Mean: {summary['delta_qalys_mean']:.4f}")
    print(f"  SD: {summary['delta_qalys_sd']:.4f}")
    print(f"  95% CI: ({summary['delta_qalys_95ci'][0]:.4f}, {summary['delta_qalys_95ci'][1]:.4f})")
    print(f"  Proportion with QALY gain: {summary['prop_qaly_gain']*100:.1f}%")

    print(f"\nICER ($/QALY):")
    if summary['icer_mean'] is not None:
        print(f"  Mean: ${summary['icer_mean']:,.0f}")
        print(f"  Median: ${summary['icer_median']:,.0f}")
        print(f"  95% CI: (${summary['icer_95ci'][0]:,.0f}, ${summary['icer_95ci'][1]:,.0f})")
    else:
        print("  Not calculable (insufficient QALY gains)")

    print(f"\nProbability Cost-Effective:")
    print(f"  At $50,000/QALY:  {summary['prop_ce_50k']*100:.1f}%")
    print(f"  At $100,000/QALY: {summary['prop_ce_100k']*100:.1f}%")
    print(f"  At $150,000/QALY: {summary['prop_ce_150k']*100:.1f}%")

    print("="*70 + "\n")


# =============================================================================
# VISUALIZATION (Optional - requires matplotlib)
# =============================================================================

def plot_ce_plane(results: PSAResults, wtp_threshold: float = 100000):
    """
    Plot cost-effectiveness plane.

    Requires matplotlib.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required for plotting. Install with: pip install matplotlib")
        return

    data = results.get_ce_plane_data()

    fig, ax = plt.subplots(figsize=(10, 8))

    # Scatter plot
    ax.scatter(data['delta_qalys'], data['delta_costs'],
               alpha=0.3, s=10, color='blue')

    # WTP threshold line
    qaly_range = np.array([data['delta_qalys'].min(), data['delta_qalys'].max()])
    ax.plot(qaly_range, wtp_threshold * qaly_range,
            'r--', label=f'WTP = ${wtp_threshold:,.0f}/QALY')

    # Reference lines
    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    ax.axvline(x=0, color='gray', linestyle='-', linewidth=0.5)

    # Labels
    ax.set_xlabel('Incremental QALYs')
    ax.set_ylabel('Incremental Costs ($)')
    ax.set_title('Cost-Effectiveness Plane\nIXA-001 vs Spironolactone')
    ax.legend()

    # Quadrant labels
    ax.text(0.02, 0.98, 'NW\nMore costly,\nless effective',
            transform=ax.transAxes, ha='left', va='top', fontsize=8, color='gray')
    ax.text(0.98, 0.98, 'NE\nMore costly,\nmore effective',
            transform=ax.transAxes, ha='right', va='top', fontsize=8, color='gray')
    ax.text(0.02, 0.02, 'SW\nLess costly,\nless effective',
            transform=ax.transAxes, ha='left', va='bottom', fontsize=8, color='gray')
    ax.text(0.98, 0.02, 'SE\nDominant\n(Less costly, more effective)',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=8, color='gray')

    plt.tight_layout()
    return fig


def plot_ceac(results: PSAResults):
    """
    Plot Cost-Effectiveness Acceptability Curve.

    Requires matplotlib.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required for plotting. Install with: pip install matplotlib")
        return

    ceac_data = results.generate_ceac()

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(ceac_data['wtp'] / 1000, ceac_data['probability_ce'],
            'b-', linewidth=2)

    # Reference lines
    ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=0.5)
    ax.axvline(x=50, color='gray', linestyle=':', linewidth=0.5, label='$50K')
    ax.axvline(x=100, color='gray', linestyle=':', linewidth=0.5, label='$100K')
    ax.axvline(x=150, color='gray', linestyle=':', linewidth=0.5, label='$150K')

    ax.set_xlabel('Willingness-to-Pay Threshold ($1,000/QALY)')
    ax.set_ylabel('Probability Cost-Effective')
    ax.set_title('Cost-Effectiveness Acceptability Curve\nIXA-001 vs Spironolactone')
    ax.set_ylim(0, 1)
    ax.set_xlim(0, 200)

    plt.tight_layout()
    return fig


def plot_evpi(results: PSAResults, population_size: float = 11000):
    """
    Plot Expected Value of Perfect Information curve.

    Args:
        results: PSA results
        population_size: Effective population for value calculation

    Requires matplotlib.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required for plotting. Install with: pip install matplotlib")
        return

    evpi_data = results.generate_evpi_curve(population_size=population_size)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(evpi_data['wtp'] / 1000, evpi_data['evpi'] / 1e6,
            'g-', linewidth=2)

    ax.set_xlabel('Willingness-to-Pay Threshold ($1,000/QALY)')
    ax.set_ylabel('EVPI ($ millions)')
    ax.set_title(f'Expected Value of Perfect Information\n(Population = {population_size:,})')
    ax.set_xlim(0, 200)

    plt.tight_layout()
    return fig
