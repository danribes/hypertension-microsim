# Model Discrepancy Report: Python Microsimulation vs Excel Markov Model

**Date:** February 3, 2026
**Author:** Generated Analysis
**Models Compared:**
- Python Microsimulation: `src/` directory
- Excel Markov Model: `DANRIBES_HTN_Model.xlsx`

---

## Executive Summary

This report documents the discrepancies identified between the Python individual-level microsimulation model and the Excel cohort-level Markov model for cost-effectiveness analysis of IXA-001 (aldosterone synthase inhibitor) in resistant hypertension.

**Key Finding:** While both models target the same therapeutic scenario, they exhibit significant discrepancies in baseline event probabilities, risk equation implementation, and target population definition that could lead to materially different cost-effectiveness conclusions.

---

## Table of Contents

1. [Model Architecture Differences](#1-model-architecture-differences)
2. [Health State Discrepancies](#2-health-state-discrepancies)
3. [Transition Probability Discrepancies](#3-transition-probability-discrepancies)
4. [Risk Equation Discrepancies](#4-risk-equation-discrepancies)
5. [Population Parameter Discrepancies](#5-population-parameter-discrepancies)
6. [Treatment Effect Discrepancies](#6-treatment-effect-discrepancies)
7. [Cost Input Comparison](#7-cost-input-comparison)
8. [Utility Value Comparison](#8-utility-value-comparison)
9. [Summary of Critical Issues](#9-summary-of-critical-issues)
10. [Recommendations](#10-recommendations)

---

## 1. Model Architecture Differences

### Fundamental Approach

| Characteristic | Python Microsimulation | Excel Markov Model |
|----------------|------------------------|-------------------|
| **Model Type** | Individual-level Monte Carlo | Cohort-level state-transition |
| **Simulation Unit** | 1,000 individual patient objects | Population proportions (0-1) |
| **Cycle Length** | Monthly (1 month) | Annual (1 year) |
| **Time Horizon** | 480 months (40 years) | Lifetime (30+ years) |
| **Heterogeneity** | Patient-level variation captured | Assumes homogeneity within states |
| **Stochasticity** | Probabilistic sampling each cycle | Deterministic Markov transitions |
| **Memory** | Full patient history tracked | Markovian (memoryless) |

### Implications

1. **Heterogeneity Capture:** Python can model within-cohort variation in treatment response, adherence, and risk factor trajectories. Excel assumes all patients in a state have identical outcomes.

2. **Computational Approach:** Python requires Monte Carlo sampling with many iterations for stable estimates. Excel provides deterministic results but may miss tail risks.

3. **Cycle Length Impact:** Monthly cycles (Python) capture acute events and rapid renal transitions better than annual cycles (Excel), but Excel uses explicit tunnel states to handle Year 1 vs Year 2+ differences.

---

## 2. Health State Discrepancies

### States Present in Python but NOT in Excel

| State | Python Implementation | Clinical Relevance |
|-------|----------------------|-------------------|
| **Mild Cognitive Impairment (MCI)** | `NeuroState.MILD_COGNITIVE_IMPAIRMENT` | SPRINT-MIND evidence for intensive BP control |
| **Dementia** | `NeuroState.DEMENTIA` | Long-term cognitive outcome of HTN |
| **CKD Stage 3A vs 3B** | Separate `CKD_STAGE_3A`, `CKD_STAGE_3B` | Finer renal progression granularity |

### States Present in Excel but NOT in Python

| State | Excel Implementation | Clinical Relevance |
|-------|---------------------|-------------------|
| **TIA** | S9 (Transient Ischemic Attack) | Stroke warning event with conversion risk |
| **Angina/CHD (Acute)** | S4 (Acute Angina/CHD) | Symptomatic coronary disease onset |
| **Angina/CHD (Chronic)** | S5 (Chronic Angina/CHD) | Ongoing CHD management |
| **Hemorrhagic Stroke** | S7 (separate from ischemic) | Different outcomes and costs |
| **Kidney Transplant** | S13 (Post-transplant state) | ESRD treatment pathway |

### Structural Differences

| Aspect | Python | Excel |
|--------|--------|-------|
| **Tunnel States** | Implicit (time-based transition rates) | Explicit (S2 Year 1 → S3 Year 2+) |
| **Stroke Subtypes** | Combined as single stroke event | Ischemic (S6) vs Hemorrhagic (S7) |
| **Death States** | CV_DEATH, RENAL_DEATH (2 states) | D1 (CV), D2 (Renal), D3 (Other) - 3 states |
| **Concurrent States** | 3 parallel domains (cardiac, renal, neuro) | Single linear state at any time |

### Impact Assessment

**HIGH IMPACT:** The lack of cognitive decline modeling in Excel may undervalue long-term benefits of intensive BP control, particularly relevant given SPRINT-MIND evidence.

**MEDIUM IMPACT:** Excel's separation of hemorrhagic vs ischemic stroke allows for differential costs and outcomes (hemorrhagic has higher mortality and costs).

---

## 3. Transition Probability Discrepancies

### Baseline Event Rates (Monthly)

**Reference Patient:** Male, 60 years, SBP 150 mmHg, eGFR 75 mL/min/1.73m², no diabetes, no prior CV events

| Event | Python | Excel | Ratio | Annual Equivalent |
|-------|--------|-------|-------|-------------------|
| **Acute MI** | ~0.0050 | 0.0018 | **2.8x** | Python: 6.0%, Excel: 2.2% |
| **Ischemic Stroke** | ~0.0038 | 0.0012 | **3.2x** | Python: 4.6%, Excel: 1.4% |
| **Heart Failure** | ~0.0040 | 0.0015 | **2.7x** | Python: 4.8%, Excel: 1.8% |
| **CV Death** | ~0.0080 | 0.0008 | **10.0x** | Python: 9.6%, Excel: 1.0% |
| **CKD Progression** | ~0.0025 | 0.0025 | **1.0x** | Python: 3.0%, Excel: 3.0% |
| **Other-Cause Death** | ~0.0006 | 0.0006 | **1.0x** | Life tables aligned |

### Critical Discrepancy: CV Death Rate

```
Python CV Death:  0.008/month = 9.6%/year = ~65% 10-year mortality
Excel CV Death:   0.0008/month = 1.0%/year = ~10% 10-year mortality
```

**This 10x discrepancy is the most critical issue identified.** A 10-year CV mortality of 65% (Python) vs 10% (Excel) would produce dramatically different:
- Life years gained
- QALYs accrued
- Total costs
- Incremental cost-effectiveness ratios

### Post-Event Transition Rates

| Transition | Python | Excel | Status |
|------------|--------|-------|--------|
| Post-MI → Recurrent MI | 0.0045/month | 0.0045/month | **Aligned** |
| Post-Stroke → Recurrent Stroke | 0.0038/month | 0.0038/month | **Aligned** |
| Chronic HF → HF Rehospitalization | 0.025/month | 0.025/month | **Aligned** |
| CKD Stage 3 → Stage 4 | 0.0069/month | 0.0069/month | **Aligned** |
| CKD Stage 4 → ESRD | 0.0135/month | 0.0135/month | **Aligned** |

### Case Fatality Rates

| Event | Python | Excel | Status |
|-------|--------|-------|--------|
| Acute MI (30-day) | 8% | 7.5% | Similar |
| Acute Stroke (30-day) | 12% | 10% | Similar |
| Acute HF (30-day) | 5% | 12% | **Discrepant** |

---

## 4. Risk Equation Discrepancies

### PREVENT Equation Implementation

Both models cite AHA PREVENT (2024) equations (Khan et al., Circulation 2024) as the primary risk source, but implement them differently.

#### Python Implementation (`src/risks/prevent.py`)

```python
# Log-transformed coefficient form
def calculate_10_year_risk(patient):
    if patient.sex == 'female':
        xbeta = (0.976 * ln(age) +
                 1.008 * ln(sbp) +
                 0.693 * diabetes +
                 -0.127 * ln(egfr) + ...)
        risk = 1 - 0.9792 ** exp(xbeta - xbar)
    else:
        xbeta = (0.847 * ln(age) +
                 0.982 * ln(sbp) + ...)
        risk = 1 - 0.9712 ** exp(xbeta - xbar)
```

#### Excel Implementation (`Risk Equations` sheet)

```
# Appears to use linear coefficient form
Variable        β (Male)    β (Female)
Age             0.064       0.072
SBP (treated)   0.0174      0.0189
Total Chol      0.0089      0.0078
HDL-C          -0.0123     -0.0145
Diabetes        0.452       0.523
Smoking         0.389       0.412
eGFR           -0.0087     -0.0092
```

### Coefficient Comparison

| Variable | Python β | Excel β | Form |
|----------|----------|---------|------|
| Age | 0.976 / 0.847 | 0.072 / 0.064 | **Incompatible** |
| SBP | 1.008 / 0.982 | 0.0189 / 0.0174 | **Incompatible** |
| Diabetes | 0.693 | 0.523 / 0.452 | Different magnitude |
| eGFR | -0.127 | -0.0092 / -0.0087 | **Incompatible** |

### Interpretation

The coefficient magnitudes suggest:
- **Python:** Uses `ln(variable)` transformations, coefficients represent elasticities
- **Excel:** Uses untransformed variables, coefficients represent absolute effects

These are **mathematically incompatible** formulations of the same underlying model. This likely explains the 2-10x difference in baseline event rates.

### BP Reduction Risk Effects (More Aligned)

| Outcome | Python RRR per 10 mmHg | Excel RRR per 10 mmHg | Difference |
|---------|------------------------|----------------------|------------|
| MI | 22% | 20% | +2% |
| Stroke | 36% | 35% | +1% |
| Heart Failure | 28% | 25% | +3% |
| CV Death | 20% | 18% | +2% |
| CKD Progression | 15% | 19% | -4% |

The relative risk reductions are reasonably aligned, suggesting the treatment effect implementation is consistent even if baseline rates differ.

---

## 5. Population Parameter Discrepancies

### Baseline Demographics

| Parameter | Python | Excel | Discrepancy |
|-----------|--------|-------|-------------|
| **Age (mean)** | 62 years | ~60 years | Minor |
| **Age (SD)** | 10 years | Not specified | - |
| **Age (range)** | 40-85 years | Not specified | - |
| **Sex (% Female)** | 45% | ~50% | Minor |

### Clinical Parameters

| Parameter | Python | Excel | Discrepancy |
|-----------|--------|-------|-------------|
| **SBP (mean)** | 155 mmHg | ~150 mmHg | Minor |
| **SBP (SD)** | 15 mmHg | Not specified | - |
| **SBP (range)** | 140-200 mmHg | Not specified | - |
| **eGFR (mean)** | 68 mL/min/1.73m² | ~75 mL/min/1.73m² | **Moderate** |
| **eGFR (SD)** | 20 mL/min/1.73m² | Not specified | - |

### Comorbidity Prevalence

| Comorbidity | Python | Excel | Discrepancy |
|-------------|--------|-------|-------------|
| **Diabetes** | **35%** | **100%** | **CRITICAL** |
| **Prior MI** | 10% | Not specified | - |
| **Prior Stroke** | 5% | Not specified | - |
| **Heart Failure** | 8% | Not specified | - |
| **Atrial Fibrillation** | 12% | Not specified | - |
| **COPD** | 17-32% | Not specified | - |
| **Depression** | 27-50% | Not specified | - |

### Critical Population Discrepancy

**The Excel model assumes 100% Type 2 Diabetes prevalence**, indicating it was designed for a diabetic resistant hypertension population. The Python model uses 35% diabetes prevalence, representing a general resistant hypertension population.

This fundamentally changes:
1. Baseline CV risk (diabetes is a major risk factor)
2. Renal progression rates (diabetic nephropathy)
3. Generalizability of results
4. Target population for reimbursement decisions

---

## 6. Treatment Effect Discrepancies

### Blood Pressure Reduction

| Treatment | Python | Excel | Status |
|-----------|--------|-------|--------|
| **IXA-001 SBP reduction** | 20 mmHg (SD=8) | 20 mmHg (95% CI: 17-23) | **Aligned** |
| **Spironolactone SBP** | 9 mmHg (SD=6) | 10 mmHg (95% CI: 8-12) | Similar |
| **Standard Care SBP** | 3 mmHg (SD=5) | Not specified | - |

### Response Rates

| Parameter | Python | Excel | Discrepancy |
|-----------|--------|-------|-------------|
| **IXA-001 Response Rate** | Implicit (continuous) | 75% (95% CI: 70-80%) | Different approach |
| **Spironolactone Response** | Implicit (continuous) | 55% (95% CI: 48-62%) | Different approach |

Python models continuous BP reduction with individual variation. Excel uses explicit responder/non-responder classification.

### Discontinuation Rates

| Treatment | Python | Excel | Discrepancy |
|-----------|--------|-------|-------------|
| **IXA-001** | 8%/year | 12%/year | **-4%** |
| **Spironolactone** | 15%/year | 18%/year | **-3%** |

Lower discontinuation rates in Python would favor treatment continuation and cumulative benefits.

### Adverse Events

| Adverse Event | Python | Excel |
|---------------|--------|-------|
| Hyperkalemia monitoring | Included | Included |
| Gynecomastia (Spiro) | Not modeled | Included with disutility |
| AKI risk | Not modeled | Included |
| Treatment waning | Not modeled | Scenario analysis available |

---

## 7. Cost Input Comparison

### Drug Costs (Monthly)

| Treatment | Python (US) | Excel (US) | Status |
|-----------|-------------|------------|--------|
| IXA-001 | $500 | $500 | **Aligned** |
| Spironolactone | $15 | $15 | **Aligned** |
| Background therapy | $75 | ~$75 | **Aligned** |
| SGLT2 Inhibitor | $450 | Not shown | Python only |

### Acute Event Costs

| Event | Python (US) | Excel (US) | Status |
|-------|-------------|------------|--------|
| Acute MI | $25,000 | ~$25,000 | **Aligned** |
| Acute Stroke | $35,000 | ~$35,000 | **Aligned** |
| Acute HF Admission | $18,000 | ~$18,000 | **Aligned** |

### Annual State Costs

| State | Python (US) | Excel (US) | Status |
|-------|-------------|------------|--------|
| Controlled HTN | $800 | $800 | **Aligned** |
| Uncontrolled HTN | $1,200 | $1,200 | **Aligned** |
| Post-MI | $5,500 | $5,500 | **Aligned** |
| Post-Stroke | $12,000 | $12,000 | **Aligned** |
| Chronic HF | $15,000 | $15,000 | **Aligned** |
| CKD Stage 3A | $2,500 | $2,500 | **Aligned** |
| CKD Stage 4 | $8,000 | $8,000 | **Aligned** |
| ESRD | $90,000 | $90,000 | **Aligned** |

### Assessment

**Cost inputs are well-aligned between models.** This is a strength, as cost discrepancies are not contributing to potential differences in cost-effectiveness results.

---

## 8. Utility Value Comparison

### Health State Utilities

| State | Python | Excel | Difference |
|-------|--------|-------|------------|
| Baseline (age 60) | 0.84 | - | - |
| Controlled HTN | 0.80 | 0.85 | -0.05 |
| Uncontrolled HTN | 0.80 | 0.82 | -0.02 |
| Post-MI (Year 1) | - | 0.68 | Excel only |
| Post-MI (Year 2+) | 0.72 | 0.76 | -0.04 |
| Post-Stroke (Year 1) | - | 0.52 | Excel only |
| Post-Stroke (Year 2+) | 0.66 | 0.65 | +0.01 |
| Chronic HF | 0.69 | 0.65 | +0.04 |
| CKD Stage 3 | 0.76 | 0.78 | -0.02 |
| CKD Stage 4 | 0.68 | 0.70 | -0.02 |
| ESRD | 0.49 | 0.55 | -0.06 |

### Methodology Differences

| Aspect | Python | Excel |
|--------|--------|-------|
| **Approach** | Baseline - disutilities | Direct state utilities |
| **Year 1 distinction** | Implicit in rates | Explicit separate values |
| **Multiple conditions** | Additive disutilities | Single state value |
| **Age adjustment** | Age-specific baseline | Not specified |

### Assessment

Utility values are **reasonably aligned** (within 0.05 for most states). The main structural difference is Python's additive disutility approach vs Excel's direct state assignment.

---

## 9. Summary of Critical Issues

### Priority Classification

| Priority | Issue | Impact on ICER | Recommendation |
|----------|-------|----------------|----------------|
| 🔴 **CRITICAL** | CV death rate 10x discrepancy | Very High | Immediate investigation required |
| 🔴 **CRITICAL** | PREVENT coefficient forms incompatible | Very High | Verify original source implementation |
| 🔴 **CRITICAL** | Population diabetes prevalence (35% vs 100%) | High | Clarify target population |
| 🟡 **HIGH** | Baseline event rates 2-3x different | High | Reconcile with published epidemiology |
| 🟡 **HIGH** | Missing cognitive decline in Excel | Medium | Consider adding if SPRINT-MIND relevant |
| 🟡 **MEDIUM** | Discontinuation rates differ by 3-4% | Medium | Align to trial data |
| 🟢 **LOW** | Missing TIA/CHD states in Python | Low | Consider adding for completeness |
| 🟢 **LOW** | Utility differences of 0.02-0.06 | Low | Minor impact |

### Potential Impact on Cost-Effectiveness Results

If the Python model's higher event rates are correct:
- More events prevented by IXA-001
- Greater QALY gains
- Higher event-related cost offsets
- **More favorable ICER** for IXA-001

If the Excel model's lower event rates are correct:
- Fewer events to prevent
- Lower absolute benefit
- Less cost offset
- **Less favorable ICER** for IXA-001

---

## 10. Recommendations

### Immediate Actions

1. **Verify PREVENT Implementation**
   - Obtain original PREVENT equation code/spreadsheet from Khan et al.
   - Confirm coefficient forms (log vs linear)
   - Validate baseline survival parameters
   - Compare calculated 10-year risks to published validation cohorts

2. **Reconcile CV Death Rates**
   - Review Python's `transitions.py` CV mortality calculation
   - Check for compounding errors or unit mismatches
   - Validate against published resistant HTN mortality data (e.g., PATHWAY-2, SPRINT)

3. **Clarify Target Population**
   - Decision needed: General resistant HTN vs Diabetic resistant HTN
   - If general: Excel diabetes prevalence should be ~30-40%
   - If diabetic: Python should increase to ~100% diabetes

### Medium-Term Harmonization

4. **Structural Alignment**
   - Add tunnel states to Python for acute phase modeling
   - Add TIA and CHD states to Python
   - Consider adding cognitive decline to Excel

5. **Parameter Synchronization**
   - Align discontinuation rates to same trial source
   - Standardize representative patient for validation
   - Cross-validate both models against same external dataset

### Validation Approach

6. **External Validation**
   - Run both models with identical inputs
   - Compare predicted outcomes to:
     - PATHWAY-2 trial (spironolactone in resistant HTN)
     - SPRINT trial (intensive BP control)
     - Published CKD-CVD interaction cohorts

7. **Sensitivity Analysis**
   - Test ICER sensitivity to baseline event rates
   - Identify which parameters drive divergence
   - Document acceptable parameter ranges

---

## Appendix A: File References

### Python Model Files

| File | Purpose | Key Parameters |
|------|---------|----------------|
| `src/patient.py` | Patient data structure | Health states, attributes |
| `src/simulation.py` | Main simulation engine | Cycle length, time horizon |
| `src/transitions.py` | Event probabilities | Transition rates, case fatality |
| `src/treatment.py` | Treatment effects | SBP reduction, discontinuation |
| `src/costs/costs.py` | Cost parameters | Drug, event, state costs |
| `src/utilities.py` | QALY calculations | Baseline utilities, disutilities |
| `src/risks/prevent.py` | PREVENT equations | Risk coefficients |
| `src/risk_assessment.py` | Risk stratification | GCUA, KDIGO, Framingham |

### Excel Model Sheets

| Sheet | Purpose | Key Parameters |
|-------|---------|----------------|
| `Health States` | State definitions | 19 health states |
| `Transition Probabilities` | Event rates | Monthly transition matrix |
| `Risk Equations` | PREVENT implementation | Coefficients, calibration |
| `Cost Inputs` | US cost parameters | Drug, event, state costs |
| `Utility Inputs` | QALY parameters | State utilities |
| `Cohort Inputs` | Population definition | Demographics, comorbidities |
| `Markov IXA-001` | IXA-001 treatment arm | State flows |
| `Markov SoC` | Comparator arm | State flows |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **ICER** | Incremental Cost-Effectiveness Ratio ($/QALY) |
| **PREVENT** | Predicting Risk of CVD Events (AHA 2024 equations) |
| **RRR** | Relative Risk Reduction |
| **QALY** | Quality-Adjusted Life Year |
| **Tunnel State** | Temporary state with forced transition (e.g., Year 1 post-MI) |
| **eGFR** | Estimated Glomerular Filtration Rate |
| **CKD** | Chronic Kidney Disease |
| **ESRD** | End-Stage Renal Disease |
| **HTN** | Hypertension |

---

*Report generated: February 3, 2026*

---

## Appendix C: Harmonization Changes Applied (February 3, 2026)

Based on the instructions in `Based on the MODEL.docx`, the following changes were applied to harmonize the two models:

### Python Microsimulation Changes

| Change | File | Description |
|--------|------|-------------|
| **Split stroke types** | `src/patient.py`, `src/transitions.py` | Added `ACUTE_ISCHEMIC_STROKE` and `ACUTE_HEMORRHAGIC_STROKE` states with different case fatality rates (10% vs 25%) |
| **Add TIA state** | `src/patient.py`, `src/transitions.py` | Added `TIA` state with elevated subsequent stroke risk (2x multiplier) |
| **Fix CV mortality** | `src/transitions.py` | Changed from additive to multiplicative risk stacking; capped annual CV mortality at 25%; added probability sum check (≤95%) |
| **Update discontinuation** | `src/treatment.py` | IXA-001 discontinuation rate: 8% → 12% (aligned with Excel) |
| **Add stroke costs** | `src/costs/costs.py` | Added separate costs: Ischemic stroke $15,200, Hemorrhagic stroke $22,500, TIA $2,100 |

### Excel Model Changes

| Change | Sheet | Description |
|--------|-------|-------------|
| **Update diabetes prevalence** | `Cohort Inputs` | Changed from 100% to 35% (16 cells updated) |
| **Fix risk equations** | `Risk Equations` | Updated to log-transformed coefficient form matching Python model |
| **Add cognitive states** | `Health States`, `HTN Model Health States` | Added MCI (N1) and Dementia (N2) states with SPRINT-MIND evidence |

### Expected Impact on Results

After harmonization:
1. **CV Death Rates**: Should now be more aligned (~1-3% annual for base population vs previous 10x discrepancy)
2. **Population Risk**: Both models now use 35% diabetes prevalence (general resistant HTN population)
3. **Stroke Modeling**: Python now differentiates hemorrhagic (higher mortality/cost) from ischemic strokes
4. **Cognitive Benefits**: Both models can now capture long-term cognitive benefits of intensive BP control
5. **Treatment Effects**: Discontinuation rates aligned for fair comparison

### Files Modified

**Python Model:**
- `src/patient.py` - Added stroke subtypes, TIA, and tracking fields
- `src/transitions.py` - Updated probabilities, CV death calculation, event sampling
- `src/treatment.py` - Updated IXA-001 discontinuation rate
- `src/costs/costs.py` - Added stroke subtype and TIA costs

**Excel Model:**
- `DANRIBES_HTN_Model.xlsx` - Updated Cohort Inputs, Risk Equations, Health States sheets

---

*Harmonization completed: February 3, 2026*
