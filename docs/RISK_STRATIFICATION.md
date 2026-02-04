# Risk Stratification in the Hypertension Microsimulation Model

## Overview

The microsimulation model incorporates four risk stratification systems to classify patients at baseline. These systems provide clinical context and enable subgroup analysis but **do not directly modify simulation dynamics**.

> **Important**: As stated in `src/risk_assessment.py`: "These assessments are calculated once at baseline for each patient and used for subgroup analysis. They do NOT modify model dynamics."

The actual simulation uses **PREVENT risk equations** with direct patient characteristics to calculate monthly event probabilities.

---

## Risk Stratification Systems

### 1. Framingham CVD Risk Score

**Applied to**: All patients (universal)

**Purpose**: Provides 10-year cardiovascular disease risk estimate for comparison and baseline classification.

**Categories**:
| Category | 10-Year Risk |
|----------|--------------|
| Low | < 5% |
| Borderline | 5% - 7.5% |
| Intermediate | 7.5% - 20% |
| High | > 20% |

**Input Variables**:
- Age, Sex
- Total cholesterol, HDL cholesterol
- Systolic blood pressure (treated/untreated)
- Diabetes status
- Smoking status
- Social Deprivation Index (SDI) - adds 3 points if > 75
- Nocturnal SBP - adds 2 points if > 130 mmHg

---

### 2. KDIGO Risk Matrix

**Applied to**: Patients with eGFR ≤ 60 (CKD patients, any age)

**Purpose**: Classifies chronic kidney disease severity and progression risk using the KDIGO (Kidney Disease: Improving Global Outcomes) framework.

**Classification Axes**:

**GFR Categories**:
| Category | eGFR (mL/min/1.73m²) | Description |
|----------|----------------------|-------------|
| G1 | ≥ 90 | Normal or high |
| G2 | 60-89 | Mildly decreased |
| G3a | 45-59 | Mildly to moderately decreased |
| G3b | 30-44 | Moderately to severely decreased |
| G4 | 15-29 | Severely decreased |
| G5 | < 15 | Kidney failure |

**Albuminuria Categories**:
| Category | UACR (mg/g) | Description |
|----------|-------------|-------------|
| A1 | < 30 | Normal to mildly increased |
| A2 | 30-300 | Moderately increased |
| A3 | > 300 | Severely increased |

**Risk Matrix**:
|  | A1 | A2 | A3 |
|--|----|----|-----|
| **G1** | Low | Moderate | High |
| **G2** | Low | Moderate | High |
| **G3a** | Moderate | High | Very High |
| **G3b** | High | Very High | Very High |
| **G4** | Very High | Very High | Very High |
| **G5** | Very High | Very High | Very High |

---

### 3. GCUA (Geriatric Cardiorenal-Metabolic Unified Algorithm)

**Applied to**: Patients with Age ≥ 60 AND eGFR > 60

**Purpose**: Phenotypes geriatric patients without established CKD to identify those at risk for accelerated cardiorenal decline.

**Component Scores**:
1. **Nelson/CKD-PC Risk**: 5-year incident CKD risk
2. **Framingham CVD Risk**: 10-year cardiovascular risk
3. **Bansal Mortality Risk**: 5-year all-cause mortality risk

**Phenotypes**:
| Phenotype | Name | Criteria | Clinical Implication |
|-----------|------|----------|---------------------|
| **I** | Accelerated Ager | Nelson ≥15% AND CVD ≥20% | Highest risk - aggressive intervention needed |
| **II** | Silent Renal | Nelson ≥15% AND CVD <7.5% | Hidden renal risk - monitor kidney function |
| **III** | Vascular Dominant | Nelson <5% AND CVD ≥20% | Primary CV risk - standard CV prevention |
| **IV** | Senescent | Mortality ≥50% | Frailty/end-of-life considerations |
| **Moderate** | Moderate Risk | Nelson 5-15% | Intermediate monitoring |
| **Low** | Low Risk | None of above | Standard care |

---

### 4. EOCRI (Early-Onset Cardiorenal Risk Indicator)

**Applied to**: Patients with Age 18-59 AND eGFR > 60

**Purpose**: Identifies younger adults with preserved kidney function who have elevated cardiorenal risk, particularly "silent" renal risk that traditional Framingham scoring misses.

**Based on**: AHA PREVENT 30-year/lifetime CVD risk equations which explicitly include renal function (eGFR, UACR) as predictors.

**Key Discriminators**:
- Albuminuria status (UACR ≥ 30 mg/g = "Elevated")
- Metabolic burden (count of: diabetes, obesity, dyslipidemia, hypertension)
- PREVENT 30-year CVD risk percentage

**Phenotypes**:
| Phenotype | Name | Criteria | Treatment Trigger |
|-----------|------|----------|-------------------|
| **A** | Early Metabolic | Elevated UACR + (Diabetes OR Obesity) | Aggressive BP + SGLT2i + Statin |
| **B** | Silent Renal | Elevated UACR + No Diabetes | Early ASI/RAASi + SGLT2i |
| **C** | Premature Vascular | Normal UACR + (High Lipids OR Smoker) | Statins + Antiplatelets |
| **Low** | Low Risk | Normal UACR + No vascular risk factors | Standard HTN Management |

**Type B (Silent Renal)** is the key target population for EOCRI - these patients have:
- Low short-term CVD risk (would be classified as "low risk" by Framingham)
- High long-term renal progression risk (elevated albuminuria)
- Often missed by traditional risk algorithms

---

## Mutual Exclusivity of Renal Risk Types

GCUA, EOCRI, and KDIGO are **mutually exclusive** for renal risk classification. Each patient receives exactly one `renal_risk_type`:

```
                    ┌─────────────────────────────────────┐
                    │        Patient at Baseline          │
                    └─────────────────────────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │   eGFR > 60?    │
                            └─────────────────┘
                             /              \
                           Yes              No
                           /                  \
                          ▼                    ▼
                ┌─────────────────┐    ┌─────────────────┐
                │   Age ≥ 60?     │    │     KDIGO       │
                └─────────────────┘    │  (CKD pathway)  │
                 /              \      └─────────────────┘
               Yes              No
               /                  \
              ▼                    ▼
        ┌─────────────┐    ┌─────────────────┐
        │    GCUA     │    │     EOCRI       │
        │ (Geriatric) │    │  (Age 18-59)    │
        └─────────────┘    └─────────────────┘
```

**Framingham is always calculated** for all patients regardless of which renal risk pathway they follow.

---

## Summary Table

| System | Eligibility | Mutual Exclusivity | Primary Focus |
|--------|-------------|-------------------|---------------|
| **Framingham** | All patients | No (always applied) | 10-year CVD risk |
| **KDIGO** | eGFR ≤ 60 (any age) | Yes (renal_risk_type) | CKD progression |
| **GCUA** | Age ≥60 AND eGFR >60 | Yes (renal_risk_type) | Geriatric cardiorenal |
| **EOCRI** | Age 18-59 AND eGFR >60 | Yes (renal_risk_type) | Early-onset cardiorenal |

---

## What Actually Drives Simulation Dynamics?

The risk stratification scores are **not used** in the simulation engine. Instead, the model uses:

### 1. PREVENT Risk Calculator (`src/risks/prevent.py`)
Calculates monthly event probabilities using:
- Age, Sex
- Systolic blood pressure (true physiological, accounting for white coat effect)
- eGFR
- Diabetes status
- Smoking status
- Total cholesterol, HDL cholesterol
- BMI
- UACR (optional enhancement)

### 2. Prior Event Multipliers (`src/transitions.py`)
| Prior Event | Risk Multiplier |
|-------------|-----------------|
| MI | 2.5× |
| Stroke | 3.0× |
| TIA | 2.0× |
| Heart Failure | 2.0× |

### 3. Treatment Effects (`src/treatment.py`)
| Treatment | SBP Reduction | Monthly Cost |
|-----------|---------------|--------------|
| IXA-001 | 20 ± 8 mmHg | $500 |
| Spironolactone | 9 ± 6 mmHg | $15 |
| Standard Care | 3 ± 5 mmHg | $50 |

### 4. SGLT2 Inhibitor Effects
- Heart failure hospitalization: HR 0.70 (30% reduction)
- eGFR decline rate: 40% slower progression

### 5. Adherence Effects
- Non-adherent patients: 70% reduction in treatment effect (only 30% of benefit)

---

## Use Cases for Risk Stratification

Although risk scores don't modify dynamics, they serve important purposes:

1. **Subgroup Analysis**: Compare outcomes (costs, QALYs, events) across risk categories
2. **Population Characterization**: Describe the simulated population's risk profile
3. **Clinical Interpretation**: Map simulation results to real-world patient phenotypes
4. **Reporting**: Generate stratified results for regulatory/HTA submissions
5. **Validation**: Compare model population to trial/registry populations

---

## Code References

| Component | File | Key Functions |
|-----------|------|---------------|
| Risk calculations | `src/risk_assessment.py` | `calculate_framingham_risk()`, `calculate_kdigo_risk()`, `calculate_gcua_phenotype()`, `calculate_eocri_phenotype()` |
| Patient assignment | `src/population.py` | `PopulationGenerator.generate()` lines 350-404 |
| PREVENT equations | `src/risks/prevent.py` | `PREVENTRiskCalculator.get_monthly_event_prob()` |
| Transition probabilities | `src/transitions.py` | `TransitionCalculator.calculate_transitions()` |
| Subgroup analysis | `streamlit_app.py` | `analyze_subgroups()`, `display_subgroup_analysis()` |
