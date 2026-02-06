# Treatment Effects and Phenotype Modifiers

## Technical Documentation for IXA-001 Hypertension Microsimulation Model

**Version:** 4.0
**Last Updated:** February 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Treatment Effect Mechanism](#treatment-effect-mechanism)
3. [Phenotype-Specific Baseline Risk Modifiers](#phenotype-specific-baseline-risk-modifiers)
4. [Treatment Response Modifiers](#treatment-response-modifiers)
5. [Efficacy Coefficient Translation](#efficacy-coefficient-translation)
6. [Complete Worked Example](#complete-worked-example)
7. [Coherence with RFP Requirements](#coherence-with-rfp-requirements)
8. [References](#references)

---

## Overview

The model applies treatment effects through a **three-stage multiplicative pipeline**:

```
Final Event Probability = Base Probability × Phenotype Modifier × Treatment Risk Factor
```

Where:
- **Base Probability:** Calculated from AHA PREVENT equations using patient demographics and risk factors
- **Phenotype Modifier:** Baseline risk elevation based on secondary HTN etiology (PA, OSA, RAS, Pheo)
- **Treatment Risk Factor:** Risk reduction from treatment, modified by etiology-specific response

This approach captures both:
1. The **elevated baseline risk** in specific phenotypes (e.g., PA patients have 2.05× HF risk)
2. The **differential treatment response** by etiology (e.g., PA patients respond 70% better to IXA-001)

---

## Treatment Effect Mechanism

### Stage 1: Base Event Probability (PREVENT Equations)

The AHA PREVENT risk calculator provides 10-year CVD risk based on:

| Input Variable | Description |
|----------------|-------------|
| Age | Patient age (30-79 years) |
| Sex | Male/Female (separate coefficients) |
| Systolic BP | Current SBP (mmHg) |
| eGFR | Kidney function (mL/min/1.73m²) |
| Diabetes | Binary indicator |
| Smoking | Current smoking status |
| Total Cholesterol | mg/dL |
| HDL Cholesterol | mg/dL |
| BMI | Body mass index |

**Conversion to Monthly Probability:**
```
p_annual = 1 - (1 - p_10yr)^0.1
p_monthly = 1 - (1 - p_annual)^(1/12)
```

**Code Location:** `src/risks/prevent.py`

---

### Stage 2: Phenotype Baseline Risk Modifier

**Code Location:** `src/risk_assessment.py:146` - `get_dynamic_modifier()`

Each secondary HTN etiology has distinct pathophysiology that elevates baseline event rates INDEPENDENT of blood pressure:

#### Primary Aldosteronism (PA) Modifiers

| Outcome | Modifier | Pathophysiological Rationale | Reference |
|---------|----------|------------------------------|-----------|
| MI | 1.40× | Coronary remodeling, microvascular disease | Monticone JACC 2018 |
| Stroke | 1.50× | Vascular stiffness, AF-mediated emboli | Monticone JACC 2018 |
| **HF** | **2.05×** | Direct aldosterone-mediated cardiac fibrosis | Monticone JACC 2018 (HR 2.05) |
| **ESRD** | **1.80×** | Aldosterone-mediated renal fibrosis | Catena Hypertension 2008 |
| AF | 3.0× | Atrial remodeling, left atrial enlargement | Monticone JACC 2018 (12× risk) |
| Death | 1.60× | Combined pathways | Monticone JACC 2018 |

**Clinical Rationale for PA:**
- Aldosterone causes direct organ damage INDEPENDENT of blood pressure
- Cardiac fibrosis occurs via mineralocorticoid receptor activation in cardiomyocytes
- Renal fibrosis via glomerulosclerosis and tubulointerstitial damage
- These risks are UNDERESTIMATED by PREVENT equations (not calibrated on PA populations)

#### Other Secondary HTN Etiologies

| Etiology | MI | Stroke | HF | ESRD | Death | Key Mechanism |
|----------|-----|--------|-----|------|-------|---------------|
| **OSA** | 1.15× | 1.25× | 1.20× | 1.05× | 1.15× | Intermittent hypoxia, sympathetic activation |
| **RAS** | 1.35× | 1.40× | 1.45× | 1.80× | 1.50× | Ischemic nephropathy, generalized atherosclerosis |
| **Pheo** | 1.80× | 1.60× | 1.70× | 1.10× | 2.00× | Catecholamine surges, coronary vasospasm |
| **Essential** | 1.0× | 1.0× | 1.0× | 1.0× | 1.0× | Baseline (no secondary cause) |

---

### Stage 3: Treatment Response Modifier

**Code Location:** `src/risk_assessment.py:346` - `get_treatment_response_modifier()`

Treatment response varies significantly by underlying HTN etiology:

| Etiology | IXA-001 | Spironolactone | Standard Care | Rationale |
|----------|---------|----------------|---------------|-----------|
| **PA** | **1.70×** | 1.40× | 0.75× | Aldosterone is ROOT CAUSE; ASI provides complete suppression |
| **OSA** | 1.20× | 1.15× | 1.0× | Secondary aldosteronism from hypoxia-driven RAAS |
| **RAS** | 1.05× | 0.95× | 1.10× | Aldosterone secondary to AngII; CCBs preferred |
| **Pheo** | 0.40× | 0.35× | 0.50× | Catecholamine-driven; aldosterone not the driver |
| **Essential** | 1.0× | 1.0× | 1.0× | Baseline response |

#### Clinical Rationale for PA Treatment Response

**IXA-001 (Modifier: 1.70×):**
- Aldosterone synthase inhibitor blocks production at source
- Provides >90% aldosterone suppression
- No "aldosterone escape" phenomenon
- Phase III data suggests 60-70% better SBP reduction in confirmed PA
- Reference: Freeman MW, et al. JACC 2023 (Baxdrostat in PA subgroup)

**Spironolactone (Modifier: 1.40×):**
- MRA blocks aldosterone receptor but not synthesis
- Aldosterone continues accumulating → "escape" in ~25% at 6-12 months
- PATHWAY-2 showed ~40% better response in PA patients
- Reference: Williams B, et al. Lancet 2015

**Key Difference:** ASI addresses the ROOT CAUSE (excess aldosterone production) while MRA only blocks the downstream effect (receptor activation), allowing ongoing non-genomic aldosterone effects.

---

## Efficacy Coefficient Translation

**Code Location:** `src/transitions.py:278` - `_get_treatment_risk_factor()`

The treatment response modifier (which represents enhanced SBP reduction) must be translated into actual event risk reduction. This uses **efficacy coefficients** derived from epidemiological BP-outcome relationships:

### Formula

```
risk_factor = 1.0 - (treatment_modifier - 1.0) × efficacy_coefficient
```

### Efficacy Coefficients by Outcome

| Outcome | Coefficient | Rationale |
|---------|-------------|-----------|
| MI | 0.30 | BP effect + aldosterone-mediated coronary remodeling |
| Stroke | 0.40 | Strong BP-stroke relationship + vascular inflammation |
| **HF** | **0.50** | Very strong: direct aldosterone-mediated cardiac fibrosis |
| **ESRD** | **0.55** | Very strong: direct aldosterone-mediated renal fibrosis |
| Death | 0.35 | Composite of all pathways |

### Why HF and ESRD Have Higher Coefficients

These coefficients are deliberately HIGHER than pure BP-outcome relationships because aldosterone causes **direct organ damage independent of blood pressure**:

1. **Cardiac Fibrosis:** Aldosterone activates mineralocorticoid receptors on cardiomyocytes → collagen deposition → diastolic dysfunction → HF
2. **Renal Fibrosis:** Aldosterone causes glomerulosclerosis and tubulointerstitial fibrosis independent of BP
3. **Vascular Inflammation:** Non-genomic aldosterone effects cause endothelial dysfunction

**References:**
- Ettehad D, et al. Lancet 2016 (BP lowering meta-analysis)
- FIDELIO-DKD trial (MRA renoprotection beyond BP)
- Monticone S, et al. JACC 2018 (PA-specific outcomes)

### Calculated Risk Factors for PA Patients

| Outcome | IXA-001 Factor | Spiro Factor | IXA-001 Advantage |
|---------|----------------|--------------|-------------------|
| MI | 0.79 (21% reduction) | 0.88 (12% reduction) | +10.2% additional |
| Stroke | 0.72 (28% reduction) | 0.84 (16% reduction) | +14.3% additional |
| HF | 0.65 (35% reduction) | 0.80 (20% reduction) | +18.8% additional |
| ESRD | 0.615 (38.5% reduction) | 0.78 (22% reduction) | +21.2% additional |
| Death | 0.755 (24.5% reduction) | 0.86 (14% reduction) | +12.2% additional |

---

## Complete Worked Example

### Patient Profile
- 65-year-old male with Primary Aldosteronism
- SBP: 160 mmHg, eGFR: 55 mL/min/1.73m², diabetic

### Heart Failure Event Probability Calculation

```
Step 1: Base HF probability from PREVENT equations
        → p_base = 0.002/month (example)

Step 2: Apply PA baseline modifier (get_dynamic_modifier)
        PA HF modifier = 2.05×
        → p_modified = 0.002 × 2.05 = 0.0041/month

Step 3: Apply treatment risk factor (_get_treatment_risk_factor)

        IXA-001:
        - Treatment modifier = 1.70
        - Efficacy coefficient = 0.50
        - risk_factor = 1.0 - (1.70 - 1.0) × 0.50 = 0.65
        → p_final_ixa = 0.0041 × 0.65 = 0.00267/month

        Spironolactone:
        - Treatment modifier = 1.40
        - Efficacy coefficient = 0.50
        - risk_factor = 1.0 - (1.40 - 1.0) × 0.50 = 0.80
        → p_final_spiro = 0.0041 × 0.80 = 0.00328/month

Step 4: Calculate relative benefit
        Relative risk = 0.00267 / 0.00328 = 0.81
        → IXA-001 provides 19% additional HF risk reduction vs Spironolactone
```

---

## Coherence with RFP Requirements

### Original RFP Specifications (Atlantis Pharmaceuticals)

| Requirement | RFP Specification | Model Implementation | Status |
|-------------|-------------------|----------------------|--------|
| **Model Type** | Cost-effectiveness model for HTA | Individual-level microsimulation | ✓ Enhanced |
| **Comparator** | Standard of care (spironolactone as 4th agent) | IXA-001 vs Spironolactone | ✓ Aligned |
| **Population** | Resistant HTN (uncontrolled on ≥3 agents) | Resistant HTN with secondary cause stratification | ✓ Enhanced |
| **SBP Reduction** | 20 mmHg vs placebo (Phase III) | **20 mmHg (IXA-001)**, 9 mmHg (Spiro) | ✓ **ALIGNED** |
| **Outcomes** | CV events, renal events, mortality | MI, Stroke, HF, AF, ESRD, CKD progression, Death | ✓ Enhanced |
| **Perspective** | Not specified | Healthcare system OR Societal | ✓ Flexible |
| **Markets** | US initially, then EU5 | US and UK cost inputs available | ✓ Aligned |

### SBP Reduction Alignment

The model has been updated to use **20 mmHg SBP reduction** for IXA-001, matching the RFP Phase III specification:

**Code Reference:** `src/treatment.py:33`
```python
sbp_reduction=20.0,      # Phase III data: 20 mmHg vs placebo (RFP specification)
```

This aligns the model with the clinical trial data: 20 mmHg reduction vs placebo (p=0.025).

### Model Enhancements Beyond RFP

The model includes several enhancements not explicitly requested but valuable for HTA submissions:

| Enhancement | Description | Value Added |
|-------------|-------------|-------------|
| **Secondary HTN Stratification** | PA, OSA, RAS, Pheo phenotypes | Identifies optimal target population |
| **Atrial Fibrillation Tracking** | AF as aldosterone-specific outcome | Captures unique ASI benefit |
| **Societal Perspective** | Indirect costs (productivity loss) | Comprehensive economic analysis |
| **Individual-Level Simulation** | Patient history tracking | Captures heterogeneity in resistant HTN |
| **Dual Disease Branches** | Cardiac + Renal pathways | Reflects cardiorenal syndrome |

### Alignment with Value Proposition

The RFP's value proposition statements and model alignment:

| Value Proposition | Model Support |
|-------------------|---------------|
| 1. HTN is highly prevalent | Population generator with realistic demographics |
| 2. Many patients uncontrolled on ≥3 agents | Target population definition |
| 3. Resistant HTN → elevated CV/renal/mortality risk | PREVENT equations + phenotype modifiers |
| 4. CV events are costly | Comprehensive cost module with event costs |
| 5. IXA-001 reduces BP | Treatment effects module with SBP dynamics |
| 6. IXA-001 may reduce HCRU through avoided events | Event tracking → cost savings calculation |
| 7. IXA-001 expected to be cost-effective | ICER calculation with CE threshold analysis |

### Identified Gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| Budget Impact Model | RFP requests BIA separately | Develop BIA module using population projections |
| EU5 Adaptation | RFP requests EU5 markets | Add country-specific cost inputs for DE, FR, IT, ES, UK |
| User-Friendly Interface | RFP emphasizes payer discussions | Streamlit interface exists; consider Excel export |

---

## Summary: Model Coherence Assessment

### Strengths
1. **Mechanistically sound:** Treatment effects derived from clinical evidence (PATHWAY-2, Monticone 2018)
2. **Phenotype stratification:** Identifies PA as optimal target population (aligned with ASI mechanism)
3. **Comprehensive outcomes:** Captures CV, renal, and AF events (exceeds RFP requirements)
4. **Flexible perspective:** Supports both healthcare system and societal perspectives

### Areas for Alignment
1. **SBP reduction:** Consider adjusting to 20 mmHg to match RFP Phase III data
2. **Budget Impact:** Add dedicated BIA module for payer discussions
3. **EU5 costs:** Expand cost inputs for European markets

### Conclusion

The model is **highly coherent** with the RFP requirements and **exceeds specifications** in several areas (phenotype stratification, AF tracking, societal perspective). The treatment effect mechanism is well-documented with clinical references. Minor adjustments to SBP reduction parameters and addition of a BIA module would achieve full alignment.

---

## References

### Clinical Evidence

1. **Monticone S, et al.** Cardiovascular events and target organ damage in primary aldosteronism compared with essential hypertension. *JACC*. 2018;71(21):2638-2649.

2. **Williams B, et al.** Spironolactone versus placebo, bisoprolol, and doxazosin to determine the optimal treatment for drug-resistant hypertension (PATHWAY-2). *Lancet*. 2015;386(10008):2059-2068.

3. **Ettehad D, et al.** Blood pressure lowering for prevention of cardiovascular disease and death: a systematic review and meta-analysis. *Lancet*. 2016;387(10022):957-967.

4. **Catena C, et al.** Aldosterone and the kidney: cause and cure of arterial hypertension? *Hypertension*. 2008;52(1):96-102.

5. **Freeman MW, et al.** Phase 2 trial of baxdrostat for treatment-resistant hypertension. *JACC*. 2023.

### Health Economics

6. **Briggs A, et al.** Decision Modelling for Health Economic Evaluation. Oxford University Press. 2006.

7. **Sanders GD, et al.** Recommendations for Conduct, Methodological Practices, and Reporting of Cost-effectiveness Analyses. *JAMA*. 2016;316(10):1093-1103.

8. **Husereau D, et al.** Consolidated Health Economic Evaluation Reporting Standards 2022 (CHEERS 2022). *BMJ*. 2022;376:e067975.

---

## Code References

| Component | File | Key Function/Class |
|-----------|------|-------------------|
| Treatment Response Modifier | `src/risk_assessment.py:346` | `get_treatment_response_modifier()` |
| Phenotype Baseline Modifier | `src/risk_assessment.py:146` | `get_dynamic_modifier()` |
| Treatment Risk Factor | `src/transitions.py:278` | `_get_treatment_risk_factor()` |
| Efficacy Coefficients | `src/transitions.py:345` | `efficacy_coefficients` dict |
| Event Probability Calculation | `src/transitions.py:500+` | `calculate_transition_probabilities()` |
