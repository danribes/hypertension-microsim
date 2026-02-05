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
from . import utilities as utilities_module


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
    # SECONDARY CAUSES OF RESISTANT HYPERTENSION
    # =========================================================================
    # Treatment response modifiers for each etiology
    # Reference: Carey RM et al. Hypertension 2018; Resistant HTN guidelines

    # Primary Aldosteronism (PA) - Enhanced response to aldosterone-targeting
    distributions['pa_ixa_response_modifier'] = ParameterDistribution(
        name='pa_ixa_response_modifier',
        distribution='lognormal',
        params={'mu': np.log(1.35), 'sigma': 0.12},  # Mean ~1.35, 95% CI: 1.1-1.7
        description='PA patient response modifier for IXA-001'
    )

    distributions['pa_spiro_response_modifier'] = ParameterDistribution(
        name='pa_spiro_response_modifier',
        distribution='lognormal',
        params={'mu': np.log(1.30), 'sigma': 0.10},  # Mean ~1.30
        description='PA patient response modifier for spironolactone'
    )

    # Pheochromocytoma - Poor response to standard therapy
    distributions['pheo_antihtn_response'] = ParameterDistribution(
        name='pheo_antihtn_response',
        distribution='beta',
        params={'alpha': 4.0, 'beta': 6.0},  # Mean ~0.40
        description='Pheo patient response to non-alpha-blocker antihypertensives'
    )

    # Renal Artery Stenosis - ESRD risk modifier
    distributions['ras_esrd_modifier'] = ParameterDistribution(
        name='ras_esrd_modifier',
        distribution='lognormal',
        params={'mu': np.log(1.80), 'sigma': 0.15},  # Mean ~1.80
        description='RAS patient ESRD progression risk modifier'
    )

    # OSA - CPAP benefit on BP control
    distributions['osa_cpap_bp_benefit'] = ParameterDistribution(
        name='osa_cpap_bp_benefit',
        distribution='normal',
        params={'mean': 5.0, 'sd': 2.5},  # Mean 5 mmHg reduction, SD 2.5
        description='Additional SBP reduction from CPAP therapy (mmHg)'
    )

    # Prevalence parameters (for scenario analysis)
    distributions['pa_prevalence'] = ParameterDistribution(
        name='pa_prevalence',
        distribution='beta',
        params={'alpha': 17.0, 'beta': 83.0},  # Mean ~17%
        description='Primary aldosteronism prevalence in resistant HTN'
    )

    distributions['ras_prevalence'] = ParameterDistribution(
        name='ras_prevalence',
        distribution='beta',
        params={'alpha': 8.0, 'beta': 92.0},  # Mean ~8%
        description='Renal artery stenosis prevalence in resistant HTN'
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

    # =========================================================================
    # DISUTILITIES (for utility parameter uncertainty)
    # =========================================================================

    distributions['disutility_post_mi'] = ParameterDistribution(
        name='disutility_post_mi',
        distribution='beta',
        params={'alpha': 88.0, 'beta': 12.0},  # Mean=0.12, as per utilities.py
        description='Disutility for post-MI state',
        correlation_group='disutilities'
    )

    distributions['disutility_post_stroke'] = ParameterDistribution(
        name='disutility_post_stroke',
        distribution='beta',
        params={'alpha': 72.0, 'beta': 28.0},  # Mean=0.18
        description='Disutility for post-stroke state',
        correlation_group='disutilities'
    )

    distributions['disutility_chronic_hf'] = ParameterDistribution(
        name='disutility_chronic_hf',
        distribution='beta',
        params={'alpha': 85.0, 'beta': 15.0},  # Mean=0.15
        description='Disutility for chronic HF state',
        correlation_group='disutilities'
    )

    distributions['disutility_esrd'] = ParameterDistribution(
        name='disutility_esrd',
        distribution='beta',
        params={'alpha': 65.0, 'beta': 35.0},  # Mean=0.35
        description='Disutility for ESRD/dialysis state',
        correlation_group='disutilities'
    )

    distributions['disutility_dementia'] = ParameterDistribution(
        name='disutility_dementia',
        distribution='beta',
        params={'alpha': 70.0, 'beta': 30.0},  # Mean=0.30
        description='Disutility for dementia state',
        correlation_group='disutilities'
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

    # Disutilities correlation (EQ-5D measurement methodology)
    groups['disutilities'] = CorrelationGroup(
        name='disutilities',
        parameters=['disutility_post_mi', 'disutility_post_stroke',
                   'disutility_chronic_hf', 'disutility_esrd', 'disutility_dementia'],
        correlation_matrix=np.array([
            [1.0,  0.6,  0.5,  0.4,  0.3],   # Post-MI
            [0.6,  1.0,  0.5,  0.5,  0.5],   # Post-Stroke
            [0.5,  0.5,  1.0,  0.4,  0.3],   # Chronic HF
            [0.4,  0.5,  0.4,  1.0,  0.4],   # ESRD
            [0.3,  0.5,  0.3,  0.4,  1.0],   # Dementia
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
    # INCREMENTAL NET BENEFIT (INB)
    # =========================================================================

    def calculate_inb(self, wtp_threshold: float = 100000) -> Dict[str, Any]:
        """
        Calculate Incremental Net Benefit statistics.

        INB = λ × ΔQ - ΔC

        Where λ is the WTP threshold, ΔQ is incremental QALYs, ΔC is incremental costs.

        Advantages of INB over ICER:
        - Linear combination, well-defined even when ΔQ ≤ 0
        - Confidence intervals are straightforward
        - Hypothesis testing: INB > 0 means cost-effective

        Reference:
            Stinnett AA, Mullahy J. Net health benefits: a new framework
            for the analysis of uncertainty in cost-effectiveness.
            Med Decis Making. 1998;18(2 Suppl):S68-80.

        Args:
            wtp_threshold: Willingness-to-pay threshold ($/QALY)

        Returns:
            Dictionary with INB statistics
        """
        inb_values = wtp_threshold * self.delta_qalys - self.delta_costs

        return {
            'wtp_threshold': wtp_threshold,
            'inb_mean': np.mean(inb_values),
            'inb_sd': np.std(inb_values),
            'inb_median': np.median(inb_values),
            'inb_95ci': (np.percentile(inb_values, 2.5),
                        np.percentile(inb_values, 97.5)),
            'prob_inb_positive': np.mean(inb_values > 0),
            'inb_values': inb_values
        }

    def generate_inb_curve(
        self,
        wtp_range: Optional[np.ndarray] = None
    ) -> pd.DataFrame:
        """
        Generate INB curve across WTP thresholds.

        Args:
            wtp_range: Array of WTP thresholds

        Returns:
            DataFrame with columns ['wtp', 'inb_mean', 'inb_lower', 'inb_upper', 'prob_positive']
        """
        if wtp_range is None:
            wtp_range = np.linspace(0, 200000, 201)

        results = []
        for wtp in wtp_range:
            inb_stats = self.calculate_inb(wtp)
            results.append({
                'wtp': wtp,
                'inb_mean': inb_stats['inb_mean'],
                'inb_lower': inb_stats['inb_95ci'][0],
                'inb_upper': inb_stats['inb_95ci'][1],
                'prob_positive': inb_stats['prob_inb_positive']
            })

        return pd.DataFrame(results)

    # =========================================================================
    # CONVERGENCE DIAGNOSTICS
    # =========================================================================

    def check_convergence(
        self,
        wtp_threshold: float = 100000,
        window_size: int = 100
    ) -> Dict[str, Any]:
        """
        Check PSA convergence using running mean and standard error.

        Convergence is assessed by examining whether the running mean and
        probability of cost-effectiveness have stabilized.

        Reference:
            O'Hagan A, et al. Uncertainty in decision models: Technical
            Support Document 15. NICE DSU. 2012.

        Args:
            wtp_threshold: WTP threshold for convergence check
            window_size: Window size for running calculations

        Returns:
            Dictionary with convergence diagnostics
        """
        if self.n_iterations < window_size * 2:
            warnings.warn(f"Fewer than {window_size * 2} iterations; "
                         "convergence diagnostics may be unreliable")

        # Calculate running statistics
        running_icer_mean = []
        running_prob_ce = []
        running_inb_mean = []

        for n in range(window_size, self.n_iterations + 1):
            subset_delta_costs = self.delta_costs[:n]
            subset_delta_qalys = self.delta_qalys[:n]

            # Running ICER (only where QALY gain > 0)
            valid_mask = subset_delta_qalys > 0.001
            if np.any(valid_mask):
                icers = subset_delta_costs[valid_mask] / subset_delta_qalys[valid_mask]
                running_icer_mean.append(np.mean(icers))
            else:
                running_icer_mean.append(np.nan)

            # Running probability of CE
            nmb = wtp_threshold * subset_delta_qalys - subset_delta_costs
            running_prob_ce.append(np.mean(nmb > 0))

            # Running INB mean
            inb = wtp_threshold * subset_delta_qalys - subset_delta_costs
            running_inb_mean.append(np.mean(inb))

        # Assess convergence: coefficient of variation in last 20% of runs
        n_check = max(int(0.2 * len(running_prob_ce)), 10)

        prob_ce_last = running_prob_ce[-n_check:]
        prob_ce_cv = np.std(prob_ce_last) / (np.mean(prob_ce_last) + 1e-10)

        inb_last = running_inb_mean[-n_check:]
        inb_cv = np.std(inb_last) / (abs(np.mean(inb_last)) + 1e-10)

        # Convergence criteria
        # CV < 1% generally indicates good convergence
        prob_ce_converged = prob_ce_cv < 0.01
        inb_converged = inb_cv < 0.01

        return {
            'n_iterations': self.n_iterations,
            'wtp_threshold': wtp_threshold,
            'window_size': window_size,
            'running_icer_mean': np.array(running_icer_mean),
            'running_prob_ce': np.array(running_prob_ce),
            'running_inb_mean': np.array(running_inb_mean),
            'prob_ce_cv': prob_ce_cv,
            'inb_cv': inb_cv,
            'prob_ce_converged': prob_ce_converged,
            'inb_converged': inb_converged,
            'overall_converged': prob_ce_converged and inb_converged,
            'recommendation': self._convergence_recommendation(prob_ce_cv, inb_cv)
        }

    def _convergence_recommendation(self, prob_ce_cv: float, inb_cv: float) -> str:
        """Generate convergence recommendation."""
        if prob_ce_cv < 0.01 and inb_cv < 0.01:
            return "PSA appears converged. Results are stable."
        elif prob_ce_cv < 0.05 and inb_cv < 0.05:
            return "PSA shows reasonable convergence. Consider more iterations for precise estimates."
        else:
            return f"PSA may not have converged (CV: prob_CE={prob_ce_cv:.3f}, INB={inb_cv:.3f}). " \
                   "Recommend increasing n_iterations."

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

        # Apply disutility parameters to the utilities module
        if 'disutility_post_mi' in parameters:
            utilities_module.DISUTILITY['post_mi'] = parameters['disutility_post_mi']
        if 'disutility_post_stroke' in parameters:
            utilities_module.DISUTILITY['post_stroke'] = parameters['disutility_post_stroke']
        if 'disutility_chronic_hf' in parameters:
            utilities_module.DISUTILITY['chronic_hf'] = parameters['disutility_chronic_hf']
        if 'disutility_esrd' in parameters:
            utilities_module.DISUTILITY['esrd'] = parameters['disutility_esrd']
        if 'disutility_dementia' in parameters:
            utilities_module.DISUTILITY['dementia'] = parameters['disutility_dementia']

        return config


# =============================================================================
# DETERMINISTIC SENSITIVITY ANALYSIS (DSA)
# =============================================================================

@dataclass
class DSAResult:
    """Results from a single DSA parameter variation."""
    parameter: str
    base_value: float
    low_value: float
    high_value: float
    icer_base: float
    icer_low: float
    icer_high: float
    inb_base: float
    inb_low: float
    inb_high: float
    icer_range: float = field(init=False)
    inb_range: float = field(init=False)

    def __post_init__(self):
        # Handle None ICERs
        low = self.icer_low if self.icer_low is not None else self.icer_base
        high = self.icer_high if self.icer_high is not None else self.icer_base
        self.icer_range = abs(high - low)
        self.inb_range = abs(self.inb_high - self.inb_low)


class DeterministicSensitivityAnalysis:
    """
    One-way Deterministic Sensitivity Analysis (DSA) for tornado diagrams.

    DSA systematically varies one parameter at a time while holding others
    at base case values to identify which parameters have the greatest
    impact on model results.

    Reference:
        Briggs A, et al. Decision Modelling for Health Economic Evaluation.
        Oxford University Press. 2006. Chapter 4.
    """

    def __init__(
        self,
        base_config: SimulationConfig,
        seed: Optional[int] = None
    ):
        """
        Initialize DSA.

        Args:
            base_config: Base simulation configuration
            seed: Random seed for reproducibility
        """
        self.base_config = base_config
        self.seed = seed
        self.distributions = get_default_parameter_distributions()

    def run(
        self,
        parameters: Optional[List[str]] = None,
        variation_pct: float = 0.20,
        wtp_threshold: float = 100000,
        show_progress: bool = True
    ) -> List[DSAResult]:
        """
        Run one-way DSA for specified parameters.

        Args:
            parameters: List of parameter names to vary (default: all)
            variation_pct: Percentage variation from base (default: ±20%)
            wtp_threshold: WTP threshold for INB calculation
            show_progress: Show progress bar

        Returns:
            List of DSAResult objects sorted by ICER range
        """
        if parameters is None:
            # Use key parameters that typically drive results
            parameters = [
                'ixa_sbp_mean', 'spiro_sbp_mean',
                'cost_mi_acute', 'cost_ischemic_stroke_acute', 'cost_hf_acute',
                'cost_esrd_annual', 'cost_ixa_monthly',
                'disutility_post_mi', 'disutility_post_stroke',
                'disutility_esrd', 'disutility_chronic_hf',
                'discontinuation_rate_ixa', 'discontinuation_rate_spiro'
            ]

        # Run base case first
        base_results = self._run_scenario({}, wtp_threshold)
        base_icer = base_results['icer']
        base_inb = base_results['inb']

        results = []
        iterator = parameters
        if show_progress:
            iterator = tqdm(parameters, desc="DSA Parameters")

        for param in iterator:
            if param not in self.distributions:
                warnings.warn(f"Parameter {param} not found in distributions, skipping")
                continue

            dist = self.distributions[param]
            base_value = self._get_base_value(dist)

            # Calculate low and high values
            low_value = base_value * (1 - variation_pct)
            high_value = base_value * (1 + variation_pct)

            # Run low scenario
            low_results = self._run_scenario({param: low_value}, wtp_threshold)

            # Run high scenario
            high_results = self._run_scenario({param: high_value}, wtp_threshold)

            results.append(DSAResult(
                parameter=param,
                base_value=base_value,
                low_value=low_value,
                high_value=high_value,
                icer_base=base_icer,
                icer_low=low_results['icer'],
                icer_high=high_results['icer'],
                inb_base=base_inb,
                inb_low=low_results['inb'],
                inb_high=high_results['inb']
            ))

        # Sort by ICER range (descending)
        results.sort(key=lambda x: x.icer_range, reverse=True)

        return results

    def _get_base_value(self, dist: ParameterDistribution) -> float:
        """Get base case (mean) value for a distribution."""
        if dist.distribution == 'normal':
            return dist.params['mean']
        elif dist.distribution == 'lognormal':
            return np.exp(dist.params['mu'] + dist.params['sigma']**2 / 2)
        elif dist.distribution == 'gamma':
            return dist.params['shape'] * dist.params['scale']
        elif dist.distribution == 'beta':
            alpha, beta = dist.params['alpha'], dist.params['beta']
            return alpha / (alpha + beta)
        elif dist.distribution == 'uniform':
            return (dist.params['low'] + dist.params['high']) / 2
        else:
            return 0.0

    def _run_scenario(
        self,
        param_overrides: Dict[str, float],
        wtp_threshold: float
    ) -> Dict[str, Any]:
        """Run a single DSA scenario."""
        from . import treatment as treatment_module
        from .costs import costs as costs_module

        # Reset to base values first
        self._reset_parameters()

        # Apply overrides
        for param, value in param_overrides.items():
            self._apply_single_parameter(param, value)

        # Run simulation
        config = deepcopy(self.base_config)
        config.seed = self.seed
        config.show_progress = False

        pop_params = PopulationParams(n_patients=config.n_patients, seed=self.seed)

        # IXA-001 arm
        generator = PopulationGenerator(pop_params)
        patients_ixa = generator.generate()
        sim_ixa = Simulation(config)
        results_ixa = sim_ixa.run(patients_ixa, Treatment.IXA_001)

        # Comparator arm
        generator = PopulationGenerator(pop_params)
        patients_comp = generator.generate()
        sim_comp = Simulation(config)
        results_comp = sim_comp.run(patients_comp, Treatment.SPIRONOLACTONE)

        # Calculate results
        delta_costs = results_ixa.mean_costs - results_comp.mean_costs
        delta_qalys = results_ixa.mean_qalys - results_comp.mean_qalys

        icer = delta_costs / delta_qalys if delta_qalys > 0.001 else None
        inb = wtp_threshold * delta_qalys - delta_costs

        return {
            'icer': icer,
            'inb': inb,
            'delta_costs': delta_costs,
            'delta_qalys': delta_qalys
        }

    def _apply_single_parameter(self, param: str, value: float):
        """Apply a single parameter value."""
        from . import treatment as treatment_module
        from .costs import costs as costs_module

        costs = costs_module.US_COSTS if self.base_config.cost_perspective == "US" else costs_module.UK_COSTS

        # Treatment effects
        if param == 'ixa_sbp_mean':
            treatment_module.TREATMENT_EFFECTS[Treatment.IXA_001].sbp_reduction = value
        elif param == 'spiro_sbp_mean':
            treatment_module.TREATMENT_EFFECTS[Treatment.SPIRONOLACTONE].sbp_reduction = value
        elif param == 'discontinuation_rate_ixa':
            treatment_module.TREATMENT_EFFECTS[Treatment.IXA_001].discontinuation_rate = value
        elif param == 'discontinuation_rate_spiro':
            treatment_module.TREATMENT_EFFECTS[Treatment.SPIRONOLACTONE].discontinuation_rate = value
        # Costs
        elif param == 'cost_mi_acute':
            costs.mi_acute = value
        elif param == 'cost_ischemic_stroke_acute':
            costs.ischemic_stroke_acute = value
        elif param == 'cost_hemorrhagic_stroke_acute':
            costs.hemorrhagic_stroke_acute = value
        elif param == 'cost_hf_acute':
            costs.hf_admission = value
        elif param == 'cost_esrd_annual':
            costs.esrd_annual = value
        elif param == 'cost_ixa_monthly':
            costs.ixa_001_monthly = value
        # Disutilities
        elif param == 'disutility_post_mi':
            utilities_module.DISUTILITY['post_mi'] = value
        elif param == 'disutility_post_stroke':
            utilities_module.DISUTILITY['post_stroke'] = value
        elif param == 'disutility_chronic_hf':
            utilities_module.DISUTILITY['chronic_hf'] = value
        elif param == 'disutility_esrd':
            utilities_module.DISUTILITY['esrd'] = value
        elif param == 'disutility_dementia':
            utilities_module.DISUTILITY['dementia'] = value

    def _reset_parameters(self):
        """Reset all parameters to base case values."""
        from . import treatment as treatment_module
        from .costs import costs as costs_module

        # Reset treatment effects to defaults
        treatment_module.TREATMENT_EFFECTS[Treatment.IXA_001].sbp_reduction = 20.0
        treatment_module.TREATMENT_EFFECTS[Treatment.IXA_001].discontinuation_rate = 0.12
        treatment_module.TREATMENT_EFFECTS[Treatment.SPIRONOLACTONE].sbp_reduction = 9.0
        treatment_module.TREATMENT_EFFECTS[Treatment.SPIRONOLACTONE].discontinuation_rate = 0.15

        # Reset costs to defaults (US perspective)
        costs = costs_module.US_COSTS
        costs.mi_acute = 25000.0
        costs.ischemic_stroke_acute = 15200.0
        costs.hemorrhagic_stroke_acute = 22500.0
        costs.hf_admission = 18000.0
        costs.esrd_annual = 90000.0
        costs.ixa_001_monthly = 500.0

        # Reset disutilities to defaults
        utilities_module.DISUTILITY['post_mi'] = 0.12
        utilities_module.DISUTILITY['post_stroke'] = 0.18
        utilities_module.DISUTILITY['chronic_hf'] = 0.15
        utilities_module.DISUTILITY['esrd'] = 0.35
        utilities_module.DISUTILITY['dementia'] = 0.30

    def to_dataframe(self, results: List[DSAResult]) -> pd.DataFrame:
        """Convert DSA results to DataFrame for tornado diagram."""
        records = []
        for r in results:
            records.append({
                'parameter': r.parameter,
                'base_value': r.base_value,
                'low_value': r.low_value,
                'high_value': r.high_value,
                'icer_base': r.icer_base,
                'icer_low': r.icer_low,
                'icer_high': r.icer_high,
                'icer_range': r.icer_range,
                'inb_base': r.inb_base,
                'inb_low': r.inb_low,
                'inb_high': r.inb_high,
                'inb_range': r.inb_range
            })
        return pd.DataFrame(records)


# =============================================================================
# SCENARIO ANALYSIS
# =============================================================================

@dataclass
class ScenarioResult:
    """Results from a scenario analysis."""
    name: str
    description: str
    parameters: Dict[str, float]
    ixa_costs: float
    ixa_qalys: float
    comparator_costs: float
    comparator_qalys: float
    delta_costs: float = field(init=False)
    delta_qalys: float = field(init=False)
    icer: Optional[float] = field(init=False)

    def __post_init__(self):
        self.delta_costs = self.ixa_costs - self.comparator_costs
        self.delta_qalys = self.ixa_qalys - self.comparator_qalys
        self.icer = self.delta_costs / self.delta_qalys if self.delta_qalys > 0.001 else None


class ScenarioAnalysis:
    """
    Scenario analysis for exploring structural uncertainty.

    Scenario analysis complements PSA by examining the impact of
    alternative structural assumptions or parameter sets.

    Common scenarios:
    - Best case / Worst case
    - Optimistic / Pessimistic treatment effects
    - Alternative cost perspectives
    - Subgroup analyses

    Reference:
        ISPOR-SMDM Modeling Good Research Practices Task Force.
        Model Transparency and Validation. Value Health. 2012;15(6):843-850.
    """

    def __init__(
        self,
        base_config: SimulationConfig,
        seed: Optional[int] = None
    ):
        self.base_config = base_config
        self.seed = seed
        self.distributions = get_default_parameter_distributions()

    def run_predefined_scenarios(
        self,
        show_progress: bool = True
    ) -> List[ScenarioResult]:
        """
        Run predefined scenario analyses.

        Returns:
            List of ScenarioResult objects
        """
        scenarios = self._get_predefined_scenarios()
        results = []

        iterator = scenarios.items()
        if show_progress:
            iterator = tqdm(list(iterator), desc="Scenarios")

        for name, scenario in iterator:
            result = self._run_single_scenario(
                name=name,
                description=scenario['description'],
                parameters=scenario['parameters']
            )
            results.append(result)

        return results

    def run_custom_scenario(
        self,
        name: str,
        description: str,
        parameters: Dict[str, float]
    ) -> ScenarioResult:
        """
        Run a custom scenario analysis.

        Args:
            name: Scenario name
            description: Scenario description
            parameters: Dictionary of parameter overrides

        Returns:
            ScenarioResult object
        """
        return self._run_single_scenario(name, description, parameters)

    def _get_predefined_scenarios(self) -> Dict[str, Dict]:
        """Define predefined scenarios."""
        return {
            'base_case': {
                'description': 'Base case analysis with mean parameter values',
                'parameters': {}
            },
            'optimistic_ixa': {
                'description': 'Optimistic IXA-001 efficacy (upper 95% CI)',
                'parameters': {
                    'ixa_sbp_mean': 24.0,  # +2 SD
                    'discontinuation_rate_ixa': 0.08
                }
            },
            'pessimistic_ixa': {
                'description': 'Pessimistic IXA-001 efficacy (lower 95% CI)',
                'parameters': {
                    'ixa_sbp_mean': 16.0,  # -2 SD
                    'discontinuation_rate_ixa': 0.18
                }
            },
            'high_event_costs': {
                'description': 'Higher acute event costs (+50%)',
                'parameters': {
                    'cost_mi_acute': 37500.0,
                    'cost_ischemic_stroke_acute': 22800.0,
                    'cost_hf_acute': 27000.0
                }
            },
            'low_event_costs': {
                'description': 'Lower acute event costs (-30%)',
                'parameters': {
                    'cost_mi_acute': 17500.0,
                    'cost_ischemic_stroke_acute': 10640.0,
                    'cost_hf_acute': 12600.0
                }
            },
            'high_ixa_cost': {
                'description': 'Higher IXA-001 drug cost ($750/month)',
                'parameters': {
                    'cost_ixa_monthly': 750.0
                }
            },
            'low_ixa_cost': {
                'description': 'Lower IXA-001 drug cost ($350/month, generic)',
                'parameters': {
                    'cost_ixa_monthly': 350.0
                }
            },
            'worse_utilities': {
                'description': 'Higher disutilities for health states (+25%)',
                'parameters': {
                    'disutility_post_mi': 0.15,
                    'disutility_post_stroke': 0.225,
                    'disutility_chronic_hf': 0.1875,
                    'disutility_esrd': 0.4375
                }
            },
            'better_utilities': {
                'description': 'Lower disutilities for health states (-25%)',
                'parameters': {
                    'disutility_post_mi': 0.09,
                    'disutility_post_stroke': 0.135,
                    'disutility_chronic_hf': 0.1125,
                    'disutility_esrd': 0.2625
                }
            }
        }

    def _run_single_scenario(
        self,
        name: str,
        description: str,
        parameters: Dict[str, float]
    ) -> ScenarioResult:
        """Run a single scenario."""
        dsa = DeterministicSensitivityAnalysis(self.base_config, self.seed)

        # Reset and apply scenario parameters
        dsa._reset_parameters()
        for param, value in parameters.items():
            dsa._apply_single_parameter(param, value)

        # Run simulation
        config = deepcopy(self.base_config)
        config.seed = self.seed
        config.show_progress = False

        pop_params = PopulationParams(n_patients=config.n_patients, seed=self.seed)

        # IXA-001 arm
        generator = PopulationGenerator(pop_params)
        patients_ixa = generator.generate()
        sim_ixa = Simulation(config)
        results_ixa = sim_ixa.run(patients_ixa, Treatment.IXA_001)

        # Comparator arm
        generator = PopulationGenerator(pop_params)
        patients_comp = generator.generate()
        sim_comp = Simulation(config)
        results_comp = sim_comp.run(patients_comp, Treatment.SPIRONOLACTONE)

        return ScenarioResult(
            name=name,
            description=description,
            parameters=parameters,
            ixa_costs=results_ixa.mean_costs,
            ixa_qalys=results_ixa.mean_qalys,
            comparator_costs=results_comp.mean_costs,
            comparator_qalys=results_comp.mean_qalys
        )

    def to_dataframe(self, results: List[ScenarioResult]) -> pd.DataFrame:
        """Convert scenario results to DataFrame."""
        records = []
        for r in results:
            records.append({
                'scenario': r.name,
                'description': r.description,
                'ixa_costs': r.ixa_costs,
                'ixa_qalys': r.ixa_qalys,
                'comparator_costs': r.comparator_costs,
                'comparator_qalys': r.comparator_qalys,
                'delta_costs': r.delta_costs,
                'delta_qalys': r.delta_qalys,
                'icer': r.icer
            })
        return pd.DataFrame(records)


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


def print_psa_summary(results: PSAResults, wtp_threshold: float = 100000):
    """Print formatted PSA summary."""
    summary = results.get_summary_statistics()
    inb_stats = results.calculate_inb(wtp_threshold)
    convergence = results.check_convergence(wtp_threshold)

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

    print(f"\nIncremental Net Benefit (at ${wtp_threshold:,.0f}/QALY):")
    print(f"  Mean: ${inb_stats['inb_mean']:,.0f}")
    print(f"  95% CI: (${inb_stats['inb_95ci'][0]:,.0f}, ${inb_stats['inb_95ci'][1]:,.0f})")
    print(f"  P(INB > 0): {inb_stats['prob_inb_positive']*100:.1f}%")

    print(f"\nProbability Cost-Effective:")
    print(f"  At $50,000/QALY:  {summary['prop_ce_50k']*100:.1f}%")
    print(f"  At $100,000/QALY: {summary['prop_ce_100k']*100:.1f}%")
    print(f"  At $150,000/QALY: {summary['prop_ce_150k']*100:.1f}%")

    print(f"\nConvergence Diagnostics:")
    print(f"  P(CE) CV: {convergence['prob_ce_cv']:.4f}")
    print(f"  INB CV: {convergence['inb_cv']:.4f}")
    print(f"  Status: {convergence['recommendation']}")

    print("="*70 + "\n")


def run_dsa(
    n_patients: int = 200,
    time_horizon_years: int = 40,
    seed: Optional[int] = 42,
    parameters: Optional[List[str]] = None,
    variation_pct: float = 0.20,
    show_progress: bool = True
) -> List[DSAResult]:
    """
    Convenience function to run Deterministic Sensitivity Analysis.

    Args:
        n_patients: Patients per scenario
        time_horizon_years: Simulation time horizon
        seed: Random seed
        parameters: Parameters to vary (default: key parameters)
        variation_pct: Percentage variation (default: ±20%)
        show_progress: Show progress bar

    Returns:
        List of DSAResult objects sorted by ICER range
    """
    config = SimulationConfig(
        n_patients=n_patients,
        time_horizon_months=time_horizon_years * 12,
        seed=seed,
        show_progress=False
    )

    dsa = DeterministicSensitivityAnalysis(config, seed=seed)
    return dsa.run(parameters=parameters, variation_pct=variation_pct, show_progress=show_progress)


def print_dsa_summary(results: List[DSAResult], top_n: int = 10):
    """Print formatted DSA summary (tornado diagram data)."""
    print("\n" + "="*70)
    print("DETERMINISTIC SENSITIVITY ANALYSIS (ONE-WAY)")
    print("="*70)

    print(f"\nTop {min(top_n, len(results))} Most Influential Parameters (by ICER range):")
    print("-"*70)
    print(f"{'Parameter':<35} {'Low ICER':>12} {'High ICER':>12} {'Range':>10}")
    print("-"*70)

    for r in results[:top_n]:
        low_str = f"${r.icer_low:,.0f}" if r.icer_low is not None else "N/A"
        high_str = f"${r.icer_high:,.0f}" if r.icer_high is not None else "N/A"
        print(f"{r.parameter:<35} {low_str:>12} {high_str:>12} ${r.icer_range:>9,.0f}")

    if results:
        print("-"*70)
        print(f"Base case ICER: ${results[0].icer_base:,.0f}" if results[0].icer_base else "Base case ICER: N/A")

    print("="*70 + "\n")


def run_scenario_analysis(
    n_patients: int = 200,
    time_horizon_years: int = 40,
    seed: Optional[int] = 42,
    show_progress: bool = True
) -> List[ScenarioResult]:
    """
    Convenience function to run scenario analysis.

    Args:
        n_patients: Patients per scenario
        time_horizon_years: Simulation time horizon
        seed: Random seed
        show_progress: Show progress bar

    Returns:
        List of ScenarioResult objects
    """
    config = SimulationConfig(
        n_patients=n_patients,
        time_horizon_months=time_horizon_years * 12,
        seed=seed,
        show_progress=False
    )

    sa = ScenarioAnalysis(config, seed=seed)
    return sa.run_predefined_scenarios(show_progress=show_progress)


def print_scenario_summary(results: List[ScenarioResult]):
    """Print formatted scenario analysis summary."""
    print("\n" + "="*80)
    print("SCENARIO ANALYSIS")
    print("="*80)

    print(f"\n{'Scenario':<25} {'Description':<35} {'ICER':>15}")
    print("-"*80)

    for r in results:
        icer_str = f"${r.icer:,.0f}" if r.icer is not None else "Dominated"
        desc = r.description[:33] + ".." if len(r.description) > 35 else r.description
        print(f"{r.name:<25} {desc:<35} {icer_str:>15}")

    print("="*80 + "\n")


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


def plot_tornado(
    dsa_results: List[DSAResult],
    top_n: int = 10,
    wtp_threshold: float = 100000
):
    """
    Plot tornado diagram from DSA results.

    Args:
        dsa_results: List of DSAResult objects
        top_n: Number of top parameters to display
        wtp_threshold: Reference line for WTP threshold

    Requires matplotlib.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required for plotting. Install with: pip install matplotlib")
        return

    # Take top N results
    results = dsa_results[:top_n]
    n = len(results)

    # Extract data (reverse order for correct tornado display)
    parameters = [r.parameter for r in results][::-1]
    base_icer = results[0].icer_base if results else 0

    # Calculate bars (relative to base)
    low_icers = []
    high_icers = []
    for r in results[::-1]:
        low = r.icer_low if r.icer_low is not None else base_icer
        high = r.icer_high if r.icer_high is not None else base_icer
        low_icers.append(low - base_icer)
        high_icers.append(high - base_icer)

    fig, ax = plt.subplots(figsize=(12, max(6, n * 0.5)))

    y_pos = np.arange(n)

    # Plot bars
    colors_low = ['#2ecc71' if v < 0 else '#e74c3c' for v in low_icers]
    colors_high = ['#e74c3c' if v > 0 else '#2ecc71' for v in high_icers]

    for i in range(n):
        ax.barh(y_pos[i], low_icers[i], align='center', color=colors_low[i], alpha=0.7, height=0.6)
        ax.barh(y_pos[i], high_icers[i], align='center', color=colors_high[i], alpha=0.7, height=0.6)

    # Reference line at base case
    ax.axvline(x=0, color='black', linestyle='-', linewidth=1.5)

    # WTP reference line (relative to base)
    if base_icer is not None:
        wtp_relative = wtp_threshold - base_icer
        ax.axvline(x=wtp_relative, color='gray', linestyle='--', linewidth=1,
                   label=f'WTP ${wtp_threshold:,.0f}')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(parameters)
    ax.set_xlabel('Change in ICER from Base Case ($)')
    ax.set_title(f'Tornado Diagram: One-Way Sensitivity Analysis\n(Base Case ICER: ${base_icer:,.0f}/QALY)')
    ax.legend(loc='best')

    plt.tight_layout()
    return fig


def plot_inb_curve(results: PSAResults):
    """
    Plot Incremental Net Benefit curve with confidence intervals.

    Args:
        results: PSA results

    Requires matplotlib.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required for plotting. Install with: pip install matplotlib")
        return

    inb_data = results.generate_inb_curve()

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot mean INB
    ax.plot(inb_data['wtp'] / 1000, inb_data['inb_mean'] / 1000,
            'b-', linewidth=2, label='Mean INB')

    # Plot confidence interval
    ax.fill_between(inb_data['wtp'] / 1000,
                    inb_data['inb_lower'] / 1000,
                    inb_data['inb_upper'] / 1000,
                    alpha=0.3, color='blue', label='95% CI')

    # Reference line at INB = 0
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1)

    # Common WTP thresholds
    for wtp in [50, 100, 150]:
        ax.axvline(x=wtp, color='lightgray', linestyle=':', linewidth=0.5)

    ax.set_xlabel('Willingness-to-Pay Threshold ($1,000/QALY)')
    ax.set_ylabel('Incremental Net Benefit ($1,000)')
    ax.set_title('Incremental Net Benefit Curve\nIXA-001 vs Spironolactone')
    ax.set_xlim(0, 200)
    ax.legend(loc='best')

    plt.tight_layout()
    return fig


def plot_convergence(results: PSAResults, wtp_threshold: float = 100000):
    """
    Plot PSA convergence diagnostics.

    Args:
        results: PSA results
        wtp_threshold: WTP threshold

    Requires matplotlib.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required for plotting. Install with: pip install matplotlib")
        return

    convergence = results.check_convergence(wtp_threshold)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    x = np.arange(100, results.n_iterations + 1)

    # Running ICER mean
    ax1 = axes[0, 0]
    valid_icer = ~np.isnan(convergence['running_icer_mean'])
    ax1.plot(x[valid_icer], convergence['running_icer_mean'][valid_icer],
             'b-', linewidth=1.5)
    ax1.axhline(y=wtp_threshold, color='r', linestyle='--', label=f'WTP ${wtp_threshold:,.0f}')
    ax1.set_xlabel('Number of Iterations')
    ax1.set_ylabel('Running Mean ICER ($)')
    ax1.set_title('Running Mean ICER')
    ax1.legend()

    # Running P(CE)
    ax2 = axes[0, 1]
    ax2.plot(x, convergence['running_prob_ce'], 'g-', linewidth=1.5)
    ax2.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Number of Iterations')
    ax2.set_ylabel('Running P(Cost-Effective)')
    ax2.set_title(f'Running Probability Cost-Effective (WTP=${wtp_threshold:,.0f})')
    ax2.set_ylim(0, 1)

    # Running INB mean
    ax3 = axes[1, 0]
    ax3.plot(x, np.array(convergence['running_inb_mean']) / 1000, 'purple', linewidth=1.5)
    ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Number of Iterations')
    ax3.set_ylabel('Running Mean INB ($1,000)')
    ax3.set_title('Running Mean Incremental Net Benefit')

    # Text summary
    ax4 = axes[1, 1]
    ax4.axis('off')
    summary_text = f"""
    Convergence Assessment
    ----------------------
    Iterations: {results.n_iterations:,}
    WTP Threshold: ${wtp_threshold:,}/QALY

    Coefficient of Variation (last 20%):
      P(CE): {convergence['prob_ce_cv']:.4f}
      INB: {convergence['inb_cv']:.4f}

    Convergence Status:
      P(CE): {'Converged' if convergence['prob_ce_converged'] else 'Not converged'}
      INB: {'Converged' if convergence['inb_converged'] else 'Not converged'}

    {convergence['recommendation']}
    """
    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
             fontsize=11, verticalalignment='top', fontfamily='monospace')

    plt.suptitle('PSA Convergence Diagnostics', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig
