# Hypertension Cardiorenal Microsimulation Model

A state-of-the-art **Individual-Level State-Transition Microsimulation (IL-STM)** for pharmacoeconomic evaluation of hypertension treatments in patients with cardiorenal disease. This model implements advanced features including dynamic blood pressure modeling, enhanced eGFR decline equations, and three-dimensional baseline risk stratification.

---

## Quick Start with Docker

The fastest way to run the Cost-Effectiveness Analysis (CEA) web interface.

### Prerequisites

| Platform | Requirements |
|----------|-------------|
| **macOS** | [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) |
| **Windows** | [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) with WSL 2 backend |
| **Linux** | [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) |

### Run with Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd hypertension_microsim

# Start the application
docker compose up

# Access the web interface at http://localhost:8502
```

To stop: `Ctrl+C` or `docker compose down`

### Alternative: Docker Run

```bash
# Build the image
docker build -t hypertension-microsim .

# Run the container
docker run -p 8502:8501 hypertension-microsim

# Access the web interface at http://localhost:8502
```

### Web Interface Features

The Streamlit interface provides:

- **Interactive Parameters**: Cohort size, time horizon, cost perspective (US/UK)
- **Key Metrics**: Incremental costs, QALYs, ICER with interpretation
- **Outcomes Table**: Comprehensive comparison of events and costs
- **Event Charts**: Visual comparison of cardiac and renal events
- **CE Plane**: Cost-effectiveness quadrant analysis
- **WTP Analysis**: Net monetary benefit at various thresholds

---

## Table of Contents

- [Quick Start with Docker](#quick-start-with-docker)
- [Overview](#overview)
- [Key Features](#key-features)
- [Microsimulation vs. Markov Models](#microsimulation-vs-markov-models)
- [Model Structure](#model-structure)
- [Population Definition](#population-definition)
- [Disease Progression Models](#disease-progression-models)
- [Baseline Risk Stratification](#baseline-risk-stratification)
- [Patient History Analyzer](#patient-history-analyzer)
- [Economic Evaluation](#economic-evaluation)
- [Technical Implementation](#technical-implementation)
- [Usage](#usage)
- [References](#references)

---

## Overview

This model simulates the **lifetime progression** of hypertensive patients through **dual disease branches** (cardiac and renal), evaluating the cost-effectiveness of novel antihypertensive treatments against standard care. It implements cutting-edge methodologies from health economics and clinical research to provide robust pharmacoeconomic evidence for reimbursement decisions.

**Model Type:** Individual-Level State-Transition Microsimulation (IL-STM)  
**Cycle Length:** Monthly (to capture acute events and rapid renal transitions)  
**Time Horizon:** Lifetime (up to age 100)  
**Perspective:** Healthcare payer  
**Discount Rate:** 3% per annum (costs and QALYs)

---

## Key Features

### 1. **Individual-Level State-Transition Model (IL-STM)**

Unlike cohort-level Markov models, this microsimulation tracks **each patient individually** through time, enabling:

- **Patient history tracking:** Prior MI, stroke, time since events
- **Continuous risk factors:** Exact eGFR, SBP, age (not discretized into health states)
- **Treatment adherence:** Individual-level compliance tracking
- **Memory effects:** Risk depends on full patient trajectory, not just current state

### 2. **Dual Disease Branch Architecture**

Patients simultaneously progress through **independent cardiac and renal pathways**:

**Cardiac Branch:**
```
No Acute Event → [MI, Stroke, PAD] → Chronic HF → Death (Cardiac)
                      ↓ (recurrent)
                Post-MI/Stroke/PAD
```

**Renal Branch:**
```
CKD Stage 1-2 → Stage 3a → Stage 3b → Stage 4 → ESRD → Death (Renal)
    (eGFR ≥60)   (45-59)   (30-44)   (15-29)  (<15)
```

### 3. **Dynamic Systolic Blood Pressure (SBP) Model**

**Stochastic monthly updates** reflecting real-world BP variability:

```
SBP(t+1) = SBP(t) + β_age + ε - treatment_effect

Where:
  β_age = 0.05 mmHg/month (age-related drift)
  ε ~ N(0, 2 mmHg)        (stochastic variation)
  treatment_effect        (medication-specific reduction)
```

**Advantages:**
- Captures **biological variability** in BP over time
- Enables **treatment response heterogeneity** across patients
- Supports **adherence modeling** (BP rebounds if non-adherent)

### 4. **Enhanced eGFR Decline Model**

**Continuous decline equation** with multiple risk factors:

```
Δ_eGFR_monthly = base_decline_age * diabetes_multiplier * BP_continuous_effect

Where:
  base_decline_age = {0.5 (age <50), 0.8 (50-65), 1.2 (65-75), 1.8 (75+)} / 12
  diabetes_multiplier = 1.5 if diabetic, else 1.0
  BP_continuous_effect = 1 + 0.05 * max(0, SBP - 140)
```

**Advantages over categorical models:**
- **Smooth transitions** (no artificial threshold effects)
- **SBP-kidney interaction** (every 1 mmHg above 140 accelerates decline)
- **Age stratification** (faster decline in elderly)

### 5. **Four-Dimensional Baseline Risk Stratification**

Every patient is classified at baseline across **four risk dimensions** using a dual-branch age-based architecture:

#### A. **Renal Risk (Mutually Exclusive Pathways)**

The model routes patients to one of three renal risk systems based on age and eGFR:

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

**GCUA Phenotypes** (age ≥60, eGFR > 60):
- **Type I (Accelerated Ager):** High renal + High CVD risk
- **Type II (Silent Renal):** High renal + Low CVD risk (missed by Framingham)
- **Type III (Vascular Dominant):** Low renal + High CVD risk
- **Type IV (Senescent):** High mortality risk (de-escalate treatment)
- **Moderate/Low:** Standard preventive care

**EOCRI Phenotypes** (age 18-59, eGFR > 60) - *NEW*:
- **Type A (Early Metabolic):** Elevated uACR + Diabetes/Obesity → Aggressive BP + SGLT2i + Statin
- **Type B (Silent Renal):** Elevated uACR + No Diabetes → Early ASI/RAASi + SGLT2i *(key target population)*
- **Type C (Premature Vascular):** Normal uACR + High Lipids/Smoker → Statins + Antiplatelets
- **Low Risk:** Normal uACR + No vascular risk factors → Standard HTN Management

> **Note:** EOCRI Type B patients are the key value driver - they have low short-term CVD risk (would be classified as "low risk" by Framingham) but high long-term renal progression risk due to elevated albuminuria.

**KDIGO Risk Matrix** (eGFR ≤ 60, any age):
```
           A1 (<30)   A2 (30-300)   A3 (>300)
G1 (≥90)     Low       Moderate        High
G2 (60-89)   Low       Moderate        High
G3a (45-59)  Moderate  High            Very High
G3b (30-44)  High      Very High       Very High
G4 (15-29)   Very High Very High       Very High
G5 (<15)     Very High Very High       Very High
```

#### B. **Cardiovascular Risk (All Patients)**

**Framingham 10-Year CVD Risk:**
- Low (<5%)
- Borderline (5-7.4%)
- Intermediate (7.5-19.9%)
- High (≥20%)

#### C. **Purpose**

Enables **subgroup cost-effectiveness analysis**:
- "Is IXA-001 cost-effective specifically in Silent Renal patients?"
- "What's the ICER for KDIGO Very High Risk subgroup?"
- "Do high Framingham patients benefit more?"
- "How do EOCRI Type B (younger silent renal) patients compare to GCUA Type II?"

---

### How Event Probabilities Are Actually Assigned

> **Critical Distinction**: The risk stratification systems above (Framingham, KDIGO, GCUA, EOCRI) are calculated **once at baseline** for classification and subgroup analysis. They do **NOT** directly drive simulation dynamics.

The actual monthly event probabilities are calculated using the **PREVENT Risk Calculator** with real-time patient characteristics:

#### PREVENT Risk Calculator (`src/risks/prevent.py`)

The AHA PREVENT equations calculate 10-year CVD risk using:

| Input Variable | Description |
|----------------|-------------|
| Age | Patient age (30-79 years) |
| Sex | Male/Female (separate coefficients) |
| Systolic BP | True physiological SBP (accounting for white coat effect) |
| eGFR | Current kidney function (mL/min/1.73m²) |
| Diabetes | Binary indicator |
| Smoking | Current smoking status |
| Total Cholesterol | mg/dL |
| HDL Cholesterol | mg/dL |
| BMI | Body mass index |
| UACR | Urine albumin-creatinine ratio (optional enhancement) |

**Conversion to Monthly Probabilities:**
```
10-year risk → Annual risk → Monthly probability
p_annual = 1 - (1 - p_10yr)^0.1
p_monthly = 1 - (1 - p_annual)^(1/12)
```

#### Prior Event Multipliers (`src/transitions.py`)

Patients with prior cardiovascular events have elevated risk:

| Prior Event | Risk Multiplier |
|-------------|-----------------|
| MI | 2.5× |
| Stroke | 3.0× |
| TIA | 2.0× |
| Heart Failure | 2.0× |

#### Treatment Effects on Risk (`src/treatment.py`)

Blood pressure reduction translates to risk reduction via meta-analysis-derived relative risks:

| Outcome | RR per 10 mmHg SBP Reduction |
|---------|------------------------------|
| Stroke | 0.64 (36% reduction) |
| MI | 0.78 (22% reduction) |
| Heart Failure | 0.72 (28% reduction) |
| Total CVD | 0.75 (25% reduction) |

**Example Calculation:**
```
Patient: 65yo male, SBP 160, eGFR 55, diabetic, smoker
PREVENT 10-year CVD risk: 28%
Prior MI multiplier: 2.5×
Adjusted 10-year risk: 70% (capped)
Monthly probability: ~0.95%

With IXA-001 treatment (20 mmHg reduction):
RR = 0.75^2 = 0.56 (44% reduction)
Adjusted monthly probability: ~0.53%
```

#### SGLT2 Inhibitor Effects

For CKD/HF patients on SGLT2 inhibitors:
- **Heart failure hospitalization**: HR 0.70 (30% reduction)
- **eGFR decline rate**: 40% slower progression

#### Adherence Effects

Non-adherent patients receive only 30% of treatment benefit:
```
effective_sbp_reduction = nominal_reduction × 0.30
```

---

#### Why This Architecture?

| Risk Stratification (Baseline) | PREVENT Equations (Monthly) |
|-------------------------------|----------------------------|
| Calculated once at start | Recalculated every month |
| For classification/subgroups | For actual event probabilities |
| Based on phenotype algorithms | Based on current patient state |
| Enables post-hoc analysis | Drives simulation dynamics |

This separation allows:
1. **Clinically meaningful subgroups** for reporting without artificially constraining the simulation
2. **Dynamic risk** that responds to treatment effects, disease progression, and aging
3. **Transparent validation** - compare population risk profiles to trial enrollments

---

### 6. **Patient History Analyzer**

**Dynamic risk modification** based on complete patient history:

**Key Capabilities:**
- **eGFR Trajectory Classification**: Rapid (>3 mL/min/year), Normal, Slow, or Stable decliner
- **Event Clustering Detection**: 3+ CV events in 60 months → 1.8x CVD risk
- **Time-Since-Event Decay**: Post-MI risk declines exponentially (e^(-0.05×months))
- **BP Control Quality**: Excellent (<130) to Poor (≥150) classification
- **Comorbidity Burden**: Charlson Index + mental health/substance use impacts

**Risk Modifiers:**
```python
# CVD Risk Modifier example:
# Patient: Prior MI + COPD + untreated depression + poor BP control
modifier = 1.5 (prior MI) × 1.5 (COPD) × 1.3 (depression) × 1.5 (poor BP)
         = 4.4x baseline Framingham risk

# Adherence Modifier:
# Patient: Substance use disorder
adherence_prob = 0.75 (baseline) × 0.5 (substance use) = 37.5%
```

**Advantage:** Microsimulation-unique capability - Markov models cannot use patient history

### 7. **Cognitive & Behavioral Enhancements (Phase 3)**

**A. Dementia & Cognitive Decline (Class 1A Outcome):**
- Tracks **Normal → MCI → Dementia** progression based on **SPRINT-MIND** trial data.
- **Key Mechanism:** Risk multipliers for **Age** (doubles every 5y >65) and **Cumulative SBP Burden** (>120 mmHg).
- **Impact:** Captures the neuroprotective benefits of intensive BP control beyond standard CV outcomes.

**B. White Coat Hypertension (WCH) Model:**
- **Physiological vs. Clinical Divergence:** Distinguishes between:
  - `current_sbp` (Office BP): Drivers treatment decisions (titration).
  - `true_mean_sbp` (Home/Physiological BP): Drivers biological risk (MI/Stroke/Neuro).
- **Mechanism:** ~20% of hypertensives have an "error term" (mean +15mmHg) added to their Office BP.
- **Result:** Correctly penalizes "overtreatment" of WCH patients who appear uncontrolled but have lower physiological risk.

**C. Clinical Inertia (Provider Behavior):**
- **Real-World Friction:** Providers do not always follow guidelines perfectly.
- **Mechanism:** **50% probability of failure to titrate** medications even when BP > 130/80 (after 3-6 months), reflecting "therapeutic inertia."
- **Benefit:** Realistically models the value of "set-and-forget" therapies (e.g., ASIs, SPCs) vs. labor-intensive titration regimens.

### 8. **SGLT2 Inhibitor Integration (Option F)**

**Class 1A Guideline Therapy** for CKD and Heart Failure:
- **Logic:** High-risk patients (CKD eGFR < 60 or Heart Failure) have a 40% uptake probability (GDMT).
- **Clinical Benefit:**
  - **HF Hospitalization:** Risk reduced by **30%** (HR 0.70).
  - **Renal Protection:** Annual eGFR decline slowed by **40%** (HR 0.60 on slope).
- **Economic Impact:** Incorporates brand-name costs ($450 US) vs. generic (~£35 UK).

### 9. **Safety Rules & Potassium Monitoring (Option H)**

**Mitigating MRA-induced Hyperkalemia:**
- **K+ Tracking:** Patient serum potassium modeled with stochastic drift influenced by eGFR and MRA use.
- **Safety Stop:** Automatic discontinuation of Spironolactone if K+ > 5.5 mmol/L.
- **Monitoring Burden:** Adds quarterly serum potassium lab costs ($15 US / £3 UK) for patients on MRAs.
- **Result:** Provides a realistic safety-benefit tradeoff for mineralocorticoid receptor antagonists.

---

## Microsimulation vs. Markov Models

### Why Microsimulation is Superior for This Application

| Feature | **Markov Cohort Model** | **Individual-Level Microsimulation** |
|---------|-------------------------|--------------------------------------|
| **Patient Heterogeneity** | Limited (must discretize into states) | **Full heterogeneity** captured (exact age, eGFR, SBP) |
| **History Dependence** | Memory-less (except tunnel states) | **Complete patient history** tracked |
| **Continuous Variables** | Must categorize (e.g., SBP 140-160) | **Exact continuous values** (e.g., SBP = 147.3) |
| **Subgroup Analysis** | Requires separate models | **Native support** via baseline stratification |
| **Time-Varying Covariates** | Complex to implement | **Natural implementation** (e.g., SBP changes each cycle) |
| **Treatment Adherence** | Population-level average | **Individual-level** compliance patterns |
| **Event Interactions** | Must pre-specify in state structure | **Emergent from patient characteristics** |
| **Stochastic Variation** | Second-order uncertainty only | **First-order variability** in patient trajectories |

### Specific Advantages for Scenario Analysis

#### 1. **Subpopulation Analysis Without Additional Models**

**Markov Approach:**
```
Separate model runs needed for each subgroup:
- Model 1: Age 60-70, eGFR 45-59, SBP 140-160
- Model 2: Age 60-70, eGFR 45-59, SBP 160-180
- ... (exponential explosion of scenarios)
```

**Microsimulation Approach:**
```python
# Single model run, stratify results post-hoc
results_silent_renal = filter(patients, 
    lambda p: p.baseline_risk_profile.gcua_phenotype == "II")
results_high_fram = filter(patients,
    lambda p: p.baseline_risk_profile.framingham_category == "High")
```

#### 2. **Treatment Response Heterogeneity**

**Markov:** Average treatment effect applied to all patients uniformly

**Microsimulation:** Treatment effect varies by individual characteristics:
```python
# Example: Treatment effect depends on baseline SBP
if patient.baseline_sbp >= 180:
    treatment_effect = 25  # Greater response in severe HTN
elif patient.baseline_sbp >= 160:
    treatment_effect = 20
else:
    treatment_effect = 15
```

#### 3. **Adherence Modeling**

**Markov:** Population-level adherence (e.g., 75% average)

**Microsimulation:** Individual adherence trajectories:
```python
# Each patient has adherence probability
if not patient.is_adherent:
    # BP rebounds without treatment
    patient.sbp += 5  # Loss of treatment effect
```

#### 4. **Interaction Effects**

**Markov:** Must explicitly code all state interactions (combinatorial explosion)

**Microsimulation:** Interactions emerge naturally:
```python
# Example: Diabetes accelerates eGFR decline, which is faster with high BP
decline = base_rate * (1.5 if diabetic else 1.0) * (1 + 0.05 * max(0, SBP-140))
```

#### 5. **Time-Since-Event Effects**

**Markov:** Requires tunnel states (complex, limited)

**Microsimulation:** Direct tracking:
```python
patient.time_since_last_cv_event  # Exact months since MI/stroke
# Risk decreases as time increases
recurrent_risk *= exp(-0.05 * patient.time_since_last_cv_event)
```

### When to Use Each Approach

**Use Markov Models When:**
- Simple disease structure with few health states
- Population-level averages are sufficient
- No need for subgroup analysis
- Computational speed is critical
- Regulatory requirement for cohort models

**Use Microsimulation When:**
- Complex patient heterogeneity
- Multiple interacting risk factors
- Subgroup/scenario analysis required
- Time-varying covariates (e.g., dynamic BP)
- Treatment adherence is important
- **Precision medicine / targeted therapies** (this model!)

---

## Model Structure

### Workflow: Population → Simulation → Analysis

```
1. POPULATION GENERATION
   ┌─────────────────────────────────────────────┐
   │ PopulationGenerator                         │
   │  - Sample demographics (age, sex, BMI)      │
   │  - Sample risk factors (eGFR, SBP, lipids)  │
   │  - Assign comorbidities (diabetes, CVD)     │
   │  - Calculate baseline risk profiles         │
   │    * GCUA phenotypes (if age 60+, eGFR>60)  │
   │    * KDIGO risk matrix (if CKD)             │
   │    * Framingham CVD risk (all)              │
   └─────────────────────────────────────────────┘
                      ↓
2. SIMULATION LOOP (Monthly Cycles)
   ┌─────────────────────────────────────────────┐
   │ For each patient, each month:               │
   │                                             │
   │  A. Check for events                        │
   │     - Cardiovascular (MI, stroke, HF)       │
   │     - Renal progression (eGFR thresholds)   │
   │     - Death (CVD, renal, other)             │
   │                                             │
   │  B. Accrue outcomes                         │
   │     - State-specific costs                  │
   │     - State-specific utilities              │
   │                                             │
   │  C. Update patient state                    │
   │     - Dynamic SBP equation                  │
   │     - eGFR decline equation                 │
   │     - Age increments                        │
   │     - Treatment effects                     │
   │                                             │
   │  D. Advance time                            │
   └─────────────────────────────────────────────┘
                      ↓
3. RESULTS AGGREGATION
   ┌─────────────────────────────────────────────┐
   │ - Calculate mean QALYs, costs per patient   │
   │ - Compute ICER (treatment vs. comparator)   │
   │ - Stratify by baseline risk profiles        │
   │ - Generate cost-effectiveness tables        │
   │ - Perform sensitivity analyses              │
   └─────────────────────────────────────────────┘
```

---

## Population Definition

### Baseline Characteristics

Patients are generated with **correlated sampling** to maintain realistic relationships:

| Parameter | Distribution | Mean | SD | Range |
|-----------|-------------|------|-----|-------|
| **Age** | Truncated Normal | 62 | 10 | 40-85 |
| **Sex (% Male)** | Bernoulli | 55% | - | - |
| **Systolic BP** | Normal + Age Effect | 155 | 15 | 140-200 |
| **Diastolic BP** | Correlated (0.6×SBP) | 92 | 10 | 60-120 |
| **eGFR** | Normal - Age Effect | 68 | 20 | 15-120 |
| **Albumin/Creat (uACR)** | Log-Normal | 50 | 80 | 1-3000 |
| **Total Cholesterol** | Normal | 200 | 40 | 120-350 |
| **HDL Cholesterol** | Normal | 48 | 12 | 20-100 |
| **BMI** | Normal | 30.5 | 5.5 | 18-55 |

### Comorbidity Prevalence

#### Traditional Cardiovascular/Metabolic

| Condition | Prevalence | Correlations |
|-----------|------------|--------------|
| **Diabetes** | 35% | ↑ with BMI, age |
| **Dyslipidemia** | 60% | Random |
| **Current Smoker** | 15% | Random |
| **Prior MI** | 10% | ↑ with age, diabetes |
| **Prior Stroke** | 5% | ↑ with age, diabetes |
| **Heart Failure** | 8% | ↑ with age, diabetes |

#### Comprehensive Comorbidity Tracking (NEW)

| Condition | Prevalence | Correlations | Impact |
|-----------|------------|--------------|--------|
| **COPD** | 17-32% | ↑ with smoking (+15%) | 1.5x CVD, 2.5x mortality (if severe) |
| **Depression** | 27-50% | ↑ in young females, diabetics | 1.3x CVD, 0.7x adherence (untreated) |
| **Anxiety** | 17-40% | ↑ with depression (comorbid) | 0.85x adherence |
| **Substance Use** | 10% | Random | 1.8x CVD, 2.0x mortality, 0.5x adherence |
| **Serious Mental Illness** | 4% | Random | 1.6x mortality, 0.6x adherence |
| **Atrial Fibrillation** | 5-25% | ↑ 1% per year after age 60 | 2.0x CVD (stroke risk) |
| **PAD** | 12-30% | ↑ with smoking (+8%), diabetes (+5%) | 2.5x CVD (atherosclerosis marker) |

### Correlations Implemented

1. **SBP increases with age** (+0.5 mmHg/year after age 50)
2. **eGFR decreases with age** (-1 mL/min/year after age 40)
3. **uACR inversely correlated with eGFR** (lower kidney function → higher albuminuria)
4. **Diabetes prevalence increases with BMI and age**
5. **Prior CV events more common in older diabetics**
6. **DBP correlated with SBP** (DBP ≈ 0.6 × SBP)

---

## Disease Progression Models

### 1. Cardiovascular Events

**Based on Framingham/QRISK3 equations**, adjusted for patient characteristics:

```
Monthly_CVD_Risk = Baseline_Risk * (1 + 0.01 * (SBP - 120)) 
                                  * (2.0 if diabetic)
                                  * (1.5 if smoker)
                                  * (age_factor)
```

**Event Types:**
- **Myocardial Infarction (MI)**
- **Stroke**
- **Peripheral Arterial Disease (PAD)**
- **Heart Failure** (can develop post-event or independently)

**Recurrent Events:** History-dependent (higher risk post-event, declining over time)

### 2. Renal Progression

**Monthly eGFR Decline:**

```python
# Age-stratified base decline (mL/min/month)
base_decline = {
    age < 50:  0.5 / 12,
    50-65:     0.8 / 12,
    65-75:     1.2 / 12,
    age >= 75: 1.8 / 12
}

# Diabetes acceleration
diabetes_mult = 1.5 if patient.has_diabetes else 1.0

# Continuous SBP effect
bp_effect = 1.0 + 0.05 * max(0, patient.current_sbp - 140)

# Monthly decline
monthly_decline = base_decline * diabetes_mult * bp_effect

# Update eGFR
patient.egfr -= monthly_decline
```

**Stage Transitions:**
- **Automatic** when eGFR crosses thresholds (90, 60, 45, 30, 15)
- **Includes G3a/G3b split** (per KDIGO 2024)
- **One-way** (no recovery, conservative assumption)

### 3. Mortality

**Three competing risks:**

1. **Cardiovascular Death:** Post-MI/stroke/HF
2. **Renal Death:** ESRD complications
3. **Other-Cause Mortality:** Age-adjusted life tables

### 4. **Treatment Adjustments & Safety**

- **Clinical Inertia:** 50% chance of failing to intensify treatment when BP > 130/80.
- **Potassium Safety Rules:** Spironolactone discontinued if serum Potassium > 5.5 mmol/L.
- **Adherence Changes:** Adherence status can flip over time, affecting treatment efficacy.

---

## Baseline Risk Stratification

### Implementation in Population Generation

After sampling baseline characteristics, **three risk assessments** are performed:

```python
# Step 1: Create risk inputs from patient data
risk_inputs = RiskInputs(
    age=patient.age,
    sex=patient.sex,
    egfr=patient.egfr,
    uacr=patient.uacr,
    sbp=patient.sbp,
    total_chol=patient.total_cholesterol,
    hdl_chol=patient.hdl_cholesterol,
    has_diabetes=patient.has_diabetes,
    is_smoker=patient.is_smoker,
    has_cvd=(patient.prior_mi or patient.prior_stroke),
    has_heart_failure=patient.has_heart_failure,
    bmi=patient.bmi
)

# Step 2: Calculate renal risk (GCUA or KDIGO)
if age >= 60 and egfr > 60:
    # GCUA phenotype classification
    gcua_result = calculate_gcua_phenotype(risk_inputs)
    # Assigns phenotype I, II, III, IV, Moderate, or Low
else:
    # KDIGO risk matrix
    kdigo_result = calculate_kdigo_risk(risk_inputs)
    # Assigns Low, Moderate, High, or Very High

# Step 3: Calculate CVD risk (Framingham)
framingham_result = calculate_framingham_risk(risk_inputs)
# 10-year CVD risk percentage

# Step 4: Store in patient profile
patient.baseline_risk_profile = BaselineRiskProfile(
    gcua_phenotype=gcua_result.phenotype,
    kdigo_risk_level=kdigo_result.risk_level,
    framingham_risk=framingham_result.risk,
    framingham_category=framingham_result.category
)
```

### Risk Assessment Algorithms

**1. Nelson/CKD-PC Incident CKD Equation** (for GCUA)
- 5-year probability of developing CKD (eGFR < 60)
- Risk multipliers for age, sex, eGFR, uACR, diabetes, CVD, HF
- C-statistic: 0.845 (non-diabetic), 0.801 (diabetic)

**2. Framingham CVD Risk Score**
- Point-based system (age, sex, BP, lipids, diabetes, smoking)
- 10-year CVD event probability
- Widely validated across populations

**3. Bansal Geriatric Mortality Score** (for GCUA)
- 5-year all-cause mortality in elderly
- Identifies "Senescent" phenotype (mortality >> disease progression)

### Subgroup Analysis Capability

**Example: Cost-Effectiveness by GCUA Phenotype**

```
Phenotype I (Accelerated Ager, n=328):
  ICER: $18,500/QALY vs. standard care
  NNT: 12 to prevent 1 MACE event
  Interpretation: Highly cost-effective, priority for treatment

Phenotype II (Silent Renal, n=227):
  ICER: $32,400/QALY vs. standard care
  NNT: 8 to prevent 1 incident CKD case
  Interpretation: Would be MISSED by CVD-only screening

Phenotype IV (Senescent, n=114):
  ICER: $127,800/QALY vs. standard care
  Interpretation: NOT cost-effective due to competing mortality
```

---

## Patient History Analyzer

### Overview

The **PatientHistoryAnalyzer** module leverages microsimulation's core advantage: using complete patient history to dynamically adjust disease risks. This transforms the model from simple baseline stratification to sophisticated, clinically-realistic risk modification.

### Dynamic Risk Modifiers

#### 1. CVD Risk Modifier

Combines multiple historical and current factors:

**Components:**
- **Prior CVD Events**: First MI → 1.5x, each additional MI → +0.3x
- **Time Decay**: Risk declines exponentially after events (e^(-0.05 × months))
- **Event Clustering**: 3+ events in 60 months → 1.8x
- **Comorbidities**:
  - COPD: 1.5x
  - Atrial fibrillation: 2.0x
  - PAD: 2.5x
  - Heavy alcohol: 1.3x
- **BP Control Quality**:
  - Excellent (<130): 0.85x
  - Poor (≥150): 1.5x
- **Mental Health**:
  - Untreated depression: 1.3x
  - Substance use disorder: 1.8x

**Example:**
```python
Patient: Prior MI (18 months ago) + severe COPD + PAD + poor BP control

Base Framingham risk: 15%
Modifiers:
  - Prior MI with time decay: 1.5 × e^(-0.05×18) = 1.5 × 0.41 = 0.61x excess → 1.61x
  - COPD (severe): 1.8x
  - PAD: 2.5x
  - Poor BP control: 1.5x
  
Total modifier: 1.61 × 1.8 × 2.5 × 1.5 = 10.8x
Adjusted risk: 15% × 10.8 = 162% (capped at realistic maximum)
```

#### 2. Renal Progression Modifier

Based on historical eGFR trajectory:

**Trajectory Classification:**
- **Rapid Decliner** (>3 mL/min/year): 1.5x progression
- **Normal Decliner** (1-3 mL/min/year): 1.0x
- **Slow Decliner** (0.5-1 mL/min/year): 0.8x
- **Stable** (<0.5 mL/min/year): 0.6x

**Additional Factors:**
- Progressing albuminuria (doubled): 1.4x
- Diabetes + CVD synergy: 1.3x
- COPD-CKD interaction: 1.2x
- Poor adherence pattern (SBP variance >400): 1.3x

#### 3. Mortality Risk Modifier

**Charlson Comorbidity Index** + high-impact conditions:

**Charlson Components:**
- MI, HF, PAD, Stroke: 1 point each
- Diabetes (no complications): 1 point
- Diabetes (with complications): 2 points
- CKD moderate (eGFR 30-60): 1 point
- CKD severe (eGFR <30): 2 points
- COPD: 1 point
- Substance use: 2 points
- Serious mental illness: 1 point

**Mortality Calculation:**
```
Base mortality modifier = 1.0 + (Charlson score × 0.10)

Additional multipliers:
  - COPD severe: 2.5x
  - COPD moderate: 1.8x
  - Substance use: 2.0x
  - Serious mental illness: 1.6x
  - Event clustering (2+ in 12 months): 1.5x
```

#### 4. Adherence Probability Modifier

**Mental health and substance use impact:**

| Condition | Adherence Modifier | Expected Adherence (from 75% base) |
|-----------|-------------------|------------------------------------|
| No mental health issues | 1.0x | 75% |
| Treated depression | 0.9x | 68% |
| Untreated depression | 0.7x | 53% |
| Anxiety | 0.85x | 64% |
| Substance use disorder | 0.5x | 38% |
| Serious mental illness | 0.6x | 45% |

**Combination effects** (multiplicative):
```
Patient: Untreated depression + anxiety
Adherence = 75% × 0.7 × 0.85 = 45%
```

### Trajectory Classification

#### eGFR Trajectory Analysis

Analyzes slope of eGFR over past 12-24 months:

```python
# Linear regression on monthly eGFR measurements
slope = Δ_eGFR / Δ_time  # mL/min/month
annual_decline = slope × 12

if annual_decline > 3.0:
    trajectory = "Rapid Decliner"  # High-risk, aggressive treatment
elif annual_decline > 1.0:
    trajectory = "Normal Decliner"  # Standard progression
elif annual_decline > 0.5:
    trajectory = "Slow Decliner"  # Treatment effective
else:
    trajectory = "Stable"  # Excellent control
```

**Clinical Application:**
- Rapid decliners: Priority for nephrology referral
- Stable patients: May be candidates for de-escalation

#### BP Control Classification

Average SBP over past 6 months:

| Classification | SBP Range | Implication |
|----------------|-----------|-------------|
| Excellent | <130 | Optimal control, 0.85x CVD risk |
| Good | 130-139 | Target achieved, 1.0x risk |
| Fair | 140-149 | Suboptimal, 1.2x risk |
| Poor | ≥150 | Treatment adjustment needed, 1.5x risk |

### Comorbidity Burden Assessment

Structured assessment across multiple dimensions:

```python
@dataclass
class ComorbidityBurden:
    charlson_score: int  # 0-15+
    mental_health_burden: str  # "none", "mild", "moderate", "severe"
    substance_use_severity: str  # "none", "mild", "moderate", "severe"
    respiratory_burden: str  # "none", "mild", "moderate", "severe"
    interactive_effects: List[str]  # e.g., ["COPD+CVD", "Depression+Diabetes"]
```

**Interactive Effects:**
- COPD + CVD: Synergistic mortality risk
- Depression + Diabetes: Poor glycemic control, reduced adherence
- Substance use + HF: Very high mortality, poor outcomes

### Clinical Validation

**Evidence-Based Risk Multipliers:**

| Factor | HR for CVD | HR for Mortality | Source |
|--------|------------|------------------|--------|
| COPD | 1.5-2.0 | 2.0-3.0 (severe) | Maclay 2012 |
| Depression | 1.3-1.5 | 1.5-2.0 | Lichtman 2014 |
| Substance use | 1.8-2.5 | 2.5-4.0 | Piano 2017 |
| Atrial fibrillation | 2.0-3.0 | 1.5-2.0 | Kirchhof 2016 |
| PAD | 2.5-3.0 | 2.0-2.5 | Criqui 2015 |

---

## Economic Evaluation

### Costs

**1. State-Specific Costs (Monthly)**

| State | Monthly Cost | Source |
|-------|--------------|--------|
| CKD Stage 1-2 | $250 | Surveillance |
| CKD Stage 3a | $400 | Increased monitoring |
| CKD Stage 3b | $550 | Nephrology consults |
| CKD Stage 4 | $1,200 | Pre-dialysis management |
| ESRD | $7,500 | Dialysis or transplant |
| Post-MI | $800 | Cardiac rehab, meds |
| Post-Stroke | $1,000 | Neurology, rehab |
| Chronic HF | $1,500 | HF clinic, devices |

**2. Event Costs (One-Time)**

| Event | Acute Cost | Source |
|-------|------------|--------|
| Myocardial Infarction | $35,000 | Hospitalization, cath lab |
| Stroke | $28,000 | ICU, imaging, rehab |
| Heart Failure Admission | $15,000 | Inpatient stay |
| ESRD Initiation | $12,000 | Access creation, training |

**3. Treatment Costs**

- **Standard Care:** $150/month (3-4 antihypertensives)
- **IXA-001 (novel agent):** $450/month (includes standard care)

**4. Indirect Costs (Productivity Loss)**

*Applies to working-age population (<65 years).*

| Component | Cost/Loss | Logic |
|-----------|-----------|-------|
| **Daily Wage** | $240 (US) / £160 (UK) | Approx. median wage |
| **Acute Absenteeism** | MI (7d), Stroke (30d), HF (5d) | One-time wage loss per event |
| **Long-Term Disability** | Stroke (20%), HF (15%) | Annual wage loss multiplier |

### Quality of Life (Utilities)

**Base Utilities by Age:**
- Age 40-50: 0.88
- Age 50-60: 0.85
- Age 60-70: 0.82
- Age 70-80: 0.78
- Age 80+: 0.72

**Decrements by State:**

| Condition | Utility Decrement |
|-----------|-------------------|
| CKD Stage 3a | -0.02 |
| CKD Stage 3b | -0.04 |
| CKD Stage 4 | -0.08 |
| ESRD (Dialysis) | -0.15 |
| Post-MI | -0.05 |
| Post-Stroke | -0.10 |
| Chronic HF | -0.12 |

**Minimum Utility:** 0.30 (multiple severe comorbidities)

### Outcomes Calculation

**Quality-Adjusted Life Years (QALYs):**
```
Monthly QALY = (Base Utility - State Decrements) × (1/12)
Lifetime QALY = Σ Monthly QALYs × Discount Factor
```

**Incremental Cost-Effectiveness Ratio (ICER):**
```
ICER = (Cost_Treatment - Cost_Control) / (QALY_Treatment - QALY_Control)
```

**Interpretation:**
- **ICER < $50,000/QALY:** Highly cost-effective (US threshold)
- **ICER $50,000-$100,000:** Cost-effective
- **ICER > $150,000:** Not cost-effective

---

## Technical Implementation

### File Structure

```
hypertension_microsim/
├── src/
│   ├── __init__.py
│   ├── patient.py              # Patient dataclass with K+ tracking and comorbidity fields
│   ├── population.py           # Population generation with SGLT2 assignment and correlations
│   ├── risk_assessment.py      # GCUA, KDIGO, Framingham
│   ├── history_analyzer.py     # Dynamic risk modification
│   ├── treatment.py            # Treatment effects & safety rules
│   ├── simulation.py           # Core simulation engine with safety check loop
│   ├── events.py               # CVD event probability (PREVENT)
│   ├── costs/
│   │   └── costs.py            # Cost parameters (Drug, Acute, Lab, Indirect)
│   └── utilities.py            # QALY calculations (State-based + decrements)
├── tests/                      # Consolidated verification scripts
│   ├── test_enhancements.py
│   ├── test_phase3.py
│   ├── test_sglt2.py
│   ├── test_safety.py
│   └── ...
├── reports/                    # Consolidated project documentation
│   └── Project_History_and_Rationale.md
├── run_demo.py                 # Main execution script
└── README.md
```

### Key Classes

**1. `Patient` Dataclass**
```python
@dataclass
class Patient:
    # Demographics
    patient_id: int
    age: float
    sex: Sex
    
    # Risk factors
    current_sbp: float
    egfr: float
    uacr: float
    has_diabetes: bool
    
    # Comprehensive comorbidity tracking (NEW)
    has_copd: bool
    copd_severity: Optional[str]  # "mild", "moderate", "severe"
    has_depression: bool
    depression_treated: bool
    has_substance_use_disorder: bool
    substance_type: Optional[str]  # "alcohol", "opioids", "stimulants", "poly"
    # ... (13 total new fields)
    
    charlson_score: int  # Comorbidity burden index
    
    # Disease states
    cardiac_state: CardiacState
    renal_state: RenalState
    
    # Baseline risk profile
    baseline_risk_profile: BaselineRiskProfile
    
    # Outcomes
    cumulative_qalys: float
    cumulative_costs: float
```

**2. `Simulation` Class**
```python
class Simulation:
    def run(self, patient: Patient, treatment: Treatment, 
            time_horizon: int = 240) -> Patient:
        """Run simulation for single patient."""
        for month in range(time_horizon):
            # 1. Check for events
            events = self._check_events(patient)
            
            # 2. Accrue outcomes
            self._accrue_outcomes(patient)
            
            # 3. Update patient state
            patient.update_sbp(treatment_effect, rng)
            patient.update_egfr()
            
            # 4. Check for death
            if patient.is_dead():
                break
```

### Python Dependencies

- **numpy**: Numerical operations, random number generation
- **pandas**: Data manipulation, results aggregation
- **dataclasses**: Clean patient/parameter structures
- **typing**: Type hints for robustness

---

## Usage

### Basic Example

```python
from src.population import generate_default_population
from src.simulation import Simulation
from src.treatment import Treatment

# 1. Generate population
patients = generate_default_population(n_patients=1000, seed=42)

# 2. Initialize simulation
sim = Simulation(seed=42)

# 3. Run treatment arm
treatment_results = []
for patient in patients:
    result = sim.run(patient, treatment=Treatment.IXA_001)
    treatment_results.append(result)

# 4. Run control arm
control_results = []
for patient in patients:
    result = sim.run(patient, treatment=Treatment.STANDARD_CARE)
    control_results.append(result)

# 5. Calculate ICER
mean_cost_tx = np.mean([p.cumulative_costs for p in treatment_results])
mean_qaly_tx = np.mean([p.cumulative_qalys for p in treatment_results])
mean_cost_ctrl = np.mean([p.cumulative_costs for p in control_results])
mean_qaly_ctrl = np.mean([p.cumulative_qalys for p in control_results])

icer = (mean_cost_tx - mean_cost_ctrl) / (mean_qaly_tx - mean_qaly_ctrl)
print(f"ICER: ${icer:,.0f}/QALY")
```

### Subgroup Analysis

```python
# Filter by GCUA phenotype
silent_renal = [p for p in treatment_results 
                if p.baseline_risk_profile.gcua_phenotype == "II"]

# Calculate phenotype-specific ICER
silent_renal_qalys = np.mean([p.cumulative_qalys for p in silent_renal])
# ... compare to control arm silent renal patients
```

### Scenario Analysis

```python
# Example: Higher treatment adherence scenario
params = PopulationParams(adherence_prob=0.90)  # vs. 0.75 baseline
high_adherence_pop = PopulationGenerator(params).generate()

# Re-run simulation
# ... compare ICERs
```

---

## References

### Clinical Equations

1. **Nelson et al. (2019)** - CKD-PC Incident CKD Prediction Equation. *Lancet*, 394(10203), 1550-1567.
2. **AHA PREVENT (2024)** - Cardiovascular-Kidney-Metabolic Risk Prediction. *Circulation*.
3. **Bansal et al. (2015)** - Geriatric Mortality Risk Score. *JAMA Internal Medicine*, 175(12), 1961-1970.
4. **KDIGO (2024)** - Clinical Practice Guideline for CKD Management.
5. **Framingham Heart Study** - 10-Year CVD Risk Score.

### Microsimulation Methodology

6. **Briggs et al. (2006)** - Decision Modelling for Health Economic Evaluation. Oxford University Press.
7. **Karnon et al. (2012)** - Selecting a Decision Model for Economic Evaluation. *Pharmacoeconomics*, 30(8), 673-684.
8. **Krijkamp et al. (2018)** - Microsimulation Modeling for Health Decision Sciences. *Medical Decision Making*, 38(3), 355-366.

### Cost-Effectiveness Guidelines

9. **Sanders et al. (2016)** - Recommendations for Conduct of CEA in Health and Medicine. *JAMA*, 316(10), 1093-1103.
10. **Neumann et al. (2017)** - Cost-Effectiveness in Health and Medicine. 2nd Edition.

---

## License

This model is provided for academic and research purposes. For commercial use, please contact the authors.

## Contact

For technical questions or collaboration inquiries, please refer to the project documentation.

---

**Version:** 3.0  
**Last Updated:** February 2026  
**Model Validation Status:** Phase 3 Complete - Advanced cardiac, renal, cognitive, and behavioral modules implemented and verified (Feb 2026).
