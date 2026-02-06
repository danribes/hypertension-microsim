# PSA Parameters Technical Report
## IXA-001 Hypertension Microsimulation Model

**Document Version:** 1.0
**Date:** February 2026
**CHEERS 2022 Compliance:** Items 20, 21 (Uncertainty Characterization)

---

## Executive Summary

This report provides a comprehensive compendium of all parameters subject to probabilistic sensitivity analysis (PSA) in the IXA-001 hypertension microsimulation model. The model incorporates **47 uncertain parameters** across 8 categories, with correlated sampling using Cholesky decomposition for structurally related parameters.

### Key Features
- **Dual uncertainty framework**: First-order (patient heterogeneity) and second-order (parameter uncertainty)
- **Common Random Numbers (CRN)**: Variance reduction for treatment comparisons
- **Correlated sampling**: 4 correlation groups with empirical correlation matrices
- **Convergence**: 1,000 iterations recommended (Monte Carlo SE < 2% of mean)

---

## 1. Distribution Selection Rationale

### 1.1 Distribution Type by Parameter Nature

| Parameter Type | Distribution | Rationale |
|----------------|--------------|-----------|
| Treatment effects (mmHg) | **Normal** | Symmetric, unbounded; based on trial estimates |
| Relative risks / Hazard ratios | **Lognormal** | Positive-valued, multiplicative; log-linear in Cox models |
| Costs ($) | **Gamma** | Positive-valued, right-skewed; standard for cost data |
| Utilities (0-1) | **Beta** | Bounded [0,1]; natural for proportions |
| Probabilities | **Beta** | Bounded [0,1]; conjugate prior for binomial |
| Multipliers / Modifiers | **Lognormal** | Positive-valued, multiplicative effects |
| Bounded multipliers | **Uniform** | When only range is known, no distributional assumption |

### 1.2 Parameter Derivation Methods

**Method of Moments** (Gamma, Beta):
```
Gamma:  shape = mean² / variance
        scale = variance / mean

Beta:   alpha = mean × ((mean × (1-mean) / variance) - 1)
        beta = (1-mean) × ((mean × (1-mean) / variance) - 1)
```

**Lognormal from CI**:
```
mu = log(median)
sigma = (log(upper_95) - log(lower_95)) / (2 × 1.96)
```

---

## 2. Complete Parameter Inventory

### 2.1 Treatment Effects (Blood Pressure Reduction)

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `ixa_sbp_reduction` | Normal | μ=20.0, σ=2.0 | 20.0 mmHg | [16.1, 23.9] | Phase III trial |
| `ixa_dbp_reduction` | Normal | μ=12.0, σ=1.5 | 12.0 mmHg | [9.1, 14.9] | Phase III trial |
| `spiro_sbp_reduction` | Normal | μ=9.0, σ=1.5 | 9.0 mmHg | [6.1, 11.9] | PATHWAY-2 |
| `spiro_dbp_reduction` | Normal | μ=5.0, σ=1.0 | 5.0 mmHg | [3.0, 7.0] | PATHWAY-2 |
| `background_sbp_reduction` | Normal | μ=15.0, σ=2.0 | 15.0 mmHg | [11.1, 18.9] | Standard care meta-analysis |

**Code Reference:** `src/psa.py:45-89`

### 2.2 Phenotype Response Modifiers

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `pa_ixa_response_modifier` | Lognormal | μ=0.262, σ=0.10 | 1.30 | [1.07, 1.58] | Aldosterone pathway affinity |
| `pa_spiro_response_modifier` | Lognormal | μ=0.336, σ=0.12 | 1.40 | [1.10, 1.78] | MR antagonist in PA |
| `ras_response_modifier` | Lognormal | μ=0.095, σ=0.08 | 1.10 | [0.94, 1.29] | RAS etiology response |
| `pheo_response_modifier` | Lognormal | μ=0.0, σ=0.15 | 1.00 | [0.74, 1.34] | Catecholamine excess |
| `osa_response_modifier` | Lognormal | μ=0.095, σ=0.10 | 1.10 | [0.90, 1.34] | OSA comorbidity |
| `eocri_modifier` | Lognormal | μ=0.182, σ=0.08 | 1.20 | [1.02, 1.41] | Age <60 phenotype |
| `gcua_modifier` | Lognormal | μ=-0.105, σ=0.08 | 0.90 | [0.77, 1.05] | Age ≥60 phenotype |

**Code Reference:** `src/psa.py:92-145`

### 2.3 Risk Ratios (per 10 mmHg SBP Reduction)

| Parameter | Distribution | Parameters | Median | 95% CI | Source |
|-----------|--------------|------------|--------|--------|--------|
| `rr_mi_per_10mmhg` | Lognormal | μ=-0.248, σ=0.05 | 0.78 | [0.70, 0.86] | Ettehad 2016 meta-analysis |
| `rr_stroke_per_10mmhg` | Lognormal | μ=-0.446, σ=0.06 | 0.64 | [0.57, 0.72] | Ettehad 2016 meta-analysis |
| `rr_hf_per_10mmhg` | Lognormal | μ=-0.329, σ=0.05 | 0.72 | [0.65, 0.80] | Ettehad 2016 meta-analysis |
| `rr_esrd_per_10mmhg` | Lognormal | μ=-0.223, σ=0.08 | 0.80 | [0.68, 0.94] | Xie 2016 CKD analysis |
| `rr_cvd_death_per_10mmhg` | Lognormal | μ=-0.288, σ=0.06 | 0.75 | [0.67, 0.84] | Ettehad 2016 meta-analysis |
| `rr_af_per_10mmhg` | Lognormal | μ=-0.198, σ=0.07 | 0.82 | [0.72, 0.94] | Okin 2015 LIFE sub-study |

**Code Reference:** `src/psa.py:148-198`

### 2.4 Baseline Risk Modifiers (Primary Aldosteronism)

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `pa_mi_risk_modifier` | Lognormal | μ=0.336, σ=0.12 | 1.40 | [1.10, 1.78] | Monticone 2018 |
| `pa_stroke_risk_modifier` | Lognormal | μ=0.405, σ=0.15 | 1.50 | [1.12, 2.01] | Monticone 2018 |
| `pa_hf_risk_modifier` | Lognormal | μ=0.718, σ=0.12 | 2.05 | [1.62, 2.60] | Monticone 2018 |
| `pa_esrd_risk_modifier` | Lognormal | μ=0.588, σ=0.15 | 1.80 | [1.34, 2.42] | Renal fibrosis data |
| `pa_af_risk_modifier` | Lognormal | μ=2.485, σ=0.20 | 12.0 | [8.1, 17.8] | Monticone 2018 |
| `pa_death_risk_modifier` | Lognormal | μ=0.470, σ=0.12 | 1.60 | [1.26, 2.03] | All-cause mortality |

**Code Reference:** `src/psa.py:201-255`

### 2.5 Acute Event Costs (US$, 2024)

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `cost_mi_acute` | Gamma | shape=25.0, scale=1000 | $25,000 | [$15,600, $37,200] | HCUP 2022 |
| `cost_ischemic_stroke_acute` | Gamma | shape=15.2, scale=1000 | $15,200 | [$9,500, $22,600] | HCUP 2022 |
| `cost_hemorrhagic_stroke_acute` | Gamma | shape=22.0, scale=1000 | $22,000 | [$13,700, $32,800] | HCUP 2022 |
| `cost_hf_acute` | Gamma | shape=18.0, scale=1000 | $18,000 | [$11,200, $26,800] | HCUP 2022 |
| `cost_af_acute` | Gamma | shape=8.5, scale=1000 | $8,500 | [$5,300, $12,700] | HCUP 2022 |
| `cost_esrd_initiation` | Gamma | shape=35.0, scale=1000 | $35,000 | [$21,800, $52,100] | USRDS 2023 |
| `cost_hyperkalemia_event` | Gamma | shape=12.0, scale=1000 | $12,000 | [$7,500, $17,900] | HCUP 2022 |

**Code Reference:** `src/psa.py:258-312`

### 2.6 Chronic Management Costs (US$/year, 2024)

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `cost_post_mi_annual` | Gamma | shape=16.0, scale=500 | $8,000 | [$4,990, $11,900] | Medicare claims |
| `cost_post_stroke_annual` | Gamma | shape=24.0, scale=500 | $12,000 | [$7,490, $17,900] | Medicare claims |
| `cost_chf_annual` | Gamma | shape=30.0, scale=500 | $15,000 | [$9,360, $22,300] | Medicare claims |
| `cost_esrd_annual` | Gamma | shape=90.0, scale=1000 | $90,000 | [$56,200, $134,100] | USRDS 2023 |
| `cost_af_chronic_annual` | Gamma | shape=8.5, scale=1000 | $8,500 | [$5,300, $12,700] | Medicare claims |
| `cost_ckd_stage3_annual` | Gamma | shape=4.5, scale=1000 | $4,500 | [$2,810, $6,710] | Medicare claims |
| `cost_ckd_stage4_annual` | Gamma | shape=8.0, scale=1000 | $8,000 | [$4,990, $11,900] | Medicare claims |
| `cost_monitoring_annual` | Gamma | shape=1.2, scale=1000 | $1,200 | [$750, $1,790] | Fee schedule |

**Code Reference:** `src/psa.py:315-378`

### 2.7 Drug Costs (US$/month, 2024)

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `cost_ixa001_monthly` | Gamma | shape=250.0, scale=2.0 | $500 | [$437, $567] | Assumed launch price |
| `cost_spiro_monthly` | Gamma | shape=15.0, scale=1.0 | $15 | [$8.4, $23.2] | NADAC 2024 |
| `cost_background_therapy_monthly` | Gamma | shape=75.0, scale=1.0 | $75 | [$59, $93] | NADAC 2024 |

**Code Reference:** `src/psa.py:381-405`

### 2.8 Utility Values

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `utility_baseline_age40` | Beta | α=87.0, β=13.0 | 0.87 | [0.80, 0.93] | Sullivan 2011 |
| `utility_baseline_age60` | Beta | α=81.0, β=19.0 | 0.81 | [0.73, 0.88] | Sullivan 2011 |
| `utility_baseline_age80` | Beta | α=72.0, β=28.0 | 0.72 | [0.63, 0.80] | Sullivan 2011 |
| `utility_post_mi` | Beta | α=70.4, β=9.6 | 0.88 | [0.81, 0.94] | NICE DSU TSD 12 |
| `utility_post_stroke` | Beta | α=65.6, β=14.4 | 0.82 | [0.74, 0.89] | NICE DSU TSD 12 |
| `utility_chf` | Beta | α=68.0, β=12.0 | 0.85 | [0.77, 0.91] | NICE DSU TSD 12 |
| `utility_esrd` | Beta | α=52.0, β=28.0 | 0.65 | [0.55, 0.74] | Gorodetskaya 2005 |
| `utility_af` | Beta | α=72.0, β=8.0 | 0.90 | [0.84, 0.95] | NICE AF guidelines |

**Code Reference:** `src/psa.py:408-468`

### 2.9 Disutility Decrements

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `disutility_mi_acute` | Beta | α=9.0, β=51.0 | 0.15 | [0.08, 0.24] | Acute phase |
| `disutility_mi_chronic` | Beta | α=7.2, β=52.8 | 0.12 | [0.05, 0.20] | Sullivan 2011 |
| `disutility_stroke_acute` | Beta | α=18.0, β=42.0 | 0.30 | [0.20, 0.41] | Acute phase |
| `disutility_stroke_chronic` | Beta | α=10.8, β=49.2 | 0.18 | [0.10, 0.28] | Sullivan 2011 |
| `disutility_hf_chronic` | Beta | α=9.0, β=51.0 | 0.15 | [0.08, 0.24] | Sullivan 2011 |
| `disutility_esrd` | Beta | α=21.0, β=39.0 | 0.35 | [0.24, 0.47] | Gorodetskaya 2005 |
| `disutility_hyperkalemia` | Beta | α=3.0, β=57.0 | 0.05 | [0.01, 0.11] | Acute event |
| `disutility_af` | Beta | α=6.0, β=54.0 | 0.10 | [0.04, 0.18] | NICE AF guidelines |

**Code Reference:** `src/psa.py:471-528`

### 2.10 Discontinuation and Adherence

| Parameter | Distribution | Parameters | Mean | 95% CI | Source |
|-----------|--------------|------------|------|--------|--------|
| `discontinuation_ixa_annual` | Beta | α=5.0, β=95.0 | 0.05 | [0.02, 0.10] | Phase III safety |
| `discontinuation_spiro_annual` | Beta | α=15.0, β=85.0 | 0.15 | [0.09, 0.23] | PATHWAY-2 |
| `adherence_modifier_ixa` | Beta | α=85.0, β=15.0 | 0.85 | [0.77, 0.91] | Assumed |
| `adherence_modifier_spiro` | Beta | α=75.0, β=25.0 | 0.75 | [0.65, 0.84] | Literature |
| `hyperkalemia_rate_spiro` | Beta | α=8.0, β=92.0 | 0.08 | [0.04, 0.14] | PATHWAY-2 |
| `hyperkalemia_rate_ixa` | Beta | α=2.0, β=98.0 | 0.02 | [0.00, 0.05] | Phase III |

**Code Reference:** `src/psa.py:531-582`

---

## 3. Correlation Structure

### 3.1 Correlation Groups

The model implements correlated sampling for parameters with structural relationships. Four correlation groups are defined:

#### Group 1: Acute Event Costs
Parameters that share common healthcare system cost drivers.

```
Correlation Matrix (acute_costs):
                MI      Stroke    HF       AF       ESRD
MI             1.00     0.60     0.55     0.40     0.30
Stroke         0.60     1.00     0.50     0.45     0.35
HF             0.55     0.50     1.00     0.50     0.45
AF             0.40     0.45     0.50     1.00     0.35
ESRD           0.30     0.35     0.45     0.35     1.00
```

#### Group 2: Chronic State Utilities
Parameters reflecting quality of life in chronic disease states.

```
Correlation Matrix (utilities):
                PostMI   PostStroke  CHF      ESRD     AF
PostMI          1.00     0.70        0.65     0.50     0.55
PostStroke      0.70     1.00        0.60     0.55     0.50
CHF             0.65     0.60        1.00     0.60     0.65
ESRD            0.50     0.55        0.60     1.00     0.45
AF              0.55     0.50        0.65     0.45     1.00
```

#### Group 3: Cardiovascular Risk Ratios
Parameters derived from common BP-lowering trial meta-analyses.

```
Correlation Matrix (risk_ratios):
                MI       Stroke    HF       Death    AF
MI              1.00     0.75      0.70     0.80     0.50
Stroke          0.75     1.00      0.65     0.75     0.55
HF              0.70     0.65      1.00     0.70     0.60
Death           0.80     0.75      0.70     1.00     0.55
AF              0.50     0.55      0.60     0.55     1.00
```

#### Group 4: Disutility Decrements
Parameters with common measurement methodology (EQ-5D).

```
Correlation Matrix (disutilities):
                MI       Stroke    HF       ESRD     AF
MI              1.00     0.65      0.60     0.45     0.50
Stroke          0.65     1.00      0.55     0.50     0.45
HF              0.60     0.55      1.00     0.55     0.60
ESRD            0.45     0.50      0.55     1.00     0.40
AF              0.50     0.45      0.60     0.40     1.00
```

**Code Reference:** `src/psa.py:585-648`

### 3.2 Cholesky Decomposition Implementation

Correlated samples are generated using Cholesky decomposition:

```python
class CholeskySampler:
    """Generate correlated samples using Cholesky decomposition."""

    def __init__(self, correlation_matrix: np.ndarray):
        # Decompose: Σ = L × L^T
        self.L = np.linalg.cholesky(correlation_matrix)
        self.n_params = correlation_matrix.shape[0]

    def sample(self, n_iterations: int) -> np.ndarray:
        # Generate independent standard normal samples
        Z = np.random.standard_normal((n_iterations, self.n_params))

        # Transform to correlated samples: X = Z × L^T
        correlated_standard = Z @ self.L.T

        return correlated_standard

    def transform_to_marginals(
        self,
        correlated_standard: np.ndarray,
        distributions: List[Distribution]
    ) -> np.ndarray:
        """Transform standard normal to target marginal distributions."""
        n_iter, n_params = correlated_standard.shape
        samples = np.zeros_like(correlated_standard)

        for j, dist in enumerate(distributions):
            # Convert standard normal to uniform via Φ(z)
            uniform = scipy.stats.norm.cdf(correlated_standard[:, j])
            # Convert uniform to target distribution via inverse CDF
            samples[:, j] = dist.ppf(uniform)

        return samples
```

**Code Reference:** `src/psa.py:651-698`

---

## 4. PSA Execution Framework

### 4.1 PSA Iteration Structure

```python
@dataclass
class PSAIteration:
    """Single PSA iteration with all sampled parameters."""
    iteration: int

    # Treatment effects
    ixa_sbp_reduction: float
    spiro_sbp_reduction: float

    # Risk ratios
    rr_mi: float
    rr_stroke: float
    rr_hf: float
    rr_esrd: float
    rr_death: float
    rr_af: float

    # Phenotype modifiers
    pa_response_modifier: float
    eocri_modifier: float
    gcua_modifier: float

    # Costs (acute and chronic)
    costs: Dict[str, float]

    # Utilities and disutilities
    utilities: Dict[str, float]
    disutilities: Dict[str, float]

    # Adherence parameters
    discontinuation_rates: Dict[str, float]
    adherence_modifiers: Dict[str, float]
```

**Code Reference:** `src/psa.py:701-745`

### 4.2 Sampling Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PSA Sampling Workflow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Initialize Samplers                                         │
│     ├── Independent parameter samplers                          │
│     └── Cholesky samplers for each correlation group            │
│                                                                 │
│  2. For iteration i = 1 to N:                                   │
│     ├── Sample independent parameters                           │
│     │   └── Normal, Lognormal, Gamma, Beta as appropriate       │
│     │                                                           │
│     ├── Sample correlated groups                                │
│     │   ├── Generate Z ~ N(0, I)                                │
│     │   ├── Transform: X = Z × L^T                              │
│     │   └── Convert to marginals via inverse CDF                │
│     │                                                           │
│     ├── Create PSAIteration object                              │
│     │                                                           │
│     └── Run simulation with sampled parameters                  │
│         ├── IXA-001 arm (with CRN seed)                         │
│         └── Comparator arm (same CRN seed)                      │
│                                                                 │
│  3. Aggregate Results                                           │
│     ├── Incremental costs per iteration                         │
│     ├── Incremental QALYs per iteration                         │
│     └── ICER distribution                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Common Random Numbers (CRN)

CRN ensures that patient-level stochastic variation is identical across treatment arms within each PSA iteration:

```python
def run_psa_iteration(iteration: int, params: PSAIteration) -> Tuple[float, float]:
    """Run single PSA iteration with CRN."""

    # Set seed based on iteration for reproducibility
    base_seed = iteration * 1000

    # Run IXA-001 arm
    np.random.seed(base_seed)
    ixa_results = run_simulation(treatment='ixa001', params=params)

    # Run comparator with SAME seed (CRN)
    np.random.seed(base_seed)
    comparator_results = run_simulation(treatment='spironolactone', params=params)

    # Calculate incremental outcomes
    delta_cost = ixa_results.total_cost - comparator_results.total_cost
    delta_qaly = ixa_results.total_qaly - comparator_results.total_qaly

    return delta_cost, delta_qaly
```

**Code Reference:** `src/simulation.py:445-489`

---

## 5. Convergence Analysis

### 5.1 Recommended Iteration Count

| Outcome | Monte Carlo SE Target | Required Iterations |
|---------|----------------------|---------------------|
| Mean ICER | <5% of mean | 500 |
| 95% CI for ICER | <10% width | 1,000 |
| CEAC (WTP=$100K) | <2% probability | 1,000 |
| Subgroup ICERs | <10% of mean | 2,000 |

**Recommendation:** 1,000 iterations for base case; 2,000 for subgroup analyses.

### 5.2 Convergence Diagnostics

```python
def check_convergence(results: List[Tuple[float, float]]) -> Dict:
    """Calculate convergence metrics for PSA results."""

    n = len(results)
    costs = np.array([r[0] for r in results])
    qalys = np.array([r[1] for r in results])

    # Cumulative means
    cum_cost_mean = np.cumsum(costs) / np.arange(1, n+1)
    cum_qaly_mean = np.cumsum(qalys) / np.arange(1, n+1)

    # Monte Carlo Standard Error
    mc_se_cost = np.std(costs) / np.sqrt(n)
    mc_se_qaly = np.std(qalys) / np.sqrt(n)

    # Coefficient of variation of running mean (last 100 vs previous 100)
    if n >= 200:
        cv_cost = np.std(cum_cost_mean[-100:]) / np.mean(cum_cost_mean[-100:])
        cv_qaly = np.std(cum_qaly_mean[-100:]) / np.mean(cum_qaly_mean[-100:])
    else:
        cv_cost = cv_qaly = np.nan

    return {
        'n_iterations': n,
        'mc_se_cost': mc_se_cost,
        'mc_se_qaly': mc_se_qaly,
        'cv_running_mean_cost': cv_cost,
        'cv_running_mean_qaly': cv_qaly,
        'converged': cv_cost < 0.02 and cv_qaly < 0.02 if n >= 200 else False
    }
```

### 5.3 Example Convergence Plot

```
Cumulative Mean ICER by Iteration
─────────────────────────────────────────────────
$300K │
      │ ╭─╮
$250K │╯  ╰──╮
      │      ╰───╮
$200K │          ╰────────────────────────────── ← Stabilized
      │
$150K │
      │
$100K │
      ├─────────┬─────────┬─────────┬──────────
      0       250       500       750      1000
                    Iteration
```

---

## 6. Parameter Sensitivity Rankings

### 6.1 Tornado Diagram (Top 10 Parameters by ICER Impact)

Based on one-way sensitivity analysis (±1 SD):

| Rank | Parameter | ICER Range | |ΔBase| |
|------|-----------|------------|---------|
| 1 | `ixa_sbp_reduction` | $180K - $350K | $85K |
| 2 | `rr_hf_per_10mmhg` | $195K - $310K | $57K |
| 3 | `pa_hf_risk_modifier` | $200K - $295K | $47K |
| 4 | `cost_esrd_annual` | $210K - $285K | $37K |
| 5 | `rr_stroke_per_10mmhg` | $215K - $280K | $32K |
| 6 | `disutility_hf_chronic` | $220K - $275K | $27K |
| 7 | `cost_ixa001_monthly` | $225K - $270K | $22K |
| 8 | `pa_response_modifier` | $228K - $268K | $20K |
| 9 | `utility_esrd` | $230K - $265K | $17K |
| 10 | `rr_esrd_per_10mmhg` | $232K - $262K | $15K |

### 6.2 Parameter Groups by Influence

| Group | Cumulative ICER Variance Explained |
|-------|-----------------------------------|
| Treatment Effects | 42% |
| Risk Ratios | 28% |
| PA Risk Modifiers | 15% |
| Costs | 10% |
| Utilities | 5% |

---

## 7. Quality Assurance

### 7.1 Distribution Verification Tests

```python
# From tests/test_psa.py

def test_gamma_moments():
    """Verify Gamma distributions match specified means."""
    cost_mi = sample_gamma(shape=25.0, scale=1000, n=10000)
    assert np.abs(np.mean(cost_mi) - 25000) < 500  # Within $500

def test_beta_bounds():
    """Verify Beta samples are in [0,1]."""
    utility = sample_beta(alpha=70.4, beta=9.6, n=10000)
    assert np.all(utility >= 0) and np.all(utility <= 1)

def test_lognormal_positivity():
    """Verify Lognormal samples are positive."""
    rr = sample_lognormal(mu=-0.248, sigma=0.05, n=10000)
    assert np.all(rr > 0)

def test_correlation_preservation():
    """Verify Cholesky sampling preserves target correlations."""
    target_corr = np.array([[1.0, 0.6], [0.6, 1.0]])
    sampler = CholeskySampler(target_corr)
    samples = sampler.sample(10000)
    empirical_corr = np.corrcoef(samples.T)
    assert np.allclose(empirical_corr, target_corr, atol=0.05)
```

**Test Results:** All 12 PSA distribution tests passing (see `tests/test_psa.py`)

### 7.2 Seed Reproducibility

```python
def test_psa_reproducibility():
    """Verify PSA results are reproducible with same seed."""
    results_1 = run_psa(n_iterations=100, seed=42)
    results_2 = run_psa(n_iterations=100, seed=42)

    assert np.allclose(results_1.mean_icer, results_2.mean_icer)
    assert np.allclose(results_1.ce_plane, results_2.ce_plane)
```

---

## 8. PSA Output Specifications

### 8.1 Standard Outputs

| Output | Format | Description |
|--------|--------|-------------|
| CE Scatter Plot | PNG/SVG | Incremental cost vs QALY, N points |
| CEAC | PNG/SVG | P(cost-effective) vs WTP threshold |
| CEAF | PNG/SVG | Optimal strategy frontier |
| Iteration Results | CSV | Per-iteration costs, QALYs, ICER |
| Summary Statistics | JSON | Mean, median, 95% CI for all outcomes |

### 8.2 Excel Workbook Structure

| Sheet | Contents |
|-------|----------|
| Summary | Mean ICER, 95% CI, probability cost-effective |
| Iterations | Raw data: iteration, Δcost, ΔQALY, ICER |
| Parameters | All sampled parameters by iteration |
| CE Plane | Embedded scatter plot |
| CEAC | Embedded acceptability curve |
| Tornado | Top 15 parameters ranked by impact |

---

## Appendix A: Parameter Quick Reference Card

```
┌────────────────────────────────────────────────────────────────────────┐
│                     PSA PARAMETER QUICK REFERENCE                      │
├────────────────────────────────────────────────────────────────────────┤
│ TREATMENT EFFECTS (Normal)                                             │
│   IXA SBP:    μ=20, σ=2 mmHg     Spiro SBP: μ=9, σ=1.5 mmHg           │
├────────────────────────────────────────────────────────────────────────┤
│ RISK RATIOS per 10mmHg (Lognormal, median)                             │
│   MI: 0.78    Stroke: 0.64    HF: 0.72    Death: 0.75    AF: 0.82     │
├────────────────────────────────────────────────────────────────────────┤
│ PA RISK MODIFIERS (Lognormal, mean)                                    │
│   MI: 1.40    Stroke: 1.50    HF: 2.05    ESRD: 1.80    AF: 12.0      │
├────────────────────────────────────────────────────────────────────────┤
│ KEY COSTS (Gamma, US$ 2024)                                            │
│   MI acute: $25K       HF acute: $18K       ESRD/yr: $90K             │
│   IXA/mo: $500        Spiro/mo: $15                                    │
├────────────────────────────────────────────────────────────────────────┤
│ UTILITIES (Beta, mean)                                                 │
│   Baseline@60: 0.81   PostMI: 0.88   PostStroke: 0.82   ESRD: 0.65    │
├────────────────────────────────────────────────────────────────────────┤
│ CORRELATION GROUPS: acute_costs, utilities, risk_ratios, disutilities │
│ RECOMMENDED ITERATIONS: 1,000 (base), 2,000 (subgroups)               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Distribution Formulas

### Probability Density Functions

**Normal:**
$$f(x) = \frac{1}{\sigma\sqrt{2\pi}} \exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right)$$

**Lognormal:**
$$f(x) = \frac{1}{x\sigma\sqrt{2\pi}} \exp\left(-\frac{(\ln x - \mu)^2}{2\sigma^2}\right), \quad x > 0$$

**Gamma:**
$$f(x) = \frac{x^{k-1}e^{-x/\theta}}{\theta^k \Gamma(k)}, \quad x > 0$$

**Beta:**
$$f(x) = \frac{x^{\alpha-1}(1-x)^{\beta-1}}{B(\alpha,\beta)}, \quad 0 \leq x \leq 1$$

---

## References

1. Briggs A, et al. Decision Modelling for Health Economic Evaluation. Oxford University Press, 2006.
2. NICE Decision Support Unit Technical Support Document 15: Cost-effectiveness modelling using patient-level simulation, 2014.
3. Ettehad D, et al. Blood pressure lowering for prevention of cardiovascular disease and death: a systematic review and meta-analysis. Lancet 2016;387:957-67.
4. Sullivan PW, Ghushchyan V. Preference-Based EQ-5D Index Scores for Chronic Conditions in the United States. Med Decis Making 2006;26:410-20.
5. Monticone S, et al. Cardiovascular events and target organ damage in primary aldosteronism compared with essential hypertension. Lancet Diabetes Endocrinol 2018;6:41-50.

---

**Document Control:**
- Author: HEOR Technical Documentation Team
- Review Status: Draft
- Code Reference: `src/psa.py`
- Last Updated: February 2026
