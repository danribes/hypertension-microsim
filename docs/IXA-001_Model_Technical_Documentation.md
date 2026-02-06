# IXA-001 Hypertension Microsimulation Model
## Comprehensive Technical Documentation

**Document Version:** 1.0
**Date:** February 2026
**Sponsor:** Atlantis Pharmaceuticals
**Prepared By:** HEOR Technical Documentation Team

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Model Overview](#2-model-overview)
3. [Dual Cardiac-Renal Pathway Interactions](#3-dual-cardiac-renal-pathway-interactions)
4. [Risk Equations](#4-risk-equations)
5. [Cost Inputs](#5-cost-inputs)
6. [Utility Values](#6-utility-values)
7. [Probabilistic Sensitivity Analysis](#7-probabilistic-sensitivity-analysis)
8. [Subgroup Analysis](#8-subgroup-analysis)
9. [Background Mortality](#9-background-mortality)
10. [Patient History Analysis](#10-patient-history-analysis)
11. [Model Validation](#11-model-validation)
12. [Results Summary](#12-results-summary)
13. [CHEERS 2022 Compliance](#13-cheers-2022-compliance)
14. [References](#14-references)
15. [Appendices](#15-appendices)

---

# 1. Executive Summary

## 1.1 Purpose

This document provides comprehensive technical documentation for the IXA-001 cost-effectiveness model, an individual-level state-transition microsimulation (IL-STM) evaluating the aldosterone synthase inhibitor IXA-001 versus spironolactone for resistant hypertension with secondary causes.

## 1.2 Model Summary

| Attribute | Specification |
|-----------|---------------|
| **Model Type** | Individual-level state-transition microsimulation |
| **Population** | Adults with resistant hypertension (N=1,000 per arm) |
| **Intervention** | IXA-001 (aldosterone synthase inhibitor) |
| **Comparator** | Spironolactone (mineralocorticoid receptor antagonist) |
| **Time Horizon** | 20 years (lifetime available) |
| **Cycle Length** | 1 month |
| **Perspective** | Healthcare system (base case), Societal (scenario) |
| **Discount Rate** | 3.0% costs, 3.0% outcomes |
| **Outcomes** | QALYs, costs, ICER, events prevented |

## 1.3 Key Results

| Subgroup | Incremental Cost | Incremental QALY | ICER ($/QALY) |
|----------|------------------|------------------|---------------|
| **Primary Aldosteronism** | +$20,550 | +0.084 | **$245,441** |
| OSA (severe) | +$25,200 | +0.081 | $311,111 |
| Renal Artery Stenosis | +$28,500 | +0.074 | $385,135 |
| Essential HTN | +$35,200 | -0.012 | Dominated |

**Primary Finding:** IXA-001 demonstrates optimal value in the **Primary Aldosteronism (PA) subgroup**, with the lowest ICER and highest clinical benefit due to mechanism-specific efficacy.

## 1.4 Documentation Structure

This master document consolidates 8 detailed technical reports:

| # | Report | Section | Detailed Report |
|---|--------|---------|-----------------|
| 1 | Risk Equations | [Section 4](#4-risk-equations) | `risk_equations_technical_report.md` |
| 2 | Cost Inputs | [Section 5](#5-cost-inputs) | `cost_inputs_technical_report.md` |
| 3 | Utility Values | [Section 6](#6-utility-values) | `utility_values_technical_report.md` |
| 4 | PSA Parameters | [Section 7](#7-probabilistic-sensitivity-analysis) | `psa_parameters_technical_report.md` |
| 5 | Subgroup Analysis | [Section 8](#8-subgroup-analysis) | `subgroup_analysis_methodology.md` |
| 6 | Background Mortality | [Section 9](#9-background-mortality) | `background_mortality_technical_note.md` |
| 7 | History Analyzer | [Section 10](#10-patient-history-analysis) | `history_analyzer_technical_note.md` |
| 8 | Model Validation | [Section 11](#11-model-validation) | `model_validation_report.md` |

---

# 2. Model Overview

## 2.1 Conceptual Framework

The model implements a dual-pathway cardiorenal microsimulation capturing:
- **Cardiovascular pathway**: MI, stroke, heart failure, atrial fibrillation, CV death
- **Renal pathway**: CKD progression (stages 1-5), ESRD, dialysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IXA-001 MICROSIMULATION STRUCTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PATIENT ENTRY                                                              │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BASELINE STRATIFICATION                          │   │
│  │  • Secondary HTN etiology (PA, RAS, Pheo, OSA, Essential)          │   │
│  │  • Age-based phenotype (EOCRI <60, GCUA ≥60, KDIGO if CKD)        │   │
│  │  • PREVENT 10-year CVD risk                                         │   │
│  │  • KFRE 2-year kidney failure risk                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    MONTHLY SIMULATION CYCLE                          │   │
│  │                                                                      │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │   │
│  │  │ CV Events    │    │ Renal        │    │ Background   │          │   │
│  │  │ • MI         │    │ Progression  │    │ Mortality    │          │   │
│  │  │ • Stroke     │    │ • eGFR       │    │ • Life       │          │   │
│  │  │ • HF         │    │   decline    │    │   tables     │          │   │
│  │  │ • AF         │    │ • ESRD       │    │              │          │   │
│  │  │ • CV Death   │    │              │    │              │          │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘          │   │
│  │         │                   │                   │                   │   │
│  │         └───────────────────┴───────────────────┘                   │   │
│  │                             │                                       │   │
│  │                             ▼                                       │   │
│  │                    OUTCOME ACCRUAL                                  │   │
│  │                    • Costs (direct + indirect)                      │   │
│  │                    • QALYs (utility × survival)                     │   │
│  │                    • Events (tracked by type)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  DEATH or END OF HORIZON                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Health States

### Cardiovascular States
| State | Description | Transitions From |
|-------|-------------|------------------|
| No Acute Event | Baseline CV state | Entry, Post-event recovery |
| Acute MI | Month of MI occurrence | No Acute Event, Post-MI |
| Post-MI | Chronic post-MI state | Acute MI |
| Acute Stroke | Month of stroke | No Acute Event, Post-Stroke |
| Post-Stroke | Chronic post-stroke | Acute Stroke |
| Acute HF | HF hospitalization | No Acute Event, Chronic HF |
| Chronic HF | Stable heart failure | Acute HF |
| Atrial Fibrillation | New-onset or chronic AF | Any non-death state |
| CV Death | Absorbing state | Any state |

### Renal States
| State | eGFR Range | KDIGO Stage |
|-------|------------|-------------|
| CKD Stage 1-2 | ≥60 mL/min/1.73m² | G1-G2 |
| CKD Stage 3a | 45-59 | G3a |
| CKD Stage 3b | 30-44 | G3b |
| CKD Stage 4 | 15-29 | G4 |
| ESRD | <15 or dialysis | G5 |

## 2.3 Treatment Effects

| Treatment | SBP Reduction | PA Response Modifier | Essential HTN Modifier |
|-----------|---------------|---------------------|------------------------|
| **IXA-001** | 20 mmHg | 1.70× | 1.00× |
| **Spironolactone** | 9 mmHg | 1.40× | 1.00× |
| Background therapy | 15 mmHg | N/A | N/A |

**Code Reference:** `src/risk_assessment.py:346-480`

---

# 3. Dual Cardiac-Renal Pathway Interactions

*This section documents how the model handles patients with simultaneous cardiac comorbidities and renal complications.*

## 3.1 Concurrent State Tracking

The model implements a **dual-branch state tracking system** where cardiac and renal states are tracked independently and simultaneously. A patient can occupy any combination of cardiac and renal states (e.g., Post-MI + CKD Stage 4).

| Dimension | States | Code Reference |
|-----------|--------|----------------|
| **Cardiac** | No Acute Event, Acute MI, Post-MI, Acute Stroke, Post-Stroke, Acute HF, Chronic HF, AF, CV Death | `src/patient.py:44-62` |
| **Renal** | CKD Stage 1-2, Stage 3a, Stage 3b, Stage 4, ESRD | `src/patient.py:64-71` |
| **Cognitive** | Normal, MCI, Dementia | `src/patient.py:73-76` |

## 3.2 Cross-Pathway Interactions

### 3.2.1 Modelled Interactions

| Interaction | Direction | Mechanism | Code Reference |
|-------------|-----------|-----------|----------------|
| **eGFR in PREVENT risk** | Renal → Cardiac | Lower eGFR increases 10-year CVD risk via PREVENT equation coefficients | `src/risks/prevent.py:45-156` |
| **ESRD CV mortality** | Renal → Cardiac | ESRD adds 9% annual incremental CV death risk (60% of ESRD mortality is CV-mediated) | `src/transitions.py:645-648` |
| **SGLT2i renal protection** | Cardiac → Renal | Patients with HF receive SGLT2i (40% uptake), which slows eGFR decline by 40% | `src/patient.py:484-491` |
| **SGLT2i cardiac protection** | Renal → Cardiac | Patients with CKD receive SGLT2i, which reduces HF hospitalization risk by 30% | `src/transitions.py:562-575` |
| **Hyperkalemia management** | Renal → Treatment | Rising K+ in renal dysfunction triggers stepped MRA management (binder → dose reduce → stop) | `src/treatment.py:260-347` |
| **Additive cost accrual** | Both | Monthly costs = cardiac state cost + renal state cost + drug costs | `src/costs/costs.py:463-514` |
| **Additive utility decrements** | Both | QALYs reflect combined disutilities from cardiac and renal states | `src/utilities.py` |

### 3.2.2 Not Currently Modelled

| Limitation | Clinical Relevance | Potential Impact |
|------------|-------------------|-----------------|
| **Acute kidney injury (AKI)** | Post-MI cardiogenic shock causes AKI in ~20% of cases | May underestimate renal costs post-cardiac event |
| **Cardiorenal syndrome (CRS)** | Type 1-4 CRS feedback loops between heart and kidney | Bidirectional organ damage not captured dynamically |
| **Treatment escalation for dual burden** | No logic to intensify renoprotection when cardiac patient develops CKD | Treatment decisions remain BP-driven only |
| **Cross-event time dependencies** | Stroke risk elevated for 12 months post-MI | Events treated as independent within each cycle |
| **Differential SBP targets** | CKD-4+ patients may warrant lower BP targets | All patients share the same target (<140 mmHg) |
| **ACEi/ARB for RAS subgroup** | RAS identified but no differential treatment pathway | May underestimate benefit of targeted RAS treatment |

### 3.2.3 Treatment for Dual-Burden Patients

Currently, treatment decisions are **BP-driven only** (`src/treatment.py`):

- **Intensify** if SBP > 130 mmHg (with 50% clinical inertia probability)
- **No consideration** of simultaneous cardiac + renal states when escalating or de-escalating treatment
- **SGLT2i** is the only agent providing explicit dual-pathway benefit (cardiac + renal)
- **Hyperkalemia management** is the only renal-aware treatment adjustment (stepped approach for MRA patients with rising K+)

**Code Reference:** `src/treatment.py:225-246` (`should_intensify_treatment()`)

## 3.3 SGLT2 Inhibitor as Dual-Benefit Agent

SGLT2 inhibitors represent the primary cross-pathway treatment mechanism in the model:

| Property | Value | Source |
|----------|-------|--------|
| **Assignment criteria** | eGFR < 60 OR heart failure present | Population generation |
| **Real-world uptake** | 40% | Clinical practice data |
| **Renal benefit** | 40% reduction in eGFR decline rate | DAPA-CKD (Heerspink 2020) |
| **Cardiac benefit** | 30% reduction in HF hospitalization | DAPA-HF (McMurray 2019) |
| **Monthly cost (US)** | $450 | WAC pricing |
| **Monthly cost (UK)** | £35 | BNF pricing |

**Code References:**
- Assignment logic: `src/population.py:388-397`
- Renal protection: `src/patient.py:484-491`
- Cardiac protection: `src/transitions.py:562-575`

## 3.4 Cost Structure for Dual-Burden Patients

Costs are calculated **additively** across pathways:

```
Total Monthly Cost = Cardiac State Cost + Renal State Cost + Drug Cost + SGLT2i + Monitoring

Example: Post-MI + CKD Stage 4 + PA patient on IXA-001
  Post-MI management:    $458/month ($5,500/year)
  CKD Stage 4:           $667/month ($8,000/year)
  IXA-001:               $500/month
  SGLT2i:                $450/month
  Standard care:          $75/month
  ─────────────────────────────────────────────────
  Total:               $2,150/month ($25,800/year)
```

**Code Reference:** `src/costs/costs.py:463-514` (`get_total_cost()`)

## 3.5 Implications for Cost-Effectiveness

Dual cardiac-renal burden patients represent the **highest-cost subgroup** and therefore the greatest opportunity for cost offsets from effective treatment:

1. **PA patients** with concurrent CKD have both elevated cardiac risk (2.05× HF) and accelerated renal decline (1.80× ESRD), making them the primary value driver for IXA-001
2. **SGLT2i co-prescription** provides dual benefits that partially offset costs in both pathways
3. **Event cost savings** from prevented MI, stroke, HF, and AF are amplified in dual-burden patients due to higher baseline event rates

---

# 4. Risk Equations

*Detailed report: `risk_equations_technical_report.md`*

## 4.1 AHA PREVENT Equations

The model uses the 2024 AHA PREVENT equations for 10-year CVD risk:

$$\text{Risk}_{10yr} = 1 - S_0(t)^{\exp(\beta \cdot X - \bar{X})}$$

### Coefficients (Female)

| Variable | Coefficient (β) | Reference Mean |
|----------|-----------------|----------------|
| Age | 0.0634 | 55.0 |
| SBP (treated) | 0.0180 | 130.0 |
| Total Cholesterol | 0.0045 | 200.0 |
| HDL Cholesterol | -0.0267 | 55.0 |
| eGFR | -0.0089 | 85.0 |
| log(UACR) | 0.1250 | 2.3 |
| Diabetes | 0.4200 | 0.12 |
| Current Smoker | 0.5100 | 0.15 |
| BMI | 0.0156 | 28.0 |

**Baseline Survival:** S₀(10) = 0.9680

### Probability Conversion

```
Annual: p_annual = 1 - (1 - p_10yr)^(1/10)
Monthly: p_monthly = 1 - (1 - p_annual)^(1/12)
```

**Code Reference:** `src/risks/prevent.py:45-156`

## 4.2 Kidney Failure Risk Equation (KFRE)

4-variable KFRE for 2-year kidney failure risk:

$$\text{Risk}_{2yr} = 1 - 0.9750^{\exp(\text{Linear Predictor} - 7.222)}$$

| Variable | Coefficient |
|----------|-------------|
| Age | -0.2201 |
| Sex (male=1) | 0.2467 |
| eGFR | -0.5567 |
| log(UACR) | 0.4510 |

**Applicability:** eGFR 15-59 mL/min/1.73m²

**Code Reference:** `src/risks/kfre.py:28-95`

## 4.3 Risk Ratio per 10 mmHg SBP Reduction

| Outcome | Risk Ratio | 95% CI | Source |
|---------|------------|--------|--------|
| MI | 0.78 | 0.70-0.86 | Ettehad 2016 |
| Stroke | 0.64 | 0.57-0.72 | Ettehad 2016 |
| Heart Failure | 0.72 | 0.65-0.80 | Ettehad 2016 |
| CV Death | 0.75 | 0.67-0.84 | Ettehad 2016 |
| ESRD | 0.80 | 0.68-0.94 | Xie 2016 |
| Atrial Fibrillation | 0.82 | 0.72-0.94 | Okin 2015 |

---

# 5. Cost Inputs

*Detailed report: `cost_inputs_technical_report.md`*

## 5.1 Drug Costs (US$ 2024)

| Drug | Monthly Cost | Annual Cost | Source |
|------|--------------|-------------|--------|
| IXA-001 | $500 | $6,000 | Assumed launch price |
| Spironolactone | $15 | $180 | NADAC 2024 |
| Background therapy | $75 | $900 | NADAC 2024 |

## 5.2 Acute Event Costs

| Event | Cost | PSA Distribution | Source |
|-------|------|------------------|--------|
| Myocardial Infarction | $25,000 | Gamma(25, 1000) | HCUP 2022 |
| Ischemic Stroke | $15,200 | Gamma(15.2, 1000) | HCUP 2022 |
| Hemorrhagic Stroke | $22,000 | Gamma(22, 1000) | HCUP 2022 |
| Heart Failure | $18,000 | Gamma(18, 1000) | HCUP 2022 |
| Atrial Fibrillation | $8,500 | Gamma(8.5, 1000) | HCUP 2022 |
| Hyperkalemia | $12,000 | Gamma(12, 1000) | HCUP 2022 |
| ESRD Initiation | $35,000 | Gamma(35, 1000) | USRDS 2023 |

## 5.3 Chronic Management Costs (Annual)

| Condition | Annual Cost | Source |
|-----------|-------------|--------|
| Post-MI | $8,000 | Medicare claims |
| Post-Stroke | $12,000 | Medicare claims |
| Chronic HF | $15,000 | Medicare claims |
| CKD Stage 3 | $4,500 | Medicare claims |
| CKD Stage 4 | $8,000 | Medicare claims |
| ESRD (dialysis) | $90,000 | USRDS 2023 |
| Chronic AF | $8,500 | Medicare claims |

## 5.4 Indirect Costs (Societal Perspective)

| Event | Productivity Loss | Duration | Total |
|-------|-------------------|----------|-------|
| MI | $4,500/month | 3 months | $13,500 |
| Stroke | $6,000/month | 6 months | $36,000 |
| HF Hospitalization | $3,500/month | 2 months | $7,000 |
| ESRD | $2,500/month | Ongoing | $30,000/year |

**Code Reference:** `src/costs/costs.py:45-180`

---

# 6. Utility Values

*Detailed report: `utility_values_technical_report.md`*

## 6.1 Baseline Utilities by Age

| Age | Male | Female | Source |
|-----|------|--------|--------|
| 40 | 0.88 | 0.86 | Sullivan 2011 |
| 50 | 0.86 | 0.84 | Sullivan 2011 |
| 60 | 0.83 | 0.80 | Sullivan 2011 |
| 70 | 0.79 | 0.76 | Sullivan 2011 |
| 80 | 0.74 | 0.70 | Sullivan 2011 |

## 6.2 Health State Utilities

| State | Utility | PSA Distribution | Source |
|-------|---------|------------------|--------|
| Post-MI | 0.88 | Beta(70.4, 9.6) | NICE DSU TSD 12 |
| Post-Stroke | 0.82 | Beta(65.6, 14.4) | NICE DSU TSD 12 |
| Chronic HF | 0.85 | Beta(68, 12) | NICE DSU TSD 12 |
| CKD Stage 3 | 0.90 | Beta(72, 8) | Gorodetskaya 2005 |
| CKD Stage 4 | 0.80 | Beta(64, 16) | Gorodetskaya 2005 |
| ESRD | 0.65 | Beta(52, 28) | Gorodetskaya 2005 |
| Atrial Fibrillation | 0.90 | Beta(72, 8) | NICE AF guidelines |

## 6.3 Disutility Decrements

| Event/State | Disutility | Duration | Source |
|-------------|------------|----------|--------|
| Acute MI | 0.15 | 1 month | Sullivan 2011 |
| Chronic Post-MI | 0.12 | Permanent | Sullivan 2011 |
| Acute Stroke | 0.30 | 1 month | Sullivan 2011 |
| Chronic Post-Stroke | 0.18 | Permanent | Sullivan 2011 |
| Chronic HF | 0.15 | Permanent | Sullivan 2011 |
| ESRD | 0.35 | Permanent | Gorodetskaya 2005 |
| Hyperkalemia | 0.05 | 1 month | Assumed |

## 6.4 QALY Calculation

$$\text{QALY}_t = \text{Utility}_t \times \text{Survival}_t \times \frac{1}{(1+r)^t}$$

- Half-cycle correction applied
- Discount rate: 3.0% annually
- Additive disutility model for comorbidities

**Code Reference:** `src/utilities.py:25-145`

---

# 7. Probabilistic Sensitivity Analysis

*Detailed report: `psa_parameters_technical_report.md`*

## 7.1 Parameter Summary

| Category | Count | Distribution Types |
|----------|-------|-------------------|
| Treatment Effects | 5 | Normal |
| Risk Ratios | 6 | Lognormal |
| Phenotype Modifiers | 7 | Lognormal |
| PA Risk Modifiers | 6 | Lognormal |
| Acute Costs | 7 | Gamma |
| Chronic Costs | 8 | Gamma |
| Utilities | 8 | Beta |
| Disutilities | 8 | Beta |
| **Total** | **47** | - |

## 7.2 Key Parameter Distributions

### Treatment Effects
| Parameter | Distribution | Mean | SD |
|-----------|--------------|------|-----|
| IXA-001 SBP reduction | Normal | 20 mmHg | 2.0 |
| Spironolactone SBP reduction | Normal | 9 mmHg | 1.5 |

### Risk Ratios (per 10 mmHg)
| Parameter | Distribution | Median | σ |
|-----------|--------------|--------|---|
| RR MI | Lognormal | 0.78 | 0.05 |
| RR Stroke | Lognormal | 0.64 | 0.06 |
| RR HF | Lognormal | 0.72 | 0.05 |

### PA Risk Modifiers
| Parameter | Distribution | Mean | σ |
|-----------|--------------|------|---|
| PA HF modifier | Lognormal | 2.05 | 0.12 |
| PA AF modifier | Lognormal | 3.0 | 0.20 |
| PA ESRD modifier | Lognormal | 1.80 | 0.15 |

## 7.3 Correlation Structure

Four correlation groups with Cholesky decomposition:

1. **Acute Costs**: MI, Stroke, HF, AF, ESRD (ρ = 0.30-0.60)
2. **Utilities**: Post-MI, Post-Stroke, CHF, ESRD, AF (ρ = 0.45-0.70)
3. **Risk Ratios**: MI, Stroke, HF, Death, AF (ρ = 0.50-0.80)
4. **Disutilities**: All event disutilities (ρ = 0.40-0.65)

## 7.4 Convergence

| Metric | Recommendation |
|--------|----------------|
| Base case iterations | 1,000 |
| Subgroup analyses | 2,000 |
| Monte Carlo SE target | <2% of mean |

**Code Reference:** `src/psa.py:45-698`

---

# 8. Subgroup Analysis

*Detailed report: `subgroup_analysis_methodology.md`*

## 8.1 Pre-Specified Subgroups

### Dimension 1: Secondary HTN Etiology
| Subgroup | Prevalence | IXA-001 Response | Baseline Risk Modifier (HF) |
|----------|------------|------------------|----------------------------|
| Primary Aldosteronism | 15-20% | 1.70× | 2.05× |
| Renal Artery Stenosis | 5-15% | 1.05× | 1.45× |
| Pheochromocytoma | 0.5-1% | 0.40× | 1.70× |
| OSA (severe) | 10-15% | 1.20× | 1.28× |
| Essential HTN | 50-60% | 1.00× | 1.00× |

### Dimension 2: Age-Based Phenotype
| Phenotype | Age Range | eGFR | Key Risk Profile |
|-----------|-----------|------|-----------------|
| EOCRI Type A | 18-59 | >60 | Early Metabolic |
| EOCRI Type B | 18-59 | >60 | Silent Renal (KEY TARGET) |
| EOCRI Type C | 18-59 | >60 | Premature Vascular |
| GCUA Type I | ≥60 | >60 | Accelerated Ager |
| GCUA Type II | ≥60 | >60 | Silent Renal |
| GCUA Type III | ≥60 | >60 | Vascular Dominant |
| GCUA Type IV | ≥60 | >60 | Senescent |
| KDIGO | Any | ≤60 | CKD pathway |

## 8.2 Subgroup Results Summary

| Subgroup | N | Δ Cost | Δ QALY | ICER | Events Prevented (per 1000) |
|----------|---|--------|--------|------|----------------------------|
| **Primary Aldosteronism** | 180 | +$20,550 | +0.084 | $245,441 | MI:12, Stroke:15, HF:28, AF:33 |
| OSA (severe) | 120 | +$25,200 | +0.081 | $311,111 | MI:8, Stroke:10, HF:15, AF:12 |
| RAS | 85 | +$28,500 | +0.074 | $385,135 | MI:6, Stroke:8, HF:12, ESRD:10 |
| Essential HTN | 500 | +$35,200 | -0.012 | Dominated | MI:2, Stroke:3, HF:4, AF:3 |

## 8.3 Value-Based Prescribing Recommendation

```
┌─────────────────────────────────────────────────────────────────┐
│                TREATMENT SELECTION ALGORITHM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  IF Primary Aldosteronism CONFIRMED:                           │
│     → IXA-001 RECOMMENDED (ICER $245K, best value)             │
│                                                                 │
│  IF OSA with Severe AHI + CPAP-intolerant:                     │
│     → IXA-001 CONSIDER (ICER $311K, moderate value)            │
│                                                                 │
│  IF RAS or Pheochromocytoma:                                   │
│     → Address primary etiology first                           │
│     → IXA-001 LIMITED VALUE                                    │
│                                                                 │
│  IF Essential/Unexplained Resistant HTN:                       │
│     → Spironolactone PREFERRED (IXA-001 dominated)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Code Reference:** `src/risk_assessment.py:146-480`

---

# 9. Background Mortality

*Detailed report: `background_mortality_technical_note.md`*

## 9.1 Life Table Sources

| Country | Source | Year | Age Resolution |
|---------|--------|------|----------------|
| United States | SSA Actuarial Life Tables | 2021 | Single-year |
| United Kingdom | ONS National Life Tables | 2020-2022 | 5-year intervals |

## 9.2 Selected Mortality Rates (US)

| Age | Male qx | Female qx | Male:Female Ratio |
|-----|---------|-----------|-------------------|
| 50 | 0.00485 | 0.00349 | 1.39 |
| 60 | 0.01152 | 0.00829 | 1.39 |
| 65 | 0.01743 | 0.01272 | 1.37 |
| 70 | 0.02679 | 0.02000 | 1.34 |
| 80 | 0.06653 | 0.05386 | 1.24 |

## 9.3 Probability Conversions

**Annual to Monthly:**
$$p_{month} = 1 - (1 - p_{year})^{1/12}$$

**Example (65-year-old male):**
- Annual qx = 0.01743
- Monthly = 1 - (1 - 0.01743)^(1/12) = 0.001463

## 9.4 Competing Risks Framework

```
Total Mortality = Background + CV Deaths + Renal Deaths

Adjusted Background = Life Table × (1 - CV_Fraction - Renal_Fraction)
                    = Life Table × (1 - 0.28 - 0.03)
                    = Life Table × 0.69
```

**Code Reference:** `src/risks/life_tables.py:94-297`

---

# 10. Patient History Analysis

*Detailed report: `history_analyzer_technical_note.md`*

## 10.1 Dynamic Risk Modifiers

The PatientHistoryAnalyzer leverages full patient trajectories to modify risk:

| Modifier Type | Range | Key Drivers |
|---------------|-------|-------------|
| CVD Risk | 0.5× - 5.0× | Prior events, clustering, comorbidities |
| Renal Progression | 0.6× - 2.0× | eGFR trajectory, albuminuria |
| Mortality | 1.0× - 4.0× | Charlson score, COPD, SUD |
| Adherence | 0.3× - 1.0× | Mental health, substance use |

## 10.2 Trajectory Classification

### eGFR Trajectories
| Type | Annual Decline | Modifier | Prevalence |
|------|---------------|----------|------------|
| Rapid Decliner | >3 mL/min/yr | 1.5× | 17% |
| Normal Decliner | 1-3 mL/min/yr | 1.0× | 45% |
| Slow Decliner | 0.5-1 mL/min/yr | 0.8× | 23% |
| Stable | <0.5 mL/min/yr | 0.6× | 15% |

### BP Control Quality
| Grade | Average SBP | CVD Modifier |
|-------|-------------|--------------|
| Excellent | <130 mmHg | 0.85× |
| Good | 130-139 mmHg | 1.00× |
| Fair | 140-149 mmHg | 1.20× |
| Poor | ≥150 mmHg | 1.50× |

## 10.3 Time-Decay Function

Prior event risk decays exponentially:

$$\text{Modifier} = 1.0 + (\text{Excess Risk}) \times e^{-0.05 \times \text{months}}$$

| Time Since MI | Residual Risk |
|---------------|---------------|
| 0 months | 1.50× |
| 12 months | 1.27× |
| 24 months | 1.15× |
| 60 months | 1.02× |

**Code Reference:** `src/history_analyzer.py:42-502`

---

# 11. Model Validation

*Detailed report: `model_validation_report.md`*

## 11.1 Validation Framework

| Validation Type | Status | Method |
|-----------------|--------|--------|
| Face Validity | ✓ Pass | Expert review, conceptual model |
| Verification | ✓ Pass | 76 unit tests, 100% pass rate |
| Internal Validity | ✓ Pass | Extreme value testing, mass balance |
| External Validity | ✓ Pass | Calibration to published data |
| Cross-Validation | ✓ Pass | ICER/NICE model comparison |
| Predictive Validity | Pending | Phase III data comparison |

## 11.2 Unit Test Coverage

| Module | Tests | Pass Rate |
|--------|-------|-----------|
| PREVENT Equations | 12 | 100% |
| KFRE Calculator | 8 | 100% |
| Life Tables | 6 | 100% |
| Cost Module | 10 | 100% |
| Utilities | 8 | 100% |
| PSA Sampling | 12 | 100% |
| Transitions | 14 | 100% |
| Population | 6 | 100% |
| **Total** | **76** | **100%** |

## 11.3 External Calibration

| Outcome | Model Prediction | Published Data | Source |
|---------|-----------------|----------------|--------|
| 10-yr MI risk (high risk) | 8.2% | 7.5-9.0% | Framingham |
| 10-yr Stroke risk | 4.1% | 3.8-4.5% | ARIC |
| 5-yr ESRD (CKD G4) | 18.5% | 17-21% | CKD-PC |
| Life expectancy (65M) | 17.1 yrs | 17.4 yrs | SSA 2021 |

## 11.4 Cross-Validation

| Comparator Model | Agreement | Notes |
|------------------|-----------|-------|
| ICER CVD Model | High | Similar PREVENT implementation |
| NICE HTN Model | Moderate | Different risk equations |
| Published CEAs | High | ICERs within expected range |

**Code Reference:** `tests/*.py`

---

# 12. Results Summary

## 12.1 Base Case Results (20-Year, PA Subgroup)

| Outcome | IXA-001 | Spironolactone | Difference |
|---------|---------|----------------|------------|
| Total Costs | $142,550 | $122,000 | +$20,550 |
| Total QALYs | 11.284 | 11.200 | +0.084 |
| Life Years | 14.52 | 14.38 | +0.14 |
| **ICER** | - | - | **$245,441/QALY** |

## 12.2 Events Prevented (PA Subgroup, per 1,000)

| Event | IXA-001 | Spironolactone | Prevented |
|-------|---------|----------------|-----------|
| MI | 45 | 57 | 12 |
| Stroke | 38 | 53 | 15 |
| Heart Failure | 82 | 110 | **28** |
| ESRD | 65 | 83 | 18 |
| Atrial Fibrillation | 120 | 153 | **33** |
| CV Death | 28 | 36 | 8 |

## 12.3 Cost-Effectiveness Acceptability

| WTP Threshold | P(Cost-Effective) - PA | P(Cost-Effective) - Overall |
|---------------|------------------------|------------------------------|
| $100,000/QALY | 8% | 2% |
| $150,000/QALY | 15% | 5% |
| $200,000/QALY | 35% | 12% |
| $300,000/QALY | 65% | 28% |

## 12.4 Threshold Pricing

| Subgroup | Current Price | Price at $150K WTP | Reduction Needed |
|----------|---------------|-------------------|------------------|
| Primary Aldosteronism | $500/mo | $467/mo | 6.7% |
| OSA (severe) | $500/mo | $385/mo | 23% |
| RAS | $500/mo | $290/mo | 42% |
| Essential HTN | $500/mo | N/A | Not cost-effective |

---

# 13. CHEERS 2022 Compliance

| Item | Requirement | Status | Documentation |
|------|-------------|--------|---------------|
| 1 | Title | ✓ | This document |
| 2 | Abstract | ✓ | Executive Summary |
| 3 | Background/Objectives | ✓ | Section 1 |
| 4 | Target Population | ✓ | Section 2 |
| 5 | Setting/Location | ✓ | Section 2 |
| 6 | Comparators | ✓ | Section 2 |
| 7 | Time Horizon | ✓ | Section 2 |
| 8 | Discount Rate | ✓ | Section 6 |
| 9 | Health Outcomes | ✓ | Section 6 |
| 10 | Costs | ✓ | Section 5 |
| 11 | Analytic Methods | ✓ | Section 2-4 |
| 12 | Measurement of Outcomes | ✓ | Section 6 |
| 13 | Valuation of Outcomes | ✓ | Section 6 |
| 14 | Valuation Methods | ✓ | Section 6 |
| 15 | Resource Estimation | ✓ | Section 5 |
| 16 | Unit Costs | ✓ | Section 5 |
| 17 | Productivity Costs | ✓ | Section 5 |
| 18 | Effect Estimation | ✓ | Section 4 |
| 19 | Uncertainty Methods | ✓ | Section 7 |
| 20 | Uncertainty Parameters | ✓ | Section 7 |
| 21 | Heterogeneity | ✓ | Section 8 |
| 22 | Model Validation | ✓ | Section 11 |

**Compliance: 22/22 items (100%)**

---

# 14. References

1. Khan SS, et al. Development and Validation of the American Heart Association's PREVENT Equations. Circulation. 2024;149:430-449.

2. Tangri N, et al. A predictive model for progression of chronic kidney disease to kidney failure. JAMA. 2011;305(15):1553-1559.

3. Ettehad D, et al. Blood pressure lowering for prevention of cardiovascular disease and death: a systematic review and meta-analysis. Lancet. 2016;387:957-67.

4. Monticone S, et al. Cardiovascular events and target organ damage in primary aldosteronism compared with essential hypertension. Lancet Diabetes Endocrinol. 2018;6:41-50.

5. Sullivan PW, Ghushchyan V. Preference-Based EQ-5D Index Scores for Chronic Conditions in the United States. Med Decis Making. 2006;26:410-20.

6. Gorodetskaya I, et al. Health-related quality of life and estimates of utility in chronic kidney disease. Kidney Int. 2005;68:2801-2808.

7. Arias E, Xu J. United States Life Tables, 2021. National Vital Statistics Reports. 2023;72(12):1-64.

8. HCUP National Inpatient Sample. Healthcare Cost and Utilization Project. Agency for Healthcare Research and Quality. 2022.

9. United States Renal Data System. 2023 USRDS Annual Data Report. National Institutes of Health, NIDDK. 2023.

10. Briggs A, Sculpher M, Claxton K. Decision Modelling for Health Economic Evaluation. Oxford University Press. 2006.

---

# 15. Appendices

## Appendix A: Detailed Technical Reports

| Report | File | Pages |
|--------|------|-------|
| Risk Equations | `risk_equations_technical_report.md` | ~35 |
| Cost Inputs | `cost_inputs_technical_report.md` | ~40 |
| Utility Values | `utility_values_technical_report.md` | ~35 |
| Model Validation | `model_validation_report.md` | ~50 |
| PSA Parameters | `psa_parameters_technical_report.md` | ~25 |
| Subgroup Analysis | `subgroup_analysis_methodology.md` | ~30 |
| Background Mortality | `background_mortality_technical_note.md` | ~15 |
| History Analyzer | `history_analyzer_technical_note.md` | ~20 |

## Appendix B: Code Reference Map

| Component | Primary File | Key Functions |
|-----------|--------------|---------------|
| Simulation Engine | `src/simulation.py` | `run_simulation()`, `CEAResults` |
| PREVENT Equations | `src/risks/prevent.py` | `calculate_10yr_risk()` |
| KFRE Calculator | `src/risks/kfre.py` | `calculate_2yr_risk()` |
| Life Tables | `src/risks/life_tables.py` | `LifeTableCalculator` |
| Costs | `src/costs/costs.py` | `CostInputs`, `calculate_costs()` |
| Utilities | `src/utilities.py` | `calculate_qaly()` |
| PSA | `src/psa.py` | `PSAIteration`, `CholeskySampler` |
| Risk Assessment | `src/risk_assessment.py` | `BaselineRiskProfile` |
| History Analyzer | `src/history_analyzer.py` | `PatientHistoryAnalyzer` |
| Population | `src/population.py` | `PopulationGenerator` |
| Transitions | `src/transitions.py` | `*Transition` classes |

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **ASI** | Aldosterone Synthase Inhibitor (IXA-001) |
| **CKD** | Chronic Kidney Disease |
| **EOCRI** | Early-Onset Cardiorenal Risk Indicator (age 18-59) |
| **ESRD** | End-Stage Renal Disease |
| **GCUA** | Geriatric Cardiorenal-Metabolic Unified Algorithm (age ≥60) |
| **ICER** | Incremental Cost-Effectiveness Ratio |
| **IL-STM** | Individual-Level State-Transition Microsimulation |
| **KFRE** | Kidney Failure Risk Equation |
| **MRA** | Mineralocorticoid Receptor Antagonist (spironolactone) |
| **PA** | Primary Aldosteronism |
| **PREVENT** | AHA Predicting Risk of CVD Events equations |
| **PSA** | Probabilistic Sensitivity Analysis |
| **QALY** | Quality-Adjusted Life Year |
| **RAS** | Renal Artery Stenosis |
| **WTP** | Willingness-to-Pay threshold |

---

**Document Control**

| Field | Value |
|-------|-------|
| Document ID | IXA-001-CEA-TechDoc-v1.0 |
| Version | 1.0 |
| Status | Final |
| Author | HEOR Technical Documentation Team |
| Reviewer | [Pending] |
| Approval | [Pending] |
| Date | February 2026 |

---

*End of Document*
