# Population Generator for Hypertension Microsimulation
## Comprehensive Guide to Risk Factors, Comorbidities, and Baseline Risk Stratification

**Model Version:** 4.0 (February 2026)
**Last Updated:** Aligned with RFP specifications for IXA-001 cost-effectiveness analysis

---

## Slide 1: Population Generator Overview

### **Purpose**
Generate synthetic cohorts of 1000 patients with resistant hypertension and cardiorenal disease

### **Key Features**
- **Correlated sampling** to maintain realistic relationships between variables
- **13 comprehensive comorbidity tracking** (traditional CV + mental health + respiratory)
- **Secondary HTN etiology classification**: PA, RAS, Pheo, OSA, Essential
- **Dual-branch baseline risk stratification**:
  - **EOCRI Phenotypes** (Age 18-59): Early-Onset CV Risk Indicators
  - **GCUA Phenotypes** (Age 60+): Geriatric CV/CKD/Frailty Assessment
  - **KDIGO Risk Matrix** (for CKD patients, any age)
  - **Framingham 10-Year CVD Risk** (all patients)

### **Data Sources**
- Clinical trial data (SPRINT, ACCORD, KDIGO studies, PATHWAY-2)
- Epidemiological studies (Framingham Heart Study, NHANES)
- Contemporary guidelines (ACC/AHA 2024, KDIGO 2024, AHA PREVENT 2024)

---

## Slide 2: Core Population Parameters

### **Demographics**
| Parameter | Distribution | Mean ± SD | Range |
|-----------|--------------|-----------|-------|
| **Age** | Truncated Normal | 62 ± 10 years | 40-85 years |
| **Sex** | Bernoulli | 55% male | - |
| **BMI** | Normal | 30.5 ± 5.5 kg/m² | 18-55 |

### **Resistant Hypertension**
- **Definition**: Uncontrolled BP despite treatment with ≥3 antihypertensive agents
- **Mean antihypertensives**: 4 medications
- **Baseline adherence**: 75% (adjusted by age and social factors)

### **Cohort Size**
- **Default**: N = 1000 patients
- **Seed**: Reproducible random number generation

---

## Slide 3: Hemodynamic Parameters - Blood Pressure

### **Systolic Blood Pressure (SBP)**
```
Distribution: Truncated Normal
Mean: 155 mmHg
SD: 15 mmHg
Range: 140-200 mmHg

Age Correlation:
SBP = Base SBP + Age Effect
where Age Effect = max(0, (Age - 50) × 0.5)

Example: 70-year-old
  Base SBP: 155 mmHg
  Age effect: (70-50) × 0.5 = +10 mmHg
  Final SBP: ~165 mmHg
```

### **Treatment Effects (IXA-001 vs Spironolactone)**
| Treatment | SBP Reduction | Source |
|-----------|---------------|--------|
| **IXA-001** | **20 mmHg** | Phase III RFP specification |
| **Spironolactone** | 9 mmHg | PATHWAY-2 trial |

### **Diastolic Blood Pressure (DBP)**
```
Correlation with SBP:
DBP ~ 0.6 × SBP + ε
where ε ~ N(0, 5 mmHg)

Mean: 92 mmHg
Range: 60-120 mmHg
```

---

## Slide 4: Renal Function Parameters

### **Estimated Glomerular Filtration Rate (eGFR)**
```
Distribution: Truncated Normal with age adjustment
Base Mean: 68 mL/min/1.73m²
SD: 20 mL/min/1.73m²
Range: 15-120 mL/min/1.73m²

Age Correlation:
eGFR = Base eGFR - Age Decline
where Age Decline = max(0, (Age - 40) × 1.0)

Example: 70-year-old
  Base eGFR: 88 mL/min
  Age decline: (70-40) × 1.0 = -30 mL/min
  Final eGFR: ~58 mL/min (CKD Stage 3a)
```

### **Urinary Albumin-to-Creatinine Ratio (uACR)**
```
Distribution: Log-normal
Inverse correlation with eGFR:

Lower eGFR → Higher albuminuria
eGFR Factor = max(0.5, (90 - eGFR) / 60)
log(uACR) ~ N(log(50) + eGFR_Factor × 0.5, 0.8)

Range: 1-3000 mg/g
```

---

## Slide 5: Secondary Causes of Resistant Hypertension (NEW)

### **Overview**
The model now explicitly captures secondary causes of resistant hypertension, which is critical for IXA-001 (aldosterone synthase inhibitor) value assessment.

### **Secondary HTN Etiologies**
| Etiology | Abbreviation | Base Prevalence | Key Risk Factors |
|----------|--------------|-----------------|------------------|
| **Primary Aldosteronism** | PA | 17% | Severe HTN (SBP>160), obesity |
| **Renal Artery Stenosis** | RAS | 8% | Age >65, diabetes, smoking, atherosclerosis |
| **Pheochromocytoma** | Pheo | 0.7% | Age <50, very severe HTN (SBP>170) |
| **Obstructive Sleep Apnea** | OSA | 65% | Obesity, male sex, older age |
| **Essential HTN** | - | ~56% | No identified secondary cause |

### **Sampling Logic**
```python
# Mutually exclusive primary etiology assignment
# OSA can coexist with other causes
if roll < pheo_prob:
    etiology = "Pheo"
elif roll < pheo_prob + pa_prob:
    etiology = "PA"
elif roll < pheo_prob + pa_prob + ras_prob:
    etiology = "RAS"
else:
    etiology = "Essential"

# OSA assigned independently (can coexist)
if random() < osa_prob:
    has_osa = True
    severity = ["mild", "moderate", "severe"]  # 30%, 40%, 30%
```

---

## Slide 6: Primary Aldosteronism (PA) - Key Target Population

### **Why PA Matters for IXA-001**
PA patients are the **optimal target population** for aldosterone synthase inhibitors because:
1. Aldosterone is the **root cause** of their hypertension
2. IXA-001 provides **complete aldosterone suppression** at the source
3. Higher baseline CV/renal risk → greater absolute benefit

### **PA Prevalence Calculation**
```python
pa_prob = 0.17 × (
    1 + 0.25 × (SBP > 160) +
    0.20 × (BMI ≥ 30)
)
pa_prob = min(pa_prob, 0.25)  # Cap at 25%

# Example: SBP 170, BMI 32
pa_prob = 0.17 × (1 + 0.25 + 0.20) = 0.25 (25%)
```

### **PA-Specific Baseline Risk Modifiers**
| Outcome | Modifier | Rationale |
|---------|----------|-----------|
| MI | 1.40× | Coronary remodeling, microvascular disease |
| Stroke | 1.50× | Vascular stiffness, AF-mediated emboli |
| **HF** | **2.05×** | Direct aldosterone-mediated cardiac fibrosis |
| **ESRD** | **1.80×** | Aldosterone-mediated renal fibrosis |
| AF | 3.0× | Atrial remodeling, left atrial enlargement |
| Death | 1.60× | Combined pathways |

**Reference:** Monticone S, et al. JACC 2018

---

## Slide 7: PA Treatment Response Modifiers

### **Differential Treatment Response by Etiology**
| Etiology | IXA-001 | Spironolactone | Standard Care |
|----------|---------|----------------|---------------|
| **PA** | **1.70×** | 1.40× | 0.75× |
| **OSA** | 1.20× | 1.15× | 1.0× |
| **RAS** | 1.05× | 0.95× | 1.10× |
| **Pheo** | 0.40× | 0.35× | 0.50× |
| **Essential** | 1.0× | 1.0× | 1.0× |

### **Clinical Rationale**
- **IXA-001 (1.70×)**: Blocks aldosterone synthesis at source; no "escape" phenomenon
- **Spironolactone (1.40×)**: Blocks receptor but aldosterone continues accumulating
- **Standard Care (0.75×)**: Poor response when aldosterone excess is root cause

### **Efficacy Coefficient Translation**
```
Risk Factor = 1.0 - (Treatment Modifier - 1.0) × Efficacy Coefficient

PA Patient on IXA-001 (HF example):
  Treatment Modifier = 1.70
  HF Efficacy Coefficient = 0.50
  Risk Factor = 1.0 - (1.70 - 1.0) × 0.50 = 0.65
  → 35% HF risk reduction
```

---

## Slide 8: Lipid Panel

### **Total Cholesterol**
```
Distribution: Truncated Normal
Mean: 200 mg/dL
SD: 40 mg/dL
Range: 120-350 mg/dL
```

### **HDL Cholesterol**
```
Distribution: Truncated Normal
Mean: 48 mg/dL
SD: 12 mg/dL
Range: 20-100 mg/dL
```

### **LDL Cholesterol** (derived)
```
Friedewald Equation:
LDL = Total Chol - HDL - (Triglycerides/5)
```

---

## Slide 9: Traditional Cardiovascular Comorbidities

### **Diabetes Mellitus**
```
Base Prevalence: 35%

Correlations:
- BMI effect: +2% per unit above 25 kg/m²
- Age effect: +0.5% per year above 50
- Formula: P(diabetes) = 0.35 + (BMI-25)×0.02 + (Age-50)×0.005

Example: Age 70, BMI 35
  P(diabetes) = 0.35 + 10×0.02 + 20×0.005 = 0.65 (65%)
```

### **Current Smoking**
```
Base prevalence: 15%
Random sampling (no correlations modeled)
```

### **Dyslipidemia**
```
Base prevalence: 60%
Random sampling
```

---

## Slide 10: Prior Cardiovascular Events

### **Sampling Method**
All prior events correlated with **age** and **diabetes status**

```
P(event) = Base Prev + Age Effect + Diabetes Effect

where:
  Age Effect = (Age - 50) × 0.003
  Diabetes Effect = HasDiabetes × 0.05
```

### **Prevalence Rates**
| Event | Base Prevalence | Age Correlation | Diabetes Bonus |
|-------|----------------|-----------------|----------------|
| **Prior MI** | 10% | +0.3%/year | +5% |
| **Prior Stroke** | 5% | +0.3%/year | +5% |
| **Heart Failure** | 8% | +0.3%/year | +5% |

### **Example**: 70-year-old with diabetes
```
P(prior MI) = 0.10 + (70-50)×0.003 + 0.05 = 0.21 (21%)
```

---

## Slide 11: Respiratory Comorbidity - COPD

### **Chronic Obstructive Pulmonary Disease**
```
Base Prevalence: 17%
Smoking Effect: +15% if current smoker

P(COPD) = 0.17 + (0.15 × IsSmoker)

Distribution:
  Smoker: 32% COPD prevalence
  Non-smoker: 17% COPD prevalence
```

### **COPD Severity Classification** (among those with COPD)
| Severity | Prevalence | Mortality Multiplier | CVD Multiplier |
|----------|------------|---------------------|----------------|
| **Mild** | 40% | 1.2× | 1.0× |
| **Moderate** | 40% | 1.8× | 1.3× |
| **Severe** | 20% | 2.5× | 1.8× |

**Impact**: Severe COPD → 2.5× baseline mortality, 1.8× CVD risk

---

## Slide 12: Mental Health Comorbidities - Depression

### **Major Depressive Disorder**
```
Base Prevalence: 27%

Risk Modifiers:
1. Female AND Age < 65: +30%
2. Has Diabetes: +20%

Formula:
P(depression) = 0.27 × (1 + 0.3×Female×Young) × (1 + 0.2×Diabetes)
Capped at 50% to maintain realism
```

### **Treatment Status**
```
Among those with depression:
  Treated (on antidepressant): 60%
  Untreated: 40%
```

### **Impact on Model Dynamics**
- **Untreated depression**:
  - Adherence multiplier: 0.7× (30% reduction)
  - CVD risk multiplier: 1.3×
- **Treated depression**: No adherence penalty

---

## Slide 13: Mental Health - Anxiety and Serious Mental Illness

### **Anxiety Disorders**
```
Base Prevalence: 17%

Comorbidity with Depression:
P(anxiety) = 0.17 × (1 + 1.35 × HasDepression)
Capped at 50%

Distribution:
  If depressed: 40% anxiety prevalence
  If not depressed: 17% anxiety prevalence
```

**Impact**: Adherence multiplier 0.85× (15% reduction)

### **Serious Mental Illness (SMI)**
```
Prevalence: 4%
Includes: Schizophrenia, schizoaffective disorder, bipolar disorder

Impact:
  - Charlson score: +1 point
  - Adherence multiplier: 0.6× (40% reduction)
  - Mortality multiplier: 1.6×
```

---

## Slide 14: Substance Use Disorders

### **Substance Use Disorder Classification**
```
Overall Prevalence: 10%

Substance Type Distribution (among users):
  Alcohol: 50%
  Opioids: 20%
  Stimulants: 15%
  Polysubstance: 15%
```

### **Heavy Alcohol Use** (separate category)
```
Prevalence: 15%
Independent of substance use disorder diagnosis
```

### **Impact on Model**
| Factor | Effect |
|--------|--------|
| **CVD Risk** | 1.8× multiplier |
| **Mortality Risk** | 2.0× multiplier |
| **Adherence** | 0.5× (50% reduction) |
| **Charlson Score** | +2 points |

---

## Slide 15: Additional Cardiovascular Comorbidities

### **Atrial Fibrillation (AFib)**
```
Base Prevalence: 5%
Age Effect: Increases 1% per year after age 60

P(AFib) = 0.05 + max(0, Age - 60) × 0.01
Capped at 25%

Example: Age 75
  P(AFib) = 0.05 + (75-60)×0.01 = 0.20 (20%)
```

**Impact**: CVD (stroke) risk multiplier = 2.0×

**NEW - PA Effect on AF**: PA patients have **12× baseline AF risk** (Monticone 2018)

### **Peripheral Artery Disease (PAD)**
```
Base Prevalence: 12%
Smoking Effect: +8%
Diabetes Effect: +5%

P(PAD) = 0.12 + 0.08×IsSmoker + 0.05×HasDiabetes
Capped at 30%

Example: Smoker with diabetes
  P(PAD) = 0.12 + 0.08 + 0.05 = 0.25 (25%)
```

**Impact**: CVD risk multiplier = 2.5× (marker of advanced atherosclerosis)

---

## Slide 16: Social Determinants of Health

### **Social Deprivation Index (SDI)**
```
Distribution: Beta(2, 2) × 100
Shape: Slight skew toward lower deprivation
Range: 0-100
Mean: ~50

Interpretation:
  0-25: Low deprivation (affluent)
  25-50: Moderate-low
  50-75: Moderate-high
  75-100: High deprivation (disadvantaged)
```

### **Impact on Adherence**
```
Baseline adherence: 75%

Modifiers:
  Age < 50: -15% absolute
  SDI > 75: -20% absolute

Example: 45-year-old, SDI = 80
  Adherence = 0.75 - 0.15 - 0.20 = 0.40 (40%)

Final adherence clipped to [0.10, 0.95]
```

---

## Slide 17: Nocturnal Blood Pressure & Dipping Status

### **Dipping Classification**
Based on nocturnal SBP relative to daytime SBP:

| Category | Nocturnal Drop | Prevalence | Risk |
|----------|----------------|------------|------|
| **Normal Dipper** | 10-20% lower | ~50% | Baseline |
| **Non-Dipper** | 0-10% lower | ~40% | 1.3× CVD risk |
| **Reverse Dipper** | 0-10% HIGHER | ~10% | 1.8× CVD risk |

### **Risk Factors for Non-Dipping**
```
Base probability: 25%
Age effect: +0.5% per year above 50
Diabetes effect: +20%

P(non-dipping) = 0.25 + 0.005×max(0,Age-50) + 0.20×HasDiabetes
Capped at 80%

Example: 70-year-old with diabetes
  P(non-dipping) = 0.25 + 0.10 + 0.20 = 0.55 (55%)
```

### **Clinical Significance**
Non-dipping status is a strong independent predictor of:
- Target organ damage (LVH, microalbuminuria)
- Cardiovascular events
- CKD progression

---

## Slide 18: White Coat Hypertension

### **Definition & Prevalence**
```
Prevalence: 20% of office hypertensives
Effect: Office SBP is 10-20 mmHg HIGHER than true/home BP
```

### **White Coat Effect Sampling**
```
Distribution: Gamma(shape=3.0, scale=5.0)
Mean effect: 15 mmHg
Range: 5-40 mmHg (clipped for realism)

For non-WCH patients:
  Effect ~ N(0, 2 mmHg) (minimal noise)
```

### **Model Implementation**
```
Office SBP = True SBP + White Coat Effect

Clinical Impact:
  - Office BP drives TREATMENT decisions (intensification)
  - True BP drives BIOLOGICAL risk (CVD, renal events)

This creates a realistic mismatch between clinical actions and outcomes,
mimicking real-world therapeutic inertia and overtreatment scenarios.
```

---

## Slide 19: SGLT2 Inhibitor Usage

### **Guideline-Directed Medical Therapy (GDMT)**
```
Indication: Class 1A recommendation for:
  - CKD (eGFR < 60)
  - Heart Failure (any stage)

Real-World Uptake: 40% among eligible patients

Eligibility Check:
  IsEligible = (eGFR < 60) OR HasHeartFailure
  OnSGLT2 = IsEligible AND (random() < 0.40)
```

### **Clinical Benefits** (modeled downstream)
| Outcome | Effect Size |
|---------|------------|
| **HF Hospitalization** | -30% (HR 0.70) |
| **eGFR Decline Rate** | -40% slower |
| **Albuminuria Progression** | -30% reduction |

**Cost**: $450/month (US), £35/month (UK generic)

---

## Slide 20: Charlson Comorbidity Index

### **Purpose**
Aggregate comorbidity burden score (0-15+ points) predicting mortality

### **Scoring Algorithm**
```python
Score = 0

# Cardiovascular (1 point each)
if prior_MI: score += 1
if heart_failure: score += 1
if PAD: score += 1
if prior_stroke: score += 1

# Diabetes
if has_diabetes:
    has_complications = (eGFR < 60) or prior_MI or prior_stroke
    score += 2 if has_complications else 1

# Renal disease
if eGFR < 30: score += 2      # Severe CKD
elif eGFR < 60: score += 1    # Moderate CKD

# Respiratory
if has_COPD: score += 1

# Substance use & mental health
if substance_use_disorder: score += 2
if serious_mental_illness: score += 1
```

### **Example Patient**
- Prior MI, diabetes with CKD 3b (eGFR 35), COPD
- Score = 1 (MI) + 2 (DM with complications) + 1 (CKD) + 1 (COPD) = **5 points**

---

## Slide 21: Dual-Branch Baseline Risk Stratification (NEW)

### **Age-Based Phenotyping Architecture**
The model uses a **dual-branch system** based on patient age:

```
┌─────────────────────────────────────────────────────────────┐
│               BASELINE RISK STRATIFICATION                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Age 18-59                          Age 60+                  │
│  ─────────                          ───────                  │
│                                                              │
│  ┌─────────────────┐               ┌─────────────────┐       │
│  │     EOCRI       │               │      GCUA       │       │
│  │  Early-Onset    │               │   Geriatric     │       │
│  │  Cardiorenal    │               │  CV/CKD/Frailty │       │
│  │  Risk Indicator │               │   Assessment    │       │
│  └─────────────────┘               └─────────────────┘       │
│                                                              │
│  Phenotypes:                       Phenotypes:               │
│  • Type A: Early Metabolic         • Type I: Accelerated     │
│  • Type B: Silent Renal ⚠️          • Type II: Silent Renal ⚠️│
│  • Type C: Premature Vascular      • Type III: Vascular Dom. │
│  • Low Risk                        • Type IV: Senescent      │
│                                    • Moderate/Low Risk       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  KDIGO Risk Matrix: Applied to ALL patients with CKD         │
│  Framingham CVD Risk: Calculated for ALL patients            │
│  Secondary HTN Etiology: PA, RAS, Pheo, OSA, Essential       │
└─────────────────────────────────────────────────────────────┘
```

### **Why Dual-Branch?**
- **GCUA** was designed for geriatric patients (60+)
- **EOCRI** uses AHA PREVENT equations optimized for ages 18-59
- Both identify **"Silent Renal"** patients who would be missed by CVD-only screening

---

## Slide 22: EOCRI Phenotype Classification (NEW)

### **Early-Onset Cardiorenal Risk Indicator (EOCRI)**
**Target Population**: Age 18-59, eGFR > 60 mL/min

### **Purpose**
Identify distinct phenotypes in **younger adults without overt CKD** who are at risk for cardiorenal disease.

### **Three-Module Architecture**
1. **PREVENT 30-Year Risk**: Lifetime CVD risk (replaces Framingham 10-year)
2. **Metabolic Burden Score**: Diabetes, obesity, dyslipidemia, elevated uACR
3. **Renal Progression Risk**: Based on albuminuria and acceleration factors

### **EOCRI Phenotype Assignment**

| Phenotype | Name | Criteria | Prevalence |
|-----------|------|----------|------------|
| **Type A** | Early Metabolic | Elevated uACR + diabetes/obesity (metabolic burden ≥2) | ~25% |
| **Type B** | Silent Renal ⚠️ | Elevated uACR + NO diabetes + normal lipids | ~18% |
| **Type C** | Premature Vascular | PREVENT risk ≥30% without elevated uACR | ~15% |
| **Low** | Low Risk | PREVENT risk <20%, no elevated uACR | ~42% |

### **Type B: Silent Renal - KEY TARGET**
- Elevated albuminuria WITHOUT traditional CVD risk factors
- Would be **MISSED by Framingham/ASCVD guidelines**
- Requires nephroprotection (ACEi/ARB, SGLT2i) despite low "CVD risk"

---

## Slide 23: EOCRI Implementation

### **PREVENT 30-Year Risk Calculation**
```python
def _calculate_prevent_30yr_risk(inputs: RiskInputs) -> float:
    """AHA PREVENT equation for 30-year CVD risk (age 30-59)."""

    log_hazard = -12.0  # Base hazard

    # Age (0.06 per year from 30)
    log_hazard += 0.06 * (inputs.age - 30)

    # Sex
    if inputs.sex == "male":
        log_hazard += 0.3

    # SBP (continuous, 0.02 per mmHg from 120)
    log_hazard += 0.02 * (inputs.sbp - 120)

    # eGFR (inverse relationship even within normal)
    log_hazard += 0.8 * max(0, (90 - inputs.egfr) / 30)

    # Albuminuria (strong predictor)
    if inputs.uacr and inputs.uacr >= 30:
        log_hazard += 1.2 * np.log(max(30, inputs.uacr) / 30)

    # Diabetes
    if inputs.has_diabetes:
        log_hazard += 0.7

    # Smoking
    if inputs.is_smoker:
        log_hazard += 0.5

    # BMI
    log_hazard += 0.03 * max(0, inputs.bmi - 25)

    # Convert to 30-year probability
    return 100 / (1 + np.exp(-log_hazard))
```

### **Metabolic Burden Score**
```python
def _calculate_metabolic_burden(inputs: RiskInputs) -> int:
    """Count metabolic risk factors (0-4)."""
    score = 0
    if inputs.has_diabetes: score += 1
    if inputs.bmi and inputs.bmi >= 30: score += 1
    if inputs.has_dyslipidemia: score += 1
    if inputs.uacr and inputs.uacr >= 30: score += 1
    return score
```

---

## Slide 24: GCUA Phenotype Classification (Age 60+)

### **Geriatric Cardiorenal-Metabolic Unified Algorithm (GCUA)**

### **Purpose**
Identify distinct phenotypes in **older adults without overt CKD**
Target: Age ≥ 60, eGFR > 60 mL/min

### **Why GCUA?**
- Traditional CVD risk scores underestimate renal risk
- **Type II (Silent Renal)** patients have high renal risk but LOW CVD risk
  - Would be MISSED by CVD-only screening (e.g., statin guidelines)
  - Require nephroprotective interventions (ACEi/ARB, SGLT2i)

### **Three-Module Architecture**
1. **Nelson/CKD-PC**: 5-year incident CKD risk
2. **Framingham**: 10-year CVD risk
3. **Bansal**: Geriatric mortality risk

### **GCUA Classification Matrix**
```
            CVD Risk Low (<20%)   CVD Risk High (≥20%)
            ┌────────────────────┬────────────────────┐
Nelson ≥15% │ Type II            │ Type I             │
(High)      │ Silent Renal ⚠️     │ Accelerated Ager   │
            ├────────────────────┼────────────────────┤
Nelson <15% │ Moderate/Low Risk  │ Type III           │
(Low)       │                    │ Vascular Dominant  │
            └────────────────────┴────────────────────┘

Mortality Override: If Bansal ≥25% → Type IV (Senescent)
```

---

## Slide 25: GCUA Phenotypes - Clinical Characteristics

### **Type I: Accelerated Ager**
**Definition**: High renal risk + High CVD risk
**Prevalence**: ~33% of eligible patients
**Characteristics**:
- Older age (typically 70+)
- Multiple risk factors (diabetes, smoking, obesity)
- Albuminuria present
- High SBP despite treatment

**Management**: Intensive BP control + Nephroprotection + Statin

---

### **Type II: Silent Renal** ⚠️ **MOST IMPORTANT**
**Definition**: High renal risk + LOW CVD risk
**Prevalence**: ~23% of eligible patients
**Characteristics**:
- Normal lipids, non-smokers
- Albuminuria WITHOUT traditional CVD risk factors
- Would be **MISSED by Framingham/ASCVD guidelines**
- **No statin indication** by CVD risk alone

**Management**: ACEi/ARB, SGLT2i for nephroprotection (even if CVD risk low)

---

### **Type III: Vascular Dominant**
**Definition**: LOW renal risk + High CVD risk
**Prevalence**: ~20% of eligible patients
**Characteristics**:
- High CVD risk (diabetes, smoking, dyslipidemia)
- Preserved kidney function
- No albuminuria

**Management**: Statin + Antiplatelet + BP control (standard CVD prevention)

---

### **Type IV: Senescent**
**Definition**: Very high mortality risk (≥25% at 5 years)
**Prevalence**: ~11% of eligible patients
**Characteristics**:
- Advanced age (typically 80+)
- Multiple comorbidities (HF, COPD, frailty)
- Competing mortality limits benefit from prevention

**Management**: Symptom control, less aggressive targets (avoid polypharmacy)

---

## Slide 26: KDIGO Risk Matrix Overview

### **Kidney Disease: Improving Global Outcomes (KDIGO)**
Classification for patients with **Chronic Kidney Disease (CKD)**

### **Purpose**
- Stratify CKD patients by **prognosis** (risk of progression to ESRD, CVD, mortality)
- Guide treatment intensity and monitoring frequency
- Applied to **all patients regardless of age** (unlike GCUA/EOCRI)

### **Two-Dimensional System**
1. **GFR Category** (G1-G5): Degree of kidney function loss
2. **Albuminuria Category** (A1-A3): Degree of kidney damage

### **GFR Categories**
| Category | eGFR (mL/min/1.73m²) | Description |
|----------|---------------------|-------------|
| **G1** | ≥ 90 | Normal/high |
| **G2** | 60-89 | Mildly decreased |
| **G3a** | 45-59 | Mildly-moderately decreased |
| **G3b** | 30-44 | Moderately-severely decreased |
| **G4** | 15-29 | Severely decreased |
| **G5** | < 15 | Kidney failure (ESRD) |

---

## Slide 27: KDIGO Risk Matrix - Combined Assessment

### **Risk Level by GFR × Albuminuria**

```
                   Albuminuria Category
                 A1          A2          A3
               (<30)      (30-300)     (>300)
         ┌──────────────────────────────────┐
      G1 │  Low        Moderate      High   │
   (≥90) │   🟢          🟡          🔴    │
         ├──────────────────────────────────┤
      G2 │  Low        Moderate      High   │
  (60-89)│   🟢          🟡          🔴    │
         ├──────────────────────────────────┤
     G3a │ Moderate      High      Very High│
  (45-59)│   🟡          🔴          🔴    │
         ├──────────────────────────────────┤
     G3b │  High     Very High   Very High  │
  (30-44)│   🔴          🔴          🔴    │
         ├──────────────────────────────────┤
      G4 │Very High  Very High   Very High  │
  (15-29)│   🔴          🔴          🔴    │
         ├──────────────────────────────────┤
      G5 │Very High  Very High   Very High  │
   (<15) │   🔴          🔴          🔴    │
         └──────────────────────────────────┘
```

### **Risk Level Interpretation**
- 🟢 **Low**: Standard monitoring (annual)
- 🟡 **Moderate**: Nephrology co-management, semi-annual monitoring
- 🔴 **High**: Intensive nephrology care, quarterly monitoring
- 🔴 **Very High**: Urgent nephrology referral, monthly monitoring, prepare for RRT

---

## Slide 28: Framingham 10-Year CVD Risk

### **Purpose**
Predict **10-year absolute risk** of cardiovascular disease events:
- Myocardial infarction (MI)
- Stroke (ischemic or hemorrhagic)
- Heart failure hospitalization
- Cardiovascular death

### **Population**
**All patients** receive Framingham score (not age- or eGFR-restricted like GCUA/EOCRI)

### **Risk Thresholds** (ACC/AHA 2019 Guidelines)

| Category | 10-Year Risk | Management |
|----------|--------------|------------|
| **Low Risk** | < 5% | Lifestyle modification, no statin |
| **Borderline** | 5-7.4% | Consider statin if risk enhancers present |
| **Intermediate** | 7.5-19.9% | **Statin recommended** (moderate intensity) |
| **High Risk** | ≥ 20% | **Statin recommended** (high intensity) |

### **Clinical Use**
- Guides statin therapy decisions
- Informs shared decision-making
- **Complements GCUA/EOCRI**: CVD risk is one axis of the classification matrix

---

## Slide 29: Patient Examples - Integration Across All Systems

### **Example 1: PA Patient with Silent Renal Disease (EOCRI Type B)**
```
Demographics: 52-year-old female, non-smoker
Risk Factors: SBP 165, eGFR 78, uACR 85, Total Chol 185, HDL 58
Comorbidities: No diabetes, no prior CVD
Secondary HTN: Primary Aldosteronism (PA)

Baseline Risk Profile:
  EOCRI Phenotype: Type B (Silent Renal)
    - PREVENT 30-year: 22% (Intermediate)
    - Metabolic burden: 1 (elevated uACR only)
    - ⚠️ Would be MISSED by CVD-only screening

  Secondary HTN Etiology: PA
    - HF risk: 2.05× baseline
    - ESRD risk: 1.80× baseline
    - AF risk: 3.0× baseline

  KDIGO: G2 + A2 = Moderate Risk

  Treatment Response:
    - IXA-001: 1.70× (enhanced)
    - Spironolactone: 1.40× (enhanced)

Management:
  - IXA-001 preferred (blocks aldosterone at source)
  - ACEi/ARB for nephroprotection
  - SGLT2i consideration
  - ⚠️ Statin debatable (borderline by CVD risk alone)
```

---

### **Example 2: Elderly Patient with Type I GCUA**
```
Demographics: 72-year-old male, former smoker
Risk Factors: SBP 158, eGFR 52, uACR 180, Total Chol 220, HDL 38
Comorbidities: Diabetes, prior MI, COPD
Secondary HTN: Essential (no secondary cause identified)

Baseline Risk Profile:
  GCUA Phenotype: Type I (Accelerated Ager)
    - Nelson (renal): 28% (HIGH)
    - Framingham (CVD): 35% (HIGH)
    - Bansal (mortality): 15%

  KDIGO: G3a + A2 = High Risk

  Charlson Score: 6 points
    - MI (+1), Diabetes with complications (+2), CKD 3a (+1), COPD (+1), smoking (+1)

  Treatment Response:
    - IXA-001: 1.0× (baseline - no PA)
    - Standard care expected

Management:
  - Intensive BP control (SBP <130)
  - High-intensity statin
  - SGLT2i (for CKD + post-MI benefit)
  - ACEi/ARB
  - Consider IXA-001 if aldosterone levels elevated
```

---

## Slide 30: Summary - Population Generator Output

### **What Gets Created for Each Patient?**

**Demographics & Risk Factors** (17 variables)
- Age, sex, BMI, SBP, DBP, eGFR, uACR, lipids, SDI, nocturnal BP, WCH effect

**Comorbidities** (13 conditions)
- Traditional CV: Diabetes, smoking, dyslipidemia, prior MI/stroke, HF, AFib, PAD
- Respiratory: COPD (with severity)
- Mental health: Depression, anxiety, SMI
- Substance: Substance use disorder, heavy alcohol use

**Secondary HTN Etiology** (NEW)
- PA, RAS, Pheo, OSA, Essential
- Determines treatment response modifiers

**Treatment & Adherence**
- Number of antihypertensives (mean 4)
- Baseline adherence (age/SDI-adjusted)
- SGLT2 inhibitor usage (GDMT-based)

**Baseline Risk Profile** (Dual-Branch)
1. **Renal Risk**: EOCRI (age 18-59) OR GCUA (age 60+) OR KDIGO (CKD patients)
2. **CVD Risk**: Framingham 10-year OR PREVENT 30-year (by age)
3. **Mortality Risk**: Bansal score (within GCUA) or Charlson score

**Initial Disease States**
- Cardiac: NO_EVENT, POST_MI, POST_STROKE, or CHRONIC_HF
- Renal: CKD_1_2, CKD_3A, CKD_3B, CKD_4, or ESRD

---

### **Key Takeaway**
Every patient is a **unique individual** with:
- Correlated risk factors for realistic heterogeneity
- Secondary HTN etiology determining treatment response
- Dual-branch phenotyping (EOCRI/GCUA) identifying high-risk patients
- Complete baseline profile enabling precision medicine targeting

**Output**: List of 1000 `Patient` objects ready for microsimulation!

---

## Appendix: References

### **Risk Stratification Algorithms**
1. **GCUA**: Nelson et al. (2019) - CKD-PC Incident CKD Equation. *Lancet Diabetes Endocrinol.*
2. **EOCRI/PREVENT**: Khan SS et al. (2024) - AHA PREVENT Equations. *Circulation.*
3. **KDIGO**: KDIGO CKD Guidelines (2024) - Risk Matrix Update
4. **Framingham**: D'Agostino et al. (2008) - General Cardiovascular Risk Profile. *Circulation.*
5. **Bansal**: Bansal et al. (2018) - Geriatric Mortality Score

### **Secondary HTN & Treatment Effects**
6. **PA Outcomes**: Monticone S, et al. (2018) - PA cardiovascular events. *JACC.*
7. **PATHWAY-2**: Williams B, et al. (2015) - Spironolactone in resistant HTN. *Lancet.*
8. **IXA-001 (Baxdrostat)**: Freeman MW, et al. (2023) - Phase 2 trial. *JACC.*

### **Comorbidity Prevalence**
9. NHANES (2017-2020) - Depression, COPD, substance use prevalence in hypertensive adults
10. Framingham Heart Study - Traditional CV risk factor distributions

### **Guidelines**
11. ACC/AHA (2024) - Blood Pressure Management Guidelines
12. AHA PREVENT (2024) - CVD-Kidney-Metabolic Risk Assessment
13. KDIGO (2024) - Clinical Practice Guideline for CKD

---

## Code References

| Component | File | Key Function/Class |
|-----------|------|-------------------|
| Population Generator | `src/population.py` | `PopulationGenerator.generate()` |
| EOCRI Phenotyping | `src/risk_assessment.py:534` | `calculate_eocri_phenotype()` |
| GCUA Phenotyping | `src/risk_assessment.py` | `calculate_gcua_phenotype()` |
| Secondary HTN Etiology | `src/population.py:244-306` | Etiology sampling loop |
| Treatment Response | `src/risk_assessment.py:346` | `get_treatment_response_modifier()` |
| Baseline Risk Modifiers | `src/risk_assessment.py:146` | `get_dynamic_modifier()` |
| KDIGO Risk Matrix | `src/risk_assessment.py` | `calculate_kdigo_risk()` |
| Framingham Risk | `src/risk_assessment.py` | `calculate_framingham_risk()` |

---

**Model Version**: 4.0 (February 2026)
**Aligned with**: Atlantis Pharmaceuticals RFP for IXA-001 CEA/BIM
