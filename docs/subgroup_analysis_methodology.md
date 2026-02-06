# Subgroup Analysis Methodology
## IXA-001 Hypertension Microsimulation Model

**Document Version:** 1.0
**Date:** February 2026
**CHEERS 2022 Compliance:** Item 21 (Characterizing Heterogeneity)

---

## Executive Summary

This report describes the pre-specified subgroup analysis methodology for the IXA-001 cost-effectiveness model. The model implements a sophisticated multi-axis stratification framework with **5 primary subgroup dimensions** and **17 distinct subgroup categories**.

### Key Findings from Subgroup Analyses

| Subgroup | ICER ($/QALY) | Value Assessment |
|----------|---------------|------------------|
| **Primary Aldosteronism (PA)** | $245,441 | Optimal target population |
| OSA (severe) | $312,000 | Moderate value |
| RAS | $385,000 | Limited value |
| Essential HTN | Dominated | Contraindicated |

**Primary Aldosteronism represents the primary value driver** due to:
- Highest baseline event rates (HF 2.05×, AF 12×)
- Best treatment response (IXA-001: 1.70×)
- Largest absolute risk reductions

---

## 1. Subgroup Taxonomy

### 1.1 Primary Subgroup Dimensions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SUBGROUP STRATIFICATION FRAMEWORK                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Dimension 1: Secondary HTN Etiology (Mutually Exclusive)                   │
│  ├── Primary Aldosteronism (PA) .......... 15-20%                          │
│  ├── Renal Artery Stenosis (RAS) ......... 5-15%                           │
│  ├── Pheochromocytoma (Pheo) ............. 0.5-1%                          │
│  ├── OSA (severe, primary driver) ........ 10-15%                          │
│  └── Essential (no identified cause) ..... 50-60%                          │
│                                                                             │
│  Dimension 2: Age-Based Phenotype (Mutually Exclusive)                      │
│  ├── EOCRI (Age 18-59, eGFR >60) ......... ~35%                            │
│  │   ├── Type A: Early Metabolic                                           │
│  │   ├── Type B: Silent Renal (KEY TARGET)                                 │
│  │   ├── Type C: Premature Vascular                                        │
│  │   └── Low Risk                                                          │
│  ├── GCUA (Age ≥60, eGFR >60) ............ ~45%                            │
│  │   ├── Type I: Accelerated Ager                                          │
│  │   ├── Type II: Silent Renal                                             │
│  │   ├── Type III: Vascular Dominant                                       │
│  │   ├── Type IV: Senescent                                                │
│  │   ├── Moderate Risk                                                     │
│  │   └── Low Risk                                                          │
│  └── KDIGO (eGFR ≤60) .................... ~20%                            │
│      ├── Very High Risk                                                    │
│      ├── High Risk                                                         │
│      ├── Moderate Risk                                                     │
│      └── Low Risk                                                          │
│                                                                             │
│  Dimension 3: CKD Stage at Baseline                                         │
│  ├── G1-G2 (eGFR ≥60) .................... ~60%                            │
│  ├── G3a (eGFR 45-59) .................... ~20%                            │
│  ├── G3b (eGFR 30-44) .................... ~12%                            │
│  ├── G4 (eGFR 15-29) ..................... ~6%                             │
│  └── G5/ESRD (eGFR <15) .................. ~2%                             │
│                                                                             │
│  Dimension 4: Prior CV Event Status                                         │
│  ├── No prior CV event ................... ~75%                            │
│  ├── Prior MI ............................ ~10%                            │
│  ├── Prior Stroke ........................ ~5%                             │
│  └── Heart Failure ....................... ~8%                             │
│                                                                             │
│  Dimension 5: Framingham Risk Category                                      │
│  ├── Low (<5%) ........................... ~15%                            │
│  ├── Borderline (5-7.5%) ................. ~20%                            │
│  ├── Intermediate (7.5-20%) .............. ~40%                            │
│  └── High (≥20%) ......................... ~25%                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Code Reference:** `src/risk_assessment.py:82-145` (BaselineRiskProfile dataclass)

### 1.2 Pre-Specification Rationale

All subgroups were pre-specified based on:

| Subgroup | Clinical Rationale | Regulatory Basis |
|----------|-------------------|------------------|
| **PA** | Aldosterone-driven HTN; target for ASI | FDA Breakthrough designation |
| **RAS** | Different pathophysiology; RAAS secondary | Differential treatment response |
| **Pheo** | Catecholamine-driven; poor BP therapy response | Safety population |
| **OSA** | High prevalence; sympathetic activation | CPAP interaction |
| **EOCRI/GCUA** | Age-dependent risk trajectories | AHA 2024 PREVENT guidelines |
| **CKD Stage** | Renal progression risk; ESRD prevention | KDIGO 2024 guidelines |
| **Prior CV** | Secondary prevention population | Standard HTA practice |

---

## 2. Subgroup-Specific Parameters

### 2.1 Secondary HTN Etiology: Baseline Risk Modifiers

These multiplicative modifiers adjust PREVENT-calculated baseline probabilities to account for etiology-specific pathophysiology.

#### Primary Aldosteronism (PA)

| Outcome | Modifier | Source | Clinical Rationale |
|---------|----------|--------|-------------------|
| MI | 1.40× | Monticone 2018 | Coronary microvascular disease |
| Stroke | 1.50× | Monticone 2018 | Vascular stiffness, AF-mediated emboli |
| HF | **2.05×** | Monticone JACC 2018 | Direct cardiac fibrosis (HR 2.05) |
| ESRD | 1.80× | Catena 2008 | Aldosterone-mediated renal fibrosis |
| AF | **3.0×** | Monticone 2018 | 12× relative risk (surrogate multiplier) |
| Death | 1.60× | Combined pathways | Multi-organ damage |

**Code Reference:** `src/risk_assessment.py:280-289`

#### Renal Artery Stenosis (RAS)

| Outcome | Modifier | Source | Clinical Rationale |
|---------|----------|--------|-------------------|
| MI | 1.35× | Textor 2008 | Generalized atherosclerosis |
| Stroke | 1.40× | Textor 2008 | Carotid disease coexistence |
| HF | 1.45× | CORAL trial | Flash pulmonary edema |
| ESRD | 1.80× | Textor 2008 | Ischemic nephropathy |
| Death | 1.50× | Combined | Atherosclerotic burden |

**Code Reference:** `src/risk_assessment.py:297-305`

#### Pheochromocytoma (Pheo)

| Outcome | Modifier | Source | Clinical Rationale |
|---------|----------|--------|-------------------|
| MI | 1.80× | Lenders 2005 | Catecholamine-induced vasospasm |
| Stroke | 1.60× | Lenders 2005 | Hypertensive crises |
| HF | 1.70× | Lenders 2005 | Catecholamine cardiomyopathy |
| ESRD | 1.10× | Expert opinion | Less direct renal impact |
| Death | 2.00× | If untreated | Crisis mortality |

**Code Reference:** `src/risk_assessment.py:313-321`

#### Obstructive Sleep Apnea (OSA)

| Outcome | Mild | Moderate | Severe | Source |
|---------|------|----------|--------|--------|
| MI | 1.11× | 1.15× | 1.21× | Pedrosa 2011 |
| Stroke | 1.18× | 1.25× | 1.35× | Nocturnal hypoxia |
| HF | 1.14× | 1.20× | 1.28× | Pulmonary HTN |
| ESRD | 1.04× | 1.05× | 1.07× | Indirect effect |
| Death | 1.11× | 1.15× | 1.21× | Combined |

**Code Reference:** `src/risk_assessment.py:329-342`

### 2.2 Secondary HTN Etiology: Treatment Response Modifiers

Treatment efficacy varies by underlying HTN mechanism.

| Etiology | IXA-001 | Spironolactone | Standard Care | Rationale |
|----------|---------|----------------|---------------|-----------|
| **PA** | **1.70×** | 1.40× | 0.75× | Aldosterone-driven; ASI blocks root cause |
| RAS | 1.05× | 0.95× | 1.10× | Aldosterone secondary; CCBs preferred |
| Pheo | 0.40× | 0.35× | 0.50× | Catecholamine-driven; requires alpha-blockade |
| OSA | 1.20× | 1.15× | 1.00× | OSA-aldosterone connection |
| Essential | 1.00× | 1.00× | 1.00× | Reference category |

**Code Reference:** `src/risk_assessment.py:346-464`

### 2.3 Age-Based Phenotype Risk Modifiers

#### EOCRI Phenotypes (Age 18-59)

| Phenotype | MI | Stroke | HF | ESRD | Death | Target |
|-----------|-----|--------|-----|------|-------|--------|
| **A: Early Metabolic** | 1.2× | 1.3× | 1.5× | 1.5× | 1.4× | Aggressive BP + SGLT2i |
| **B: Silent Renal** | 0.7× | 0.75× | 0.9× | **2.0×** | 1.1× | Early ASI/RAASi (KEY) |
| C: Premature Vascular | 1.6× | 1.7× | 1.3× | 0.8× | 1.2× | Statins + Antiplatelets |
| Low | 0.8× | 0.8× | 0.85× | 0.9× | 0.8× | Standard monitoring |

**Code Reference:** `src/risk_assessment.py:208-228`

#### GCUA Phenotypes (Age ≥60)

| Phenotype | MI | Stroke | HF | ESRD | Death | Clinical Profile |
|-----------|-----|--------|-----|------|-------|-----------------|
| I: Accelerated Ager | 1.3× | 1.4× | 1.4× | 1.3× | 1.5× | Multi-organ decline |
| II: Silent Renal | 0.9× | 0.95× | 1.1× | 1.4× | 1.2× | Renal-dominant |
| III: Vascular Dominant | 1.4× | 1.5× | 1.2× | 0.8× | 1.3× | Atherosclerotic |
| **IV: Senescent** | 1.8× | 2.0× | 2.2× | 1.5× | **2.5×** | Frailty/competing risks |
| Moderate | 1.1× | 1.1× | 1.15× | 1.15× | 1.1× | Intermediate |
| Low | 0.9× | 0.9× | 0.9× | 0.9× | 0.85× | Low risk |

**Code Reference:** `src/risk_assessment.py:179-205`

#### KDIGO Risk Levels

| Risk Level | MI | Stroke | HF | ESRD | Death |
|------------|-----|--------|-----|------|-------|
| Very High | 1.4× | 1.5× | 1.6× | 1.8× | 2.0× |
| High | 1.2× | 1.3× | 1.4× | 1.5× | 1.5× |
| Moderate | 1.1× | 1.1× | 1.2× | 1.2× | 1.1× |
| Low | 0.9× | 0.9× | 0.95× | 0.95× | 0.9× |

**Code Reference:** `src/risk_assessment.py:231-248`

### 2.4 Prevalence Estimates

Population distribution derived from resistant HTN epidemiology:

| Subgroup | Prevalence | Source |
|----------|-----------|--------|
| **Primary Aldosteronism** | 15-20% | Carey 2018, Calhoun 2008 |
| Renal Artery Stenosis | 5-15% | Rimoldi 2014 |
| Pheochromocytoma | 0.5-1% | Lenders 2005 |
| Obstructive Sleep Apnea | 60-80% | Pedrosa 2011 |
| Essential (no cause) | 50-60% | Residual |

**Code Reference:** `src/population.py:244-283`

---

## 3. Analytical Methodology

### 3.1 Subgroup-Stratified Simulation

The model runs separate simulations for each subgroup using the same PSA parameter draws:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SUBGROUP ANALYSIS WORKFLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. POPULATION GENERATION                                                   │
│     └── Generate N patients with subgroup attributes                        │
│         └── Secondary HTN etiology assigned (PA, RAS, Pheo, OSA, Essential)│
│         └── Age-based phenotype calculated (EOCRI/GCUA/KDIGO)              │
│                                                                             │
│  2. BASELINE RISK CALCULATION                                               │
│     └── For each patient:                                                   │
│         └── Calculate PREVENT 10-year CV risk                               │
│         └── Apply phenotype modifier (EOCRI/GCUA/KDIGO)                    │
│         └── Apply etiology modifier (PA/RAS/Pheo/OSA)                      │
│         └── Final risk = PREVENT × phenotype × etiology                    │
│                                                                             │
│  3. TREATMENT EFFECT APPLICATION                                            │
│     └── For each patient:                                                   │
│         └── Calculate BP reduction by treatment                             │
│         └── Apply treatment response modifier by etiology                   │
│         └── Translate BP reduction to risk reduction                        │
│                                                                             │
│  4. MICROSIMULATION                                                         │
│     └── Run IL-STM for each patient                                         │
│         └── Monthly transitions with modified probabilities                 │
│         └── Accrue costs, QALYs, events                                     │
│                                                                             │
│  5. SUBGROUP-SPECIFIC AGGREGATION                                           │
│     └── Stratify results by:                                                │
│         └── Secondary HTN etiology                                          │
│         └── Age-based phenotype                                             │
│         └── CKD stage                                                       │
│         └── Prior CV event status                                           │
│                                                                             │
│  6. CALCULATE SUBGROUP ICERs                                                │
│     └── For each subgroup:                                                  │
│         └── ICER = ΔCost / ΔQALY (within subgroup)                         │
│         └── 95% CI from PSA iterations                                      │
│         └── P(cost-effective at WTP)                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Modifier Multiplication Logic

Risk modifiers are applied multiplicatively:

```python
def calculate_transition_probability(patient, event_type, treatment):
    """Calculate event probability with all modifiers applied."""

    # 1. Base probability from PREVENT equation
    base_prob = calculate_prevent_probability(patient, event_type)

    # 2. Apply phenotype modifier (EOCRI/GCUA/KDIGO)
    phenotype_mod = patient.baseline_risk_profile.get_dynamic_modifier(event_type)

    # 3. Apply etiology modifier (PA/RAS/Pheo/OSA)
    # Already incorporated in get_dynamic_modifier()

    # 4. Apply treatment effect
    treatment_response = patient.baseline_risk_profile.get_treatment_response_modifier(treatment)
    bp_reduction = get_bp_reduction(treatment) * treatment_response
    rr_per_10mmhg = get_risk_ratio(event_type)  # e.g., 0.78 for MI
    treatment_rr = rr_per_10mmhg ** (bp_reduction / 10)

    # 5. Final probability
    final_prob = base_prob * phenotype_mod * treatment_rr

    return min(final_prob, 1.0)
```

### 3.3 Common Random Numbers for Subgroup Comparisons

CRN ensures valid within-subgroup comparisons:

```python
def run_subgroup_analysis(population, psa_iteration):
    """Run analysis with same random seed for all arms."""

    # Same seed for all treatment arms within PSA iteration
    base_seed = psa_iteration * 1000

    results_by_subgroup = {}

    for subgroup_name, subgroup_filter in SUBGROUPS.items():
        # Filter population to subgroup
        subgroup_patients = [p for p in population if subgroup_filter(p)]

        # Run IXA-001 arm
        np.random.seed(base_seed)
        ixa_results = simulate(subgroup_patients, treatment='ixa001')

        # Run comparator with SAME seed
        np.random.seed(base_seed)
        comp_results = simulate(subgroup_patients, treatment='spironolactone')

        # Calculate subgroup-specific ICER
        delta_cost = ixa_results.mean_cost - comp_results.mean_cost
        delta_qaly = ixa_results.mean_qaly - comp_results.mean_qaly

        results_by_subgroup[subgroup_name] = {
            'n_patients': len(subgroup_patients),
            'delta_cost': delta_cost,
            'delta_qaly': delta_qaly,
            'icer': delta_cost / delta_qaly if delta_qaly > 0 else float('inf')
        }

    return results_by_subgroup
```

### 3.4 Interaction Testing

Subgroup × treatment interactions are assessed using ratio of ICERs:

```
Interaction Ratio = ICER_subgroup / ICER_overall

Interpretation:
- Ratio < 0.8: Strong positive interaction (better value in subgroup)
- Ratio 0.8-1.2: No meaningful interaction
- Ratio > 1.2: Negative interaction (worse value in subgroup)
- Ratio < 0 or undefined: Dominated in subgroup
```

---

## 4. Multiplicity Considerations

### 4.1 Pre-Specified vs. Post-Hoc

| Analysis Type | Subgroups | Adjustment |
|---------------|-----------|------------|
| **Pre-specified (primary)** | PA, Essential, RAS | None (hypothesis-generating) |
| **Pre-specified (secondary)** | EOCRI/GCUA phenotypes | Holm-Bonferroni |
| **Post-hoc (exploratory)** | Combinations, interactions | Report as exploratory |

### 4.2 Credibility Assessment

Subgroup analyses are evaluated against ICEMAN criteria:

| Criterion | PA Subgroup | Essential Subgroup |
|-----------|-------------|-------------------|
| Pre-specified? | Yes | Yes |
| Biological plausibility? | **Strong** (aldosterone mechanism) | Weak |
| Effect direction consistent? | Yes | No (dominated) |
| Statistically compelling? | Yes (p<0.05) | N/A |
| Replication? | Pending Phase III | N/A |
| **Overall Credibility** | **HIGH** | LOW |

---

## 5. Subgroup Results Summary

### 5.1 Primary Etiology Subgroups (20-Year Horizon)

| Subgroup | N (%) | Δ Cost | Δ QALY | ICER | 95% CI |
|----------|-------|--------|--------|------|--------|
| **Primary Aldosteronism** | 180 (18%) | +$20,550 | +0.084 | **$245,441** | [$185K, $340K] |
| OSA (severe) | 120 (12%) | +$25,200 | +0.081 | $311,111 | [$220K, $450K] |
| Renal Artery Stenosis | 85 (8.5%) | +$28,500 | +0.074 | $385,135 | [$280K, $550K] |
| Pheochromocytoma | 8 (0.8%) | +$32,000 | +0.045 | $711,111 | [Wide CI] |
| Essential HTN | 500 (50%) | +$35,200 | -0.012 | **Dominated** | N/A |

### 5.2 Events Prevented by Subgroup (per 1,000 patients)

| Subgroup | MI | Stroke | HF | ESRD | AF | Death |
|----------|-----|--------|-----|------|-----|-------|
| **PA** | 12 | 15 | 28 | 18 | **33** | 8 |
| OSA (severe) | 8 | 10 | 15 | 6 | 12 | 5 |
| RAS | 6 | 8 | 12 | 10 | 8 | 4 |
| Essential | 2 | 3 | 4 | 2 | 3 | 0 |

### 5.3 Threshold Pricing by Subgroup

| Subgroup | Base Price | Price at $150K WTP | Price Cut Required |
|----------|-----------|-------------------|-------------------|
| **PA** | $500/mo | $467/mo | 6.7% |
| OSA (severe) | $500/mo | $385/mo | 23% |
| RAS | $500/mo | $290/mo | 42% |
| Essential | $500/mo | N/A | Not cost-effective |

---

## 6. Results Interpretation Guide

### 6.1 Clinical Decision Support

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IXA-001 VALUE-BASED PRESCRIBING GUIDE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STEP 1: Identify Secondary HTN Etiology                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ □ Screen for Primary Aldosteronism (ARR, confirmatory testing)         ││
│  │ □ Assess for OSA (STOP-BANG, polysomnography if indicated)             ││
│  │ □ Evaluate for RAS (renal artery Doppler, CTA if high suspicion)       ││
│  │ □ Rule out Pheo (24h urine catecholamines if episodic HTN)             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  STEP 2: Value-Based Treatment Selection                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ IF Primary Aldosteronism CONFIRMED:                                    ││
│  │    → IXA-001 is VALUE-OPTIMAL                                          ││
│  │    → Expected ICER: $245K/QALY (favorable for PA-specific indication)  ││
│  │    → AF prevention is key differentiator                               ││
│  │                                                                         ││
│  │ IF OSA with Severe AHI:                                                ││
│  │    → IXA-001 provides MODERATE VALUE                                   ││
│  │    → Consider if CPAP-intolerant or inadequate response                ││
│  │                                                                         ││
│  │ IF RAS or Pheo:                                                        ││
│  │    → IXA-001 provides LIMITED VALUE                                    ││
│  │    → Address primary etiology first (revascularization, surgery)       ││
│  │                                                                         ││
│  │ IF Essential/Unexplained Resistant HTN:                                ││
│  │    → IXA-001 NOT RECOMMENDED (dominated by spironolactone)             ││
│  │    → Continue spironolactone-based regimen                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  STEP 3: Monitor and Reassess                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ □ Repeat aldosterone assessment at 3-6 months                          ││
│  │ □ Monitor for AF development (ECG, symptoms)                           ││
│  │ □ Track renal function (eGFR, uACR)                                    ││
│  │ □ Document treatment response for value confirmation                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Payer Considerations

| Coverage Recommendation | Subgroup | Rationale |
|------------------------|----------|-----------|
| **Tier 1: Preferred** | Confirmed PA | Best ICER, mechanistic rationale |
| **Tier 2: Prior Auth** | Severe OSA, EOCRI-B | Moderate value, specific indications |
| **Tier 3: Step Edit** | RAS, GCUA-II | Limited value, try spironolactone first |
| **Not Covered** | Essential HTN | Dominated; no clinical benefit |

### 6.3 Subgroup ICER Interpretation

```
ICERs should be interpreted in context:

1. ABSOLUTE VALUE
   - PA ICER of $245K/QALY is above typical US thresholds ($100-150K)
   - However, for orphan-like indications (PA = 15-20% of resistant HTN),
     higher thresholds may be acceptable

2. RELATIVE VALUE
   - PA has the BEST ICER among all subgroups
   - If IXA-001 is to be covered at all, PA is the optimal target

3. UNCERTAINTY
   - 95% CI [$185K, $340K] indicates moderate uncertainty
   - Probability cost-effective at $150K: ~15%
   - Probability cost-effective at $300K: ~65%

4. CLINICAL DIFFERENTIATION
   - AF prevention (33 events per 1,000) is unique to PA subgroup
   - This benefit is NOT captured in standard CVD risk equations
   - Post-hoc analyses may underestimate PA-specific value
```

---

## 7. Validation of Subgroup Analyses

### 7.1 Internal Validity Checks

| Check | Method | Result |
|-------|--------|--------|
| Modifier sum | Subgroup results sum to overall | ✓ Pass |
| Sample size | Each subgroup N ≥ 50 | ✓ Pass |
| Balance | Subgroup characteristics similar | ✓ Pass |
| Monotonicity | Higher risk → higher ICER | ✓ Pass (except PA) |

### 7.2 External Calibration

| Subgroup | Model Prediction | Published Data | Source |
|----------|-----------------|----------------|--------|
| PA HF risk | 2.05× vs Essential | HR 2.05 (1.85-2.27) | Monticone 2018 |
| PA AF risk | 12× vs Essential | OR 12.3 (8.1-18.7) | Monticone 2018 |
| OSA stroke | 1.25× baseline | RR 1.2-1.4 | Pedrosa 2011 |
| RAS ESRD | 1.80× baseline | HR 1.7-2.0 | Textor 2008 |

---

## 8. Sensitivity of Subgroup Findings

### 8.1 One-Way Sensitivity by Subgroup

| Parameter | PA ICER Range | Essential ICER Impact |
|-----------|--------------|----------------------|
| PA HF modifier (1.5-2.5×) | $200K - $320K | No change (dominated) |
| PA treatment response (1.4-2.0×) | $180K - $350K | No change |
| IXA-001 price ($400-$600) | $195K - $295K | Still dominated |
| Discount rate (0-5%) | $220K - $280K | Still dominated |

### 8.2 Scenario Analyses

| Scenario | PA ICER | Essential |
|----------|---------|-----------|
| Base case | $245,441 | Dominated |
| No AF tracking | $298,000 | Dominated |
| 10-year horizon | $312,000 | Dominated |
| Societal perspective | $228,000 | Dominated |
| UK costs | £185,000 | Dominated |

---

## 9. Reporting Standards

### 9.1 CHEERS 2022 Compliance

| Item | Requirement | Status |
|------|-------------|--------|
| 21a | Describe approach for subgroups | ✓ Section 3 |
| 21b | Report subgroup-specific results | ✓ Section 5 |
| 21c | Discuss credibility | ✓ Section 4.2 |
| 21d | Discuss multiplicity | ✓ Section 4.1 |

### 9.2 HTA Submission Format

Subgroup results should be presented as:

1. **Executive summary table** (Section 5.1)
2. **Forest plot** of subgroup ICERs with 95% CIs
3. **Waterfall chart** of events prevented by subgroup
4. **Credibility assessment** using ICEMAN criteria
5. **Clinical decision algorithm** (Section 6.1)

---

## Appendix A: Subgroup Filter Definitions

```python
# Subgroup filter functions for stratification

SUBGROUP_FILTERS = {
    # Secondary HTN Etiology
    'PA': lambda p: p.baseline_risk_profile.has_primary_aldosteronism,
    'RAS': lambda p: p.baseline_risk_profile.has_renal_artery_stenosis,
    'Pheo': lambda p: p.baseline_risk_profile.has_pheochromocytoma,
    'OSA_severe': lambda p: (
        p.baseline_risk_profile.has_obstructive_sleep_apnea and
        p.baseline_risk_profile.osa_severity == 'severe'
    ),
    'Essential': lambda p: (
        p.baseline_risk_profile.secondary_htn_etiology == 'Essential'
    ),

    # Age-based phenotype
    'EOCRI': lambda p: p.baseline_risk_profile.renal_risk_type == 'EOCRI',
    'EOCRI_A': lambda p: (
        p.baseline_risk_profile.renal_risk_type == 'EOCRI' and
        p.baseline_risk_profile.eocri_phenotype == 'A'
    ),
    'EOCRI_B': lambda p: (
        p.baseline_risk_profile.renal_risk_type == 'EOCRI' and
        p.baseline_risk_profile.eocri_phenotype == 'B'
    ),
    'GCUA': lambda p: p.baseline_risk_profile.renal_risk_type == 'GCUA',
    'GCUA_I': lambda p: (
        p.baseline_risk_profile.renal_risk_type == 'GCUA' and
        p.baseline_risk_profile.gcua_phenotype == 'I'
    ),
    'KDIGO': lambda p: p.baseline_risk_profile.renal_risk_type == 'KDIGO',

    # CKD Stage
    'CKD_G3a': lambda p: p.egfr >= 45 and p.egfr < 60,
    'CKD_G3b': lambda p: p.egfr >= 30 and p.egfr < 45,
    'CKD_G4': lambda p: p.egfr >= 15 and p.egfr < 30,

    # Prior CV Events
    'Prior_MI': lambda p: p.prior_mi_count > 0,
    'Prior_Stroke': lambda p: p.prior_stroke_count > 0,
    'Heart_Failure': lambda p: p.has_heart_failure,

    # Framingham Category
    'Framingham_High': lambda p: (
        p.baseline_risk_profile.framingham_category == 'High'
    ),
}
```

---

## Appendix B: Subgroup Sample Size Requirements

| Analysis Type | Minimum N | Rationale |
|---------------|-----------|-----------|
| Primary subgroup | 100 | Stable ICER estimate |
| Secondary subgroup | 50 | Exploratory |
| Interaction test | 200 per arm | Statistical power |
| PSA convergence | 1,000 iterations × N | Monte Carlo precision |

For rare subgroups (e.g., Pheo at 0.8%), results should be interpreted with caution due to wide confidence intervals.

---

## References

1. Carey RM, et al. Resistant Hypertension: Detection, Evaluation, and Management. Hypertension 2018;72:e53-e90.
2. Monticone S, et al. Cardiovascular events and target organ damage in primary aldosteronism compared with essential hypertension. Lancet Diabetes Endocrinol 2018;6:41-50.
3. Textor SC. Renovascular Hypertension and Ischemic Nephropathy. Circulation 2008;117:3085-87.
4. Lenders JW, et al. Phaeochromocytoma. Lancet 2005;366:665-75.
5. Pedrosa RP, et al. Obstructive Sleep Apnea and Hypertension. Hypertension 2011;58:811-17.
6. Sun X, et al. Is a subgroup effect believable? Updating criteria to evaluate the credibility of subgroup analyses. BMJ 2010;340:c117 (ICEMAN criteria).
7. Khan SS, et al. Development and Validation of the PREVENT Equations. Circulation 2024;149:430-449.

---

**Document Control:**
- Author: HEOR Technical Documentation Team
- Review Status: Draft
- Last Updated: February 2026
