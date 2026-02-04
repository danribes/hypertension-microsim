# Risk Stratification in the Hypertension Microsimulation Model

## Overview

The microsimulation model incorporates four risk stratification systems to classify patients at baseline. These systems serve **two purposes**:

1. **Subgroup analysis and reporting** - Stratify outcomes by clinical phenotype
2. **Dynamic risk modification** - Phenotype-based multipliers that modify simulation event probabilities

> **Architecture**: The model uses a two-layer risk calculation:
> 1. **PREVENT equations** calculate base monthly event probabilities from patient characteristics
> 2. **Phenotype modifiers** adjust these probabilities based on baseline risk classification

This design preserves the clinical fidelity of PREVENT while allowing phenotype-specific risk trajectories.

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

## What Drives Simulation Dynamics?

The model uses a **layered risk calculation** that combines PREVENT equations with phenotype-specific modifiers:

### Layer 1: PREVENT Risk Calculator (`src/risks/prevent.py`)
Calculates **base** monthly event probabilities using:
- Age, Sex
- Systolic blood pressure (true physiological, accounting for white coat effect)
- eGFR
- Diabetes status
- Smoking status
- Total cholesterol, HDL cholesterol
- BMI
- UACR (optional enhancement)

### Layer 2: Phenotype Risk Modifiers (`src/risk_assessment.py`)

The `BaselineRiskProfile.get_dynamic_modifier()` method returns outcome-specific multipliers:

**GCUA Phenotypes (age ≥60, eGFR >60):**

| Phenotype | MI | Stroke | HF | ESRD | Death | Criteria | Clinical Rationale |
|-----------|-----|--------|-----|------|-------|----------|-------------------|
| **I** (Accelerated Ager) | 1.3× | 1.4× | 1.4× | 1.3× | 1.5× | Nelson ≥15% AND CVD ≥20% | High renal + High CV → multi-organ decline synergy |
| **II** (Silent Renal) | 0.9× | 0.95× | 1.1× | 1.4× | 1.2× | Nelson ≥15% AND CVD <7.5% | High renal + Low CV → renal-dominant, CV preserved |
| **III** (Vascular Dominant) | 1.4× | 1.5× | 1.2× | 0.8× | 1.3× | Nelson <5% AND CVD ≥20% | Low renal + High CV → atherosclerotic pathway, kidneys protected |
| **IV** (Senescent) | 1.8× | 2.0× | 2.2× | 1.5× | 2.5× | Mortality ≥50% | Frailty → high competing mortality, de-escalate treatment |
| **Moderate** | 1.1× | 1.1× | 1.15× | 1.15× | 1.1× | Nelson 5-15% | Intermediate renal risk |
| **Low** | 0.9× | 0.9× | 0.9× | 0.9× | 0.85× | None of above | Standard preventive care |

> **Note on GCUA III**: These patients have atherosclerotic disease (lipids, smoking) but relatively preserved kidney function. Their ESRD modifier is 0.8× (protective) while MI/Stroke are elevated 1.4-1.5×.

**EOCRI Phenotypes (age 18-59, eGFR >60):**

| Phenotype | MI | Stroke | HF | ESRD | Death | Criteria | Clinical Rationale |
|-----------|-----|--------|-----|------|-------|----------|-------------------|
| **A** (Early Metabolic) | 1.2× | 1.3× | 1.5× | 1.5× | 1.4× | Elevated uACR + (Diabetes OR Obesity) | Metabolic syndrome → accelerated dual CV/renal risk |
| **B** (Silent Renal) | 0.7× | 0.75× | 0.9× | **2.0×** | 1.1× | Elevated uACR + NO Diabetes | **KEY TARGET**: Low CV but high renal progression |
| **C** (Premature Vascular) | 1.6× | 1.7× | 1.3× | 0.8× | 1.2× | Normal uACR + (High Lipids OR Smoker) | Young atherosclerosis, kidneys protected |
| **Low** | 0.8× | 0.8× | 0.85× | 0.9× | 0.8× | Normal uACR + No vascular risk factors | Standard HTN management |

> **Note on EOCRI-B (Silent Renal)**: These patients are the **key value driver** for early intervention:
> - Would be classified as "low risk" by Framingham (low short-term CVD risk)
> - Have elevated albuminuria (uACR ≥30) indicating early kidney damage
> - 2× faster ESRD progression despite 0.7× MI risk
> - Target for early SGLT2i/RAASi therapy before overt CKD develops
>
> **Note on EOCRI-C (Premature Vascular)**: Opposite pattern from Type B:
> - High CV risk (MI 1.6×, Stroke 1.7×) from lipids/smoking
> - Protected kidneys (ESRD 0.8×) - no albuminuria
> - Target for aggressive statins and antiplatelet therapy

**KDIGO Risk Levels (eGFR ≤60, any age):**

The KDIGO risk matrix combines GFR category (G1-G5) and Albuminuria category (A1-A3):

| Risk Level | MI | Stroke | HF | ESRD | Death | GFR + Albuminuria Criteria | Clinical Profile |
|------------|-----|--------|-----|------|-------|---------------------------|-----------------|
| **Very High** | 1.4× | 1.5× | 1.6× | 1.8× | 2.0× | G4-G5 (any A) OR G3b+A2/A3 OR G3a+A3 | Advanced CKD, high CV burden |
| **High** | 1.2× | 1.3× | 1.4× | 1.5× | 1.5× | G3b+A1 OR G3a+A2 OR G1-G2+A3 | Moderate-severe CKD or severe albuminuria |
| **Moderate** | 1.1× | 1.1× | 1.2× | 1.2× | 1.1× | G3a+A1 OR G1-G2+A2 | Early CKD or moderate albuminuria |
| **Low** | 0.9× | 0.9× | 0.95× | 0.95× | 0.9× | G1-G2+A1 | Preserved function, minimal albuminuria |

**KDIGO Risk Matrix Reference:**
```
                    Albuminuria Category
                    A1 (<30)    A2 (30-300)   A3 (>300)
GFR Category
G1 (≥90)            Low         Moderate      High
G2 (60-89)          Low         Moderate      High
G3a (45-59)         Moderate    High          Very High
G3b (30-44)         High        Very High     Very High
G4 (15-29)          Very High   Very High     Very High
G5 (<15)            Very High   Very High     Very High
```

> **Note on KDIGO**: Unlike GCUA/EOCRI which are phenotype-based, KDIGO is a **severity-based** classification for established CKD. Higher risk levels reflect both CV burden (cardiorenal syndrome) and progression risk. The 2.0× mortality modifier for Very High reflects the poor prognosis of advanced CKD.

### Layer 3: Prior Event Multipliers (`src/transitions.py`)
| Prior Event | Risk Multiplier |
|-------------|-----------------|
| MI | 2.5× |
| Stroke | 3.0× |
| TIA | 2.0× |
| Heart Failure | 2.0× |

### Layer 4: Treatment Effects (`src/treatment.py`)
| Treatment | SBP Reduction | Monthly Cost |
|-----------|---------------|--------------|
| IXA-001 | 20 ± 8 mmHg | $500 |
| Spironolactone | 9 ± 6 mmHg | $15 |
| Standard Care | 3 ± 5 mmHg | $50 |

### Layer 5: SGLT2 Inhibitor Effects
- Heart failure hospitalization: HR 0.70 (30% reduction)
- eGFR decline rate: 40% slower progression

### Layer 6: Adherence Effects
- Non-adherent patients: 70% reduction in treatment effect (only 30% of benefit)

---

## Probability Calculation Flow

```
PREVENT Base Probability
        │
        ▼
  × Phenotype Modifier (GCUA/EOCRI/KDIGO)
        │
        ▼
  × Prior Event Multiplier (if applicable)
        │
        ▼
  × Treatment Effect (if applicable)
        │
        ▼
  × SGLT2i Effect (if applicable)
        │
        ▼
  Final Monthly Event Probability
```

---

## Use Cases for Risk Stratification

Risk stratification now serves both analytical and dynamic purposes:

### Dynamic Simulation Impact
1. **Phenotype-Specific Trajectories**: EOCRI-B patients experience 2× faster ESRD progression
2. **Risk-Adjusted Event Rates**: GCUA-IV patients have 2.5× higher mortality probability
3. **Treatment Response Heterogeneity**: Different phenotypes respond differently to interventions

### Analytical Purposes
1. **Subgroup Analysis**: Compare outcomes (costs, QALYs, events) across risk categories
2. **Population Characterization**: Describe the simulated population's risk profile
3. **Clinical Interpretation**: Map simulation results to real-world patient phenotypes
4. **Reporting**: Generate stratified results for regulatory/HTA submissions
5. **Validation**: Compare model population to trial/registry populations

### Clinical Decision Support
The phenotype modifiers enable the model to answer questions like:
- "How much more benefit does EOCRI-B (Silent Renal) get from early SGLT2i?"
- "What's the cost-effectiveness of aggressive treatment in GCUA-I vs GCUA-IV?"
- "Should we screen young adults for albuminuria to identify Type B patients?"

---

## Code References

| Component | File | Key Functions |
|-----------|------|---------------|
| Risk calculations | `src/risk_assessment.py` | `calculate_framingham_risk()`, `calculate_kdigo_risk()`, `calculate_gcua_phenotype()`, `calculate_eocri_phenotype()` |
| **Phenotype modifiers** | `src/risk_assessment.py` | `BaselineRiskProfile.get_dynamic_modifier()` |
| Patient assignment | `src/population.py` | `PopulationGenerator.generate()` lines 350-404 |
| PREVENT equations | `src/risks/prevent.py` | `PREVENTRiskCalculator.get_monthly_event_prob()` |
| **CV event transitions** | `src/transitions.py` | `TransitionCalculator.calculate_transitions()` - applies MI, Stroke, HF, Death modifiers |
| **Renal progression** | `src/patient.py` | `Patient._update_egfr()` - applies ESRD modifier |
| Subgroup analysis | `streamlit_app.py` | `analyze_subgroups()`, `display_subgroup_analysis()` |
