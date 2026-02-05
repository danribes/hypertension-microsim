# Hypertension Microsimulation CEA: Technical Guide

## Overview

This document explains how the hypertension microsimulation model works after population generation, with particular emphasis on the **dual uncertainty framework** that separates:

1. **First-order (stochastic) uncertainty**: Patient-level variability inherent in the microsimulation
2. **Second-order (parameter) uncertainty**: Uncertainty in model input parameters, addressed via PSA

---

## Table of Contents

1. [Simulation Architecture](#1-simulation-architecture)
2. [Patient Journey Through the Model](#2-patient-journey-through-the-model)
3. [Event Transition Logic](#3-event-transition-logic)
4. [Outcome Accrual](#4-outcome-accrual)
5. [Dual Uncertainty Framework](#5-dual-uncertainty-framework)
6. [PSA Implementation](#6-psa-implementation)
7. [Key Code References](#7-key-code-references)

---

## 1. Simulation Architecture

### 1.1 High-Level Flow

```
Population Generation ──► Simulation.run() ──► CEAResults
        │                        │
        │                  ┌─────┴─────┐
        │                  │  Monthly  │
        │                  │   Cycle   │◄────┐
        │                  └─────┬─────┘     │
        │                        │           │
        ▼                        ▼           │
   List[Patient]           For each patient: │
                           1. Adherence check│
                           2. AF onset check │
                           3. CV event sample│
                           4. Accrue costs   │
                           5. Update SBP     │
                           6. Advance time   │
                           7. Renal check    │
                                │            │
                                └────────────┘
                                 (n_cycles)
```

### 1.2 Configuration (`SimulationConfig`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_patients` | 1,000 | Patients per treatment arm |
| `time_horizon_months` | 480 | 40-year simulation |
| `cycle_length_months` | 1.0 | Monthly cycles |
| `discount_rate` | 0.03 | 3% annual for costs/QALYs |
| `use_half_cycle_correction` | True | CHEERS 2022 compliant |
| `use_competing_risks_framework` | True | Proper cause-specific hazards |
| `economic_perspective` | "societal" | Includes indirect costs |

**Reference**: `simulation.py:24-71`

---

## 2. Patient Journey Through the Model

### 2.1 Treatment Assignment

When `Simulation.run()` is called, each patient in the cohort receives their assigned treatment:

```python
for patient in patients:
    self.treatment_mgr.assign_treatment(patient, treatment)
```

The `TreatmentManager`:
1. Sets `patient.treatment` to the assigned treatment
2. Calculates the treatment effect on SBP based on:
   - Base treatment effect (IXA-001: ~20 mmHg, Spiro: ~9 mmHg)
   - Individual variation (sampled from treatment-specific SD)
   - Adherence multiplier (30% effect if non-adherent)
   - Secondary HTN etiology modifier (e.g., PA patients: 1.70× for IXA-001)

**Reference**: `simulation.py:325-329`

### 2.2 Monthly Cycle Processing

Each living patient undergoes the following sequence every cycle:

```
┌──────────────────────────────────────────────────────────────┐
│                    MONTHLY CYCLE (for each patient)          │
├──────────────────────────────────────────────────────────────┤
│ 1. Adherence transition check                                │
│    └─ Bernoulli sample: adherent ↔ non-adherent              │
│                                                              │
│ 2. Hyperkalemia management (quarterly, Spiro only)           │
│    └─ K+ > 5.0: dose reduction, potassium binders            │
│                                                              │
│ 3. Neurological progression check                            │
│    └─ Normal → MCI → Dementia                                │
│                                                              │
│ 4. AF onset check (aldosterone-specific)                     │
│    └─ Bernoulli sample based on PA status, treatment         │
│                                                              │
│ 5. Cardiovascular event sampling ◄── MAIN STOCHASTIC EVENT   │
│    └─ Multinomial sample from competing risks                │
│    └─ Events: MI, Ischemic Stroke, Hemorrhagic Stroke,       │
│               TIA, HF, CV Death, Non-CV Death                │
│                                                              │
│ 6. TIA → Stroke conversion (if recent TIA)                   │
│    └─ 10% 90-day risk, front-loaded                          │
│                                                              │
│ 7. Accrue costs and QALYs (state-based)                      │
│    └─ Discounted monthly costs + drug costs                  │
│    └─ Utility-weighted monthly QALYs                         │
│                                                              │
│ 8. Update SBP dynamics                                       │
│    └─ SBP(t+1) = SBP(t) + age_drift + ε - treatment_effect   │
│    └─ ε ~ N(0, 2.0) → PATIENT-LEVEL STOCHASTICITY            │
│                                                              │
│ 9. Advance time (age, eGFR decline, K+ dynamics)             │
│    └─ KFRE-informed eGFR decline with risk stratification    │
│    └─ Renal state transitions based on eGFR thresholds       │
│                                                              │
│ 10. Discontinuation check                                    │
│     └─ Bernoulli sample for treatment dropout                │
└──────────────────────────────────────────────────────────────┘
```

**Reference**: `simulation.py:338-485`

---

## 3. Event Transition Logic

### 3.1 Transition Probability Calculation

The `TransitionCalculator` computes monthly probabilities for each competing event:

```python
probs = TransitionProbabilities()

# MI probability
base_mi_prob = risk_calc.get_monthly_event_prob(...)
probs.to_mi = base_mi_prob * phenotype_modifier * dipping_risk_mult * treatment_factor

# Similar for stroke, HF, death...
```

**Key modifiers applied:**
| Modifier | Source | Example |
|----------|--------|---------|
| Phenotype modifier | `baseline_risk_profile.get_dynamic_modifier()` | GCUA Type I: 1.5× MI |
| Treatment effect | `_get_treatment_risk_factor()` | PA + IXA-001: 0.65× HF |
| Prior event multiplier | `PRIOR_EVENT_MULT` | Prior MI: 2.5× MI |
| Nocturnal dipping | Patient attribute | Reverse dipper: 1.8× |

**Reference**: `transitions.py:467-594`

### 3.2 Competing Risks Framework

Rather than naive probability capping, the model uses **cause-specific hazards**:

```python
def _apply_competing_risks(self, probs):
    # Convert probability to hazard
    def prob_to_hazard(p):
        return -np.log(1 - p) if p > 0 else 0.0

    # Sum all cause-specific hazards
    total_hazard = sum(hazards.values())

    # Overall survival: S(t) = exp(-H)
    survival_prob = np.exp(-total_hazard)
    event_prob = 1 - survival_prob

    # Redistribute: P(event_k) = (h_k / H) × (1 - S)
    new_probs.to_mi = (hazards['mi'] / total_hazard) * event_prob
```

This ensures:
- Probabilities sum to ≤ 1.0
- Relative risk relationships preserved
- Proper handling of high-risk patients

**Reference**: `transitions.py:366-438`

### 3.3 Event Sampling (First-Order Uncertainty)

Events are sampled using **multinomial distribution**:

```python
def sample_event(self, patient, probs):
    event_probs = [
        probs.to_cv_death,
        probs.to_non_cv_death,
        probs.to_mi,
        probs.to_hemorrhagic_stroke,
        probs.to_ischemic_stroke,
        probs.to_hf,
        probs.to_tia,
    ]

    p_no_event = max(0.0, 1.0 - sum(event_probs))
    event_probs.append(p_no_event)

    # STOCHASTIC SAMPLE ← First-order uncertainty
    sampled_idx = self.rng.choice(len(event_outcomes), p=event_probs)
    return event_outcomes[sampled_idx]
```

**Why multinomial?** More accurate than sequential Bernoulli trials when multiple events can occur in the same period.

**Reference**: `transitions.py:659-734`

### 3.4 State Transition Cascade

```
       ┌─────────────────────────────────────────────────────────┐
       │               CARDIAC STATE MACHINE                     │
       ├─────────────────────────────────────────────────────────┤
       │                                                         │
       │   NO_ACUTE_EVENT ───────────────────────────────────┐   │
       │         │                                           │   │
       │    ┌────┼────┬────────┬────────┬────────┐          │   │
       │    ▼    ▼    ▼        ▼        ▼        ▼          │   │
       │  ACUTE ACUTE ACUTE  ACUTE    TIA    CV_DEATH       │   │
       │   MI  ISch  Hem     HF        │         │          │   │
       │    │  Str   Str      │        │         │          │   │
       │    │    │    │       │        │         ▼          │   │
       │    ▼    └────┴───────┼────────┼───► [ABSORBING]    │   │
       │  POST_MI             │        │                    │   │
       │                      ▼        ▼                    │   │
       │               POST_STROKE   (returns to            │   │
       │                      │      NO_ACUTE)              │   │
       │                      ▼                             │   │
       │               CHRONIC_HF                           │   │
       │                                                    │   │
       └────────────────────────────────────────────────────────┘
```

**Reference**: `patient.py:44-62`

---

## 4. Outcome Accrual

### 4.1 Cost Accrual

```python
def _accrue_outcomes(self, patient, results):
    # Monthly state management costs
    monthly_cost = get_total_cost(patient, self.costs, is_monthly=True)

    # Monthly productivity loss (societal perspective)
    monthly_indirect = get_productivity_loss(patient, self.costs, is_monthly=True)

    # Drug costs
    drug_cost = get_drug_cost(patient, self.costs)

    # Discounting with half-cycle correction
    discount_factor = self._get_discount_factor(patient.time_in_simulation)

    patient.accrue_costs(discounted_cost)
    results.total_costs += discounted_cost
    results.total_indirect_costs += monthly_indirect * discount_factor
```

**Reference**: `simulation.py:512-563`

### 4.2 QALY Accrual

```python
qaly = calculate_monthly_qaly(
    patient,
    discount_rate,
    cycle_length_months,
    use_half_cycle_correction
)
patient.accrue_qalys(qaly)
results.total_qalys += qaly
```

**Utility calculation** applies multiplicative disutilities:
```
Utility = Baseline × (1 - disutility_cardiac) × (1 - disutility_renal) × ...
```

**Reference**: `utilities.py`

---

## 5. Dual Uncertainty Framework

### 5.1 Conceptual Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DUAL UNCERTAINTY MODEL                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           SECOND-ORDER (PARAMETER) UNCERTAINTY               │   │
│  │                    (Addressed by PSA)                        │   │
│  │                                                              │   │
│  │  • Treatment effects (SBP reduction mean/SD)                 │   │
│  │  • Relative risks (per 10 mmHg)                              │   │
│  │  • Costs (acute events, chronic management, drugs)           │   │
│  │  • Utilities/disutilities                                    │   │
│  │  • Discontinuation rates                                     │   │
│  │                                                              │   │
│  │  PSA Outer Loop: K iterations                                │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  For k = 1 to K:                                     │   │   │
│  │  │    Sample parameters from distributions              │   │   │
│  │  │    ↓                                                 │   │   │
│  └──┼────────────────────────────────────────────────────────┘   │
│     │                                                            │
│     ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           FIRST-ORDER (STOCHASTIC) UNCERTAINTY              │ │
│  │                (Inherent in microsimulation)                 │ │
│  │                                                              │ │
│  │  • Which specific patients experience events                 │ │
│  │  • Timing of events within simulation                        │ │
│  │  • SBP trajectory (stochastic ε term)                        │ │
│  │  • Adherence transitions                                     │ │
│  │  • eGFR decline variation                                    │ │
│  │                                                              │ │
│  │  Inner Loop: N patients × T cycles                           │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │  For each patient i = 1 to N:                        │   │ │
│  │  │    For each cycle t = 1 to T:                        │   │ │
│  │  │      • Sample event from multinomial(probs)          │   │ │
│  │  │      • Sample SBP noise: ε ~ N(0, 2)                 │   │ │
│  │  │      • Sample adherence change: Bernoulli            │   │ │
│  │  │      • Sample eGFR variation                         │   │ │
│  │  │    end                                               │   │ │
│  │  │  end                                                 │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 5.2 Where Stochasticity Enters (First-Order)

| Location | Mechanism | Code Reference |
|----------|-----------|----------------|
| Event occurrence | `rng.choice()` multinomial | `transitions.py:712` |
| SBP dynamics | `rng.normal(0, 2.0)` monthly noise | `patient.py:328` |
| Adherence changes | `rng.random() < prob` Bernoulli | `transitions.py:929` |
| AF onset | `rng.random() < prob` Bernoulli | `transitions.py:1073` |
| TIA→Stroke | `rng.random() < prob` Bernoulli | `transitions.py:792` |
| K+ dynamics | `np.random.normal()` reversion | `patient.py:509` |
| ESRD mortality | `rng.random() < prob` Bernoulli | `transitions.py:839` |

### 5.3 Parameter Distributions (Second-Order)

| Parameter | Distribution | Rationale |
|-----------|--------------|-----------|
| Treatment effects | Normal | Can theoretically be negative |
| Relative risks | Lognormal | Must be positive, often right-skewed |
| Costs | Gamma | Positive, right-skewed |
| Utilities | Beta | Bounded 0-1 |
| Discontinuation | Beta | Probability parameter |
| Risk modifiers | Lognormal | Multiplicative factor, positive |

**Reference**: `psa.py:132-469`

---

## 6. PSA Implementation

### 6.1 Nested Loop Architecture

```python
class PSARunner:
    """
    Outer loop: Sample parameters from distributions (K iterations)
    Inner loop: Simulate patients with sampled parameters (N patients per arm)
    """

    def run(self, n_iterations=1000, use_common_random_numbers=True):
        # Sample ALL parameter sets upfront
        parameter_samples = self.sampler.sample(n_iterations)

        for k in range(n_iterations):
            params_k = {name: values[k] for name, values in parameter_samples.items()}

            # Run simulation with these FIXED parameters
            # Patient-level stochasticity happens INSIDE
            result = self._run_single_iteration(k, params_k, use_crn=True)
            iterations.append(result)
```

**Reference**: `psa.py:1131-1177`

### 6.2 Common Random Numbers (CRN)

CRN reduces variance in incremental comparisons by ensuring:
1. **Same patients** in both arms (identical population seeds)
2. **Synchronized random streams** for event sampling

```python
if use_crn:
    base_seed = (self.seed or 0) + iteration * 1000000
    population_seed = base_seed
    sim_seed_ixa = base_seed + 1
    sim_seed_comp = base_seed + 1  # SAME SEED ← CRN
```

**Effect**: The *same* patient experiences the *same* random draws in both arms, making incremental differences attributable solely to treatment effect.

**Reference**: `psa.py:1199-1208`

### 6.3 Correlated Parameter Sampling

Uses **Cholesky decomposition** for correlation structure:

```python
class CholeskySampler:
    def _sample_correlated_group(self, group, n_samples):
        # Step 1: Generate independent standard normals
        Z = self.rng.standard_normal((n_samples, n_params))

        # Step 2: Transform to correlated normals: X = Z × L^T
        X = Z @ group.cholesky_L.T

        # Step 3: Transform marginals via inverse CDF
        for i, param_name in enumerate(group.parameters):
            u = stats.norm.cdf(X[:, i])  # Correlated uniform
            samples[param_name] = self._inverse_cdf(dist, u)  # Target distribution
```

**Correlation groups:**
- Acute costs (hospital inflation affects all events)
- Utilities (EQ-5D measurement methodology)
- Risk ratios (shared meta-analysis evidence)

**Reference**: `psa.py:542-654`

### 6.4 PSA Outputs

| Output | Description | Code Reference |
|--------|-------------|----------------|
| CE Plane | Scatter of (ΔQALYs, ΔCosts) | `psa.py:860-866` |
| CEAC | P(cost-effective) vs WTP | `psa.py:772-793` |
| EVPI | Value of perfect information | `psa.py:799-838` |
| INB | Incremental Net Benefit | `psa.py:905-940` |
| Convergence | Running mean stability | `psa.py:975-1053` |

---

## 7. Key Code References

### 7.1 Core Simulation Loop
```
simulation.py:338-485   Simulation.run() main loop
```

### 7.2 Event Sampling
```
transitions.py:659-734   TransitionCalculator.sample_event()
transitions.py:467-594   TransitionCalculator.calculate_transitions()
transitions.py:366-438   _apply_competing_risks()
```

### 7.3 Patient State
```
patient.py:88-253        Patient dataclass
patient.py:348-404       Cardiac/renal/neuro transitions
patient.py:406-499       Time advancement and eGFR updates
```

### 7.4 PSA Framework
```
psa.py:1093-1177         PSARunner.run()
psa.py:1179-1247         _run_single_iteration()
psa.py:542-654           CholeskySampler
psa.py:693-970           PSAResults (CEAC, EVPI, INB)
```

### 7.5 Population Generation
```
population.py:112-609    PopulationGenerator.generate()
population.py:244-328    Secondary HTN etiology assignment
```

---

## Summary

The hypertension microsimulation implements a **rigorous dual-uncertainty framework**:

1. **First-order uncertainty** is captured through:
   - Multinomial event sampling each cycle
   - Stochastic SBP dynamics
   - Probabilistic adherence/discontinuation transitions
   - Individual patient trajectories

2. **Second-order uncertainty** is characterized through:
   - 40+ parameter distributions (costs, utilities, treatment effects, risks)
   - Cholesky-based correlated sampling
   - 1,000+ PSA iterations with Common Random Numbers
   - CEAC, EVPI, and INB outputs for decision-making

This separation ensures that cost-effectiveness results properly reflect both **what could happen to patients** (first-order) and **what we don't know about model inputs** (second-order).

---

*Generated: 2026-02-05*
*Model Version: 4.0 (Dual-Branch Phenotyping with Option B)*
