# Cost Inputs Technical Report

## IXA-001 Hypertension Microsimulation Model

**Version:** 1.0
**Date:** February 2026
**Price Year:** 2024
**CHEERS 2022 Compliance:** Items 15, 16, 17

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Methodology](#2-methodology)
3. [Drug Costs](#3-drug-costs)
4. [Acute Event Costs](#4-acute-event-costs)
5. [Chronic Management Costs](#5-chronic-management-costs)
6. [Indirect Costs (Societal Perspective)](#6-indirect-costs-societal-perspective)
7. [Laboratory and Monitoring Costs](#7-laboratory-and-monitoring-costs)
8. [Country-Specific Cost Summary](#8-country-specific-cost-summary)
9. [PSA Distributions](#9-psa-distributions)
10. [Inflation and Currency Adjustments](#10-inflation-and-currency-adjustments)
11. [References](#11-references)

---

## 1. Executive Summary

This report documents all cost inputs used in the IXA-001 hypertension microsimulation model, including sources, price year, and probabilistic sensitivity analysis (PSA) distributions.

### Cost Categories

| Category | US (2024 USD) | UK (2024 GBP) | Key Driver |
|----------|---------------|---------------|------------|
| Drug Costs | $590-1,040/month | £448-783/month | IXA-001 vs Spironolactone |
| Acute Events | $2,100-25,000 | £850-9,000 | MI, Stroke, HF admission |
| Chronic Management | $1,200-90,000/year | £350-35,000/year | ESRD highest cost |
| Indirect (Societal) | $1,680-14,400/event | £2,240-28,800/event | Stroke disability |

### Perspective Options

| Perspective | Included Costs |
|-------------|----------------|
| **Healthcare System** | Drug costs, acute events, chronic management, laboratory |
| **Societal** | All above + absenteeism + chronic disability |

---

## 2. Methodology

### 2.1 Cost Identification

Costs were identified using a **micro-costing approach** for drugs and a **gross-costing approach** for healthcare resource use:

1. **Drug Costs:** Unit costs from national pricing databases
2. **Acute Events:** Hospital episode costs from administrative databases
3. **Chronic Management:** Published literature with inflation adjustment
4. **Indirect Costs:** Human capital approach

### 2.2 Data Sources by Country

| Country | Drug Pricing | Hospital Costs | Wage Data |
|---------|--------------|----------------|-----------|
| **US** | NADAC, SSR Health | HCUP NIS 2022 | BLS OEWS 2024 |
| **UK** | NHS Drug Tariff | NHS Reference Costs 2022-23 | ONS ASHE 2024 |

### 2.3 Price Year and Currency

| Market | Currency | Price Year | Inflation Index |
|--------|----------|------------|-----------------|
| US | USD ($) | 2024 | Medical CPI |
| UK | GBP (£) | 2024 | NHS Cost Inflation Index |

### 2.4 CHEERS 2022 Compliance

| CHEERS Item | Requirement | Compliance |
|-------------|-------------|------------|
| 15 | Methods for estimating resource quantities | ✓ Section 2.1 |
| 16 | Unit costs, currency, price date | ✓ All tables |
| 17 | Methods for productivity costs | ✓ Section 6 |

---

## 3. Drug Costs

### 3.1 Investigational Product: IXA-001

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Monthly Cost | $500 | £400 | Manufacturer WAC (placeholder) |
| Annual Cost | $6,000 | £4,800 | - |
| PSA Distribution | Gamma(μ=500, σ=100) | Gamma(μ=400, σ=80) | ±20% range |

**Notes:**
- US price reflects anticipated Wholesale Acquisition Cost (WAC)
- UK price assumes PPRS/VPAS agreement pricing
- Prices are placeholders pending commercial launch

### 3.2 Comparator: Spironolactone

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Monthly Cost | $15 | £8 | NADAC 2024 / NHS Drug Tariff |
| Annual Cost | $180 | £96 | - |
| Formulation | 25mg tablets × 30 | 25mg tablets × 28 | - |
| PSA Distribution | Gamma(μ=15, σ=5) | Gamma(μ=8, σ=2) | Generic variability |

**Reference:** NADAC (National Average Drug Acquisition Cost). Medicaid.gov. 2024.

### 3.3 Background Antihypertensive Therapy

All patients receive background therapy regardless of investigational treatment:

| Component | US Monthly | UK Monthly | Notes |
|-----------|------------|------------|-------|
| ACE inhibitor/ARB | $25 | £15 | Generic lisinopril/losartan |
| Calcium channel blocker | $30 | £15 | Generic amlodipine |
| Thiazide diuretic | $20 | £10 | Generic HCTZ/indapamide |
| **Total Background** | **$75** | **£40** | - |

**Reference:** Moran AE, et al. Cost-effectiveness of hypertension therapy. *JAMA*. 2015;312(20):2069-2082.

### 3.4 SGLT2 Inhibitors (Add-on Therapy)

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Monthly Cost | $450 | £35 | SSR Health / NHS Tariff |
| Products | Empagliflozin, Dapagliflozin | Dapagliflozin (generic) | - |
| Annual Cost | $5,400 | £420 | - |

**Notes:**
- US: Brand pricing (Jardiance®, Farxiga®) per SSR Health Net Price Report 2024
- UK: Generic dapagliflozin available since 2022 patent expiry

### 3.5 Potassium Binders

For hyperkalemia management with MRA/ASI therapy:

| Product | US Monthly | UK Monthly | Source |
|---------|------------|------------|--------|
| Patiromer (Veltassa®) | $500 | £300 | SSR Health / NHS Tariff |
| Sodium zirconium (Lokelma®) | $400 | £250 | SSR Health / NHS Tariff |
| **Model Input** | **$500** | **£300** | Higher cost (conservative) |

**Reference:** Weir MR, et al. Patiromer in patients with kidney disease and hyperkalemia. *NEJM*. 2015;372(3):211-221.

### 3.6 Total Monthly Drug Cost by Treatment Arm

| Treatment Arm | US | UK | Components |
|---------------|-----|-----|------------|
| **IXA-001** | $575 | £440 | IXA + background |
| **IXA-001 + SGLT2i** | $1,025 | £475 | IXA + background + SGLT2i |
| **Spironolactone** | $90 | £48 | Spiro + background |
| **Spironolactone + SGLT2i** | $540 | £83 | Spiro + background + SGLT2i |
| **Standard Care** | $75 | £40 | Background only |

---

## 4. Acute Event Costs

### 4.1 Myocardial Infarction (MI)

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Acute Hospitalization | $25,000 | £8,000 | HCUP DRG 280-282 / NHS EB10A-C |
| Severity Range | $22,000-28,000 | £6,000-12,000 | Without/with MCC |
| PSA Distribution | Gamma(μ=25000, σ=5000) | Gamma(μ=8000, σ=1600) | - |

**Resource Bundle (US):**
| Resource | Quantity | Unit Cost | Total |
|----------|----------|-----------|-------|
| Coronary angiography | 1 | $4,500 | $4,500 |
| PCI (70% of patients) | 0.7 | $18,000 | $12,600 |
| ICU days | 2 | $2,500 | $5,000 |
| Ward days | 3 | $1,000 | $3,000 |
| **Total** | - | - | **$25,100** |

**References:**
- Kauf TL, et al. The cost of acute myocardial infarction. *Am Heart J*. 2006;152(4):678-684.
- HCUP National Inpatient Sample 2022. AHRQ.

### 4.2 Stroke

#### 4.2.1 Ischemic Stroke

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Acute Hospitalization | $15,200 | £6,000 | HCUP DRG 61-63 / NHS AA22A-D |
| PSA Distribution | Gamma(μ=15200, σ=3000) | Gamma(μ=6000, σ=1200) | - |

**Resource Bundle (US):**
| Resource | Quantity | Unit Cost | Total |
|----------|----------|-----------|-------|
| CT/MRI imaging | 1 | $1,200 | $1,200 |
| tPA (25% eligible) | 0.25 | $8,000 | $2,000 |
| Thrombectomy (15%) | 0.15 | $25,000 | $3,750 |
| Stroke unit days | 5 | $1,500 | $7,500 |
| **Total** | - | - | **$14,450** |

#### 4.2.2 Hemorrhagic Stroke

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Acute Hospitalization | $22,500 | £9,000 | HCUP DRG 64-66 / NHS AA23A-C |
| PSA Distribution | Gamma(μ=22500, σ=5000) | Gamma(μ=9000, σ=2000) | - |

**Notes:** Higher cost due to ICU care, potential neurosurgical intervention, and longer length of stay.

**References:**
- Wang G, et al. The cost of stroke in the United States. *Stroke*. 2014;45(1):29-35.
- Qureshi AI, et al. Intracerebral haemorrhage. *Lancet*. 2009;373(9675):1632-1644.

### 4.3 Transient Ischemic Attack (TIA)

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Acute Workup | $2,100 | £850 | HCUP / NHS Rapid Access TIA |
| Setting | Emergency Department | TIA Clinic | - |
| PSA Distribution | Gamma(μ=2100, σ=500) | Gamma(μ=850, σ=200) | - |

**Resource Bundle (US):**
| Resource | Unit Cost | Total |
|----------|-----------|-------|
| ER visit | $500 | $500 |
| CT/MRI brain | $800 | $800 |
| Carotid doppler | $400 | $400 |
| Labs (BMP, CBC, lipids) | $200 | $200 |
| Neurology consult | $200 | $200 |
| **Total** | - | **$2,100** |

**Reference:** Johnston SC, et al. Short-term prognosis after emergency department diagnosis of TIA. *JAMA*. 2000;284(22):2901-2906.

### 4.4 Heart Failure Admission

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Acute Hospitalization | $18,000 | £5,500 | HCUP DRG 291-293 / NHS EB03A-D |
| Mean LOS | 5.5 days | 7.0 days | - |
| PSA Distribution | Gamma(μ=18000, σ=4000) | Gamma(μ=5500, σ=1100) | - |

**Resource Bundle (US):**
| Resource | Quantity | Unit Cost | Total |
|----------|----------|-----------|-------|
| Telemetry bed days | 5 | $2,200 | $11,000 |
| Echocardiogram | 1 | $1,500 | $1,500 |
| BNP testing | 2 | $150 | $300 |
| IV diuretics | - | $500 | $500 |
| Cardiology consult | 1 | $300 | $300 |
| Discharge planning | 1 | $400 | $400 |
| **Total** | - | - | **$14,000** |

**Note:** Actual billed costs typically higher due to facility fees; model uses mean DRG payment.

**Reference:** Heidenreich PA, et al. Forecasting the future of cardiovascular disease in the United States. *Circ Heart Fail*. 2013;126(5):1001-1010.

### 4.5 Atrial Fibrillation (New Onset)

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Acute Hospitalization | $8,500 | £3,500 | HCUP DRG 308-310 / NHS EB07A-C |
| PSA Distribution | Gamma(μ=8500, σ=2000) | Gamma(μ=3500, σ=700) | - |

**Resource Bundle:**
| Resource | Description |
|----------|-------------|
| Admission | Rate control, anticoagulation initiation |
| Cardioversion | Electrical or pharmacological (50%) |
| TEE | If cardioversion planned |
| DOAC initiation | Education and monitoring |

**Reference:** Kim MH, et al. Estimation of total incremental health care costs in patients with atrial fibrillation. *Circ Cardiovasc Qual Outcomes*. 2011;4(3):313-320.

### 4.6 Acute Event Cost Summary Table

| Event | US (2024 USD) | UK (2024 GBP) | US:UK Ratio |
|-------|---------------|---------------|-------------|
| MI | $25,000 | £8,000 | 3.1:1 |
| Ischemic Stroke | $15,200 | £6,000 | 2.5:1 |
| Hemorrhagic Stroke | $22,500 | £9,000 | 2.5:1 |
| TIA | $2,100 | £850 | 2.5:1 |
| HF Admission | $18,000 | £5,500 | 3.3:1 |
| New AF | $8,500 | £3,500 | 2.4:1 |

---

## 5. Chronic Management Costs

### 5.1 Hypertension Management

#### Controlled Hypertension (Resistant HTN, on stable therapy)

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Annual Cost | $1,200 | £350 | Sim JJ 2015 / NICE CG127 |
| PSA Distribution | Gamma(μ=1200, σ=240) | Gamma(μ=350, σ=70) | - |

**Resource Use (US):**
| Resource | Frequency | Unit Cost | Annual |
|----------|-----------|-----------|--------|
| Primary care visits | 3/year | $150 | $450 |
| Specialist visits | 1/year | $250 | $250 |
| Routine labs | 2/year | $75 | $150 |
| ECG | 1/year | $100 | $100 |
| Home BP monitor | 0.2/year | $50 | $10 |
| **Total** | - | - | **$960** |

**Note:** Resistant HTN patients have ~1.5× higher costs than general HTN population.

#### Uncontrolled Hypertension

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Annual Cost | $1,800 | £550 | Valderrama 2014 / NICE CG127 |
| PSA Distribution | Gamma(μ=1800, σ=360) | Gamma(μ=550, σ=110) | - |

**Additional Resources vs Controlled:**
- More frequent visits (4-6/year vs 3/year)
- Additional specialist referrals
- Medication titration costs
- Secondary HTN workup (if indicated)

**References:**
- Sim JJ, et al. Resistant hypertension and healthcare costs. *J Am Heart Assoc*. 2015;4(12):e002404.
- Valderrama AL, et al. Direct medical costs of uncontrolled hypertension. *J Am Soc Hypertens*. 2014;8(4):210-219.
- Daugherty SL, et al. Incidence and prognosis of resistant hypertension. *Circulation*. 2012;125(13):1635-1642.

### 5.2 Post-Event Cardiac Management

#### Post-MI (Secondary Prevention)

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Annual Cost | $5,500 | £2,200 | Zhao 2010 / Luengo-Fernandez 2006 |
| PSA Distribution | Gamma(μ=5500, σ=1100) | Gamma(μ=2200, σ=440) | - |

**Resource Bundle (Annual):**
| Resource | Frequency | US Cost |
|----------|-----------|---------|
| Cardiology visits | 2-4/year | $600 |
| Echo/stress test | 1/year | $1,200 |
| Cardiac rehab | 36 sessions | $2,000 |
| Dual antiplatelet | 12 months | $1,200 |
| Statin (high-intensity) | 12 months | $300 |
| **Total** | - | **$5,300** |

**Reference:** Zhao Z, et al. Healthcare costs and utilization for Medicare beneficiaries with acute myocardial infarction. *JMCP*. 2010;16(8):601-610.

#### Post-Stroke

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Annual Cost | $12,000 | £5,500 | Luengo-Fernandez 2013 |
| PSA Distribution | Gamma(μ=12000, σ=3000) | Gamma(μ=5500, σ=1375) | - |

**Cost Drivers:**
- Rehabilitation (inpatient and outpatient)
- Disability care (home health, assistive devices)
- Anticoagulation (if cardioembolic)
- Secondary prevention medications
- Neurologist follow-up

**Note:** Costs highly variable by stroke severity (mRS 0-2 vs 3-5).

**Reference:** Luengo-Fernandez R, et al. A population-based study of costs of stroke care in England. *Stroke*. 2013;44(5):1287-1294.

#### Chronic Heart Failure

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Annual Cost | $15,000 | £6,000 | Dunlay 2011 / NICE TA388 |
| PSA Distribution | Gamma(μ=15000, σ=4000) | Gamma(μ=6000, σ=1500) | - |

**Resource Bundle (Annual):**
| Resource | US Cost |
|----------|---------|
| HF clinic visits | $1,500 |
| Cardiology visits | $600 |
| BNP monitoring | $600 |
| Echo | $1,200 |
| GDMT medications | $3,600 |
| Hospitalizations (0.5/year) | $9,000 |
| **Total** | **$16,500** |

**Note:** HF patients average 0.5-1.0 hospitalizations/year; model uses 0.5 for prevalent HF.

**Reference:** Dunlay SM, et al. Lifetime costs of medical care after heart failure diagnosis. *Circ Heart Fail*. 2011;4(1):68-75.

#### Chronic Atrial Fibrillation

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Annual Cost | $8,500 | £2,500 | Kim 2011 / NHS Reference Costs |
| PSA Distribution | Gamma(μ=8500, σ=2000) | Gamma(μ=2500, σ=625) | - |

**Cost Components:**
| Component | US Annual | UK Annual |
|-----------|-----------|-----------|
| DOAC therapy | $6,000 | £600 |
| INR monitoring (warfarin) | $1,500 | £400 |
| Cardiology visits | $500 | £300 |
| Echo monitoring | $1,000 | £500 |
| Rate/rhythm control meds | $500 | £200 |

**Note:** Model assumes DOAC as standard; warfarin would reduce drug cost but increase monitoring.

**Reference:** Kim MH, et al. Estimation of total incremental health care costs in AF. *Circ Cardiovasc Qual Outcomes*. 2011;4(3):313-320.

### 5.3 Chronic Kidney Disease Management

| CKD Stage | eGFR Range | US Annual | UK Annual | Source |
|-----------|------------|-----------|-----------|--------|
| Stage 3a | 45-59 | $2,500 | £1,200 | Vupputuri 2014 / Kerr 2012 |
| Stage 3b | 30-44 | $4,500 | £2,200 | Vupputuri 2014 / Kerr 2012 |
| Stage 4 | 15-29 | $8,000 | £3,500 | Smith 2004 / Kerr 2012 |
| Stage 5/ESRD | <15 | $90,000 | £35,000 | USRDS 2023 / NHS Ref Costs |

#### CKD Stage 3a

**Resource Bundle:**
| Resource | Frequency | US Cost |
|----------|-----------|---------|
| Nephrology referral | Once | $400 |
| Primary care visits | 3/year | $450 |
| Labs (eGFR, uACR, K+) | 3/year | $225 |
| ACEi/ARB optimization | - | $200 |
| **Total** | - | **$1,275** |

#### CKD Stage 3b

**Additional vs Stage 3a:**
- More frequent nephrology visits
- Anemia workup (iron, B12, EPO if indicated)
- Bone mineral monitoring (Ca, Phos, PTH)
- Dietary counseling

#### CKD Stage 4 (Pre-Dialysis)

**Additional Resources:**
- Pre-dialysis education
- Vascular access creation (fistula/graft)
- Transplant evaluation (if candidate)
- More frequent labs and visits

#### ESRD (Dialysis)

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Annual Cost | $90,000 | £35,000 | USRDS 2023 / NHS 2022-23 |
| Modality | Hemodialysis (in-center) | Hemodialysis | - |
| PSA Distribution | Gamma(μ=90000, σ=15000) | Gamma(μ=35000, σ=7000) | - |

**US Cost Breakdown:**
| Component | Annual Cost |
|-----------|-------------|
| Dialysis sessions (3×/week) | $72,000 |
| Vascular access maintenance | $5,000 |
| EPO and IV iron | $8,000 |
| Hospitalization (1/year) | $5,000 |
| **Total** | **$90,000** |

**References:**
- USRDS Annual Data Report 2023. Chapter 9: Healthcare Expenditures for Persons with ESRD.
- Vupputuri S, et al. The economic burden of CKD. *Kidney Int*. 2014;86(3):619-624.
- Kerr M, et al. Estimating the financial cost of CKD to the NHS in England. *Nephrol Dial Transplant*. 2012;27(suppl_3):iii73-iii80.
- Smith DH, et al. Cost of medical care for CKD and comorbidity among enrollees in a large HMO. *Am J Kidney Dis*. 2004;44(2):261-271.

### 5.4 Chronic Management Cost Summary

| Condition | US Annual | UK Annual | Monthly (US) |
|-----------|-----------|-----------|--------------|
| Controlled HTN | $1,200 | £350 | $100 |
| Uncontrolled HTN | $1,800 | £550 | $150 |
| Post-MI | $5,500 | £2,200 | $458 |
| Post-Stroke | $12,000 | £5,500 | $1,000 |
| Chronic HF | $15,000 | £6,000 | $1,250 |
| Chronic AF | $8,500 | £2,500 | $708 |
| CKD Stage 3a | $2,500 | £1,200 | $208 |
| CKD Stage 3b | $4,500 | £2,200 | $375 |
| CKD Stage 4 | $8,000 | £3,500 | $667 |
| ESRD | $90,000 | £35,000 | $7,500 |

---

## 6. Indirect Costs (Societal Perspective)

### 6.1 Methodology

Indirect costs are estimated using the **Human Capital Approach**, which values productivity loss at market wages.

**Assumptions:**
- Working age defined as <65 years
- Working days per year: 250
- Productivity loss = 0 for patients aged ≥65

**Reference:** Drummond MF, et al. *Methods for the Economic Evaluation of Health Care Programmes*. 4th ed. Oxford. 2015. Chapter 6.

### 6.2 Wage Data

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Daily Wage (median) | $240 | £160 | BLS OEWS / ONS ASHE 2024 |
| Annual Wage (median) | $60,000 | £40,000 | - |
| Working Days/Year | 250 | 250 | - |

### 6.3 Acute Absenteeism (One-Time)

| Event | Days Lost (US) | Days Lost (UK) | US Cost | UK Cost |
|-------|----------------|----------------|---------|---------|
| Acute MI | 7 | 14 | $1,680 | £2,240 |
| Stroke | 30 | 60 | $7,200 | £9,600 |
| TIA | 3 | 3 | $720 | £480 |
| HF Admission | 5 | 10 | $1,200 | £1,600 |

**Note:** UK estimates higher due to longer statutory sick leave provisions.

**References:**
- Greiner W, et al. Productivity loss after acute coronary syndrome. *Eur J Health Econ*. 2004;5(4):324-330.
- Dewilde S, et al. Work absence and return after stroke. *BMJ Open*. 2017;7(6):e014163.
- Liao L, et al. Costs and resource use in heart failure. *JACC Heart Fail*. 2007;49(5):523-531.

### 6.4 Chronic Disability (Annual)

| Condition | Disability Multiplier (US) | Disability Multiplier (UK) | US Annual Loss | UK Annual Loss |
|-----------|---------------------------|---------------------------|----------------|----------------|
| Post-Stroke | 20% | 30% | $12,000 | £12,000 |
| Chronic HF | 15% | 20% | $9,000 | £8,000 |

**Calculation:**
```
Annual Disability Cost = Annual Wage × Disability Multiplier
US Post-Stroke = $60,000 × 0.20 = $12,000/year
UK Post-Stroke = £40,000 × 0.30 = £12,000/year
```

**References:**
- Tanaka E, et al. Long-term economic impact of stroke in Japan. *Stroke*. 2011;42(11):3034-3039.
- Heidenreich PA, et al. Economic impact of heart failure. *Circulation*. 2013;127(10):1132-1143.
- Patel A, et al. Productivity costs of stroke in the United Kingdom. *Stroke*. 2020;51(5):1429-1436.

### 6.5 Total Indirect Cost by Event (Working-Age Patient)

| Event | Acute + Year 1 Chronic (US) | Acute + Year 1 Chronic (UK) |
|-------|------------------------------|------------------------------|
| MI | $1,680 | £2,240 |
| Stroke | $7,200 + $12,000 = $19,200 | £9,600 + £12,000 = £21,600 |
| HF | $1,200 + $9,000 = $10,200 | £1,600 + £8,000 = £9,600 |

---

## 7. Laboratory and Monitoring Costs

### 7.1 Potassium Monitoring

| Parameter | US | UK | Source |
|-----------|-----|-----|--------|
| Serum K+ (BMP) | $15 | £3 | Medicare CLFS / NHS DAPS08 |
| PSA Distribution | Gamma(μ=15, σ=5) | Gamma(μ=3, σ=1) | - |

**Monitoring Frequency by Treatment:**
| Treatment | Frequency | US Annual | UK Annual |
|-----------|-----------|-----------|-----------|
| IXA-001 | Monthly × 3, then quarterly | $105 | £21 |
| Spironolactone | Monthly × 3, then quarterly | $105 | £21 |
| Standard Care | Quarterly | $60 | £12 |

### 7.2 Other Laboratory Tests

| Test | US Cost | UK Cost | Frequency |
|------|---------|---------|-----------|
| Basic Metabolic Panel | $15 | £3 | Per protocol |
| eGFR/Creatinine | $10 | £2 | Per renal state |
| Lipid Panel | $25 | £5 | Annual |
| HbA1c (diabetics) | $20 | £4 | Quarterly |

---

## 8. Country-Specific Cost Summary

### 8.1 US Costs (2024 USD)

| Category | Cost | Notes |
|----------|------|-------|
| **Drug Costs (Monthly)** | | |
| IXA-001 + background | $575 | |
| Spironolactone + background | $90 | |
| SGLT2i add-on | $450 | |
| **Acute Events** | | |
| MI | $25,000 | |
| Ischemic stroke | $15,200 | |
| Hemorrhagic stroke | $22,500 | |
| HF admission | $18,000 | |
| New AF | $8,500 | |
| TIA | $2,100 | |
| **Annual Management** | | |
| Controlled HTN | $1,200 | |
| Post-MI | $5,500 | |
| Post-stroke | $12,000 | |
| Chronic HF | $15,000 | |
| Chronic AF | $8,500 | |
| CKD Stage 4 | $8,000 | |
| ESRD | $90,000 | |
| **Indirect (working age)** | | |
| Daily wage | $240 | |
| Stroke disability | $12,000/yr | |

### 8.2 UK Costs (2024 GBP)

| Category | Cost | Notes |
|----------|------|-------|
| **Drug Costs (Monthly)** | | |
| IXA-001 + background | £440 | |
| Spironolactone + background | £48 | |
| SGLT2i add-on | £35 | Generic |
| **Acute Events** | | |
| MI | £8,000 | |
| Ischemic stroke | £6,000 | |
| Hemorrhagic stroke | £9,000 | |
| HF admission | £5,500 | |
| New AF | £3,500 | |
| TIA | £850 | |
| **Annual Management** | | |
| Controlled HTN | £350 | |
| Post-MI | £2,200 | |
| Post-stroke | £5,500 | |
| Chronic HF | £6,000 | |
| Chronic AF | £2,500 | |
| CKD Stage 4 | £3,500 | |
| ESRD | £35,000 | |
| **Indirect (working age)** | | |
| Daily wage | £160 | |
| Stroke disability | £12,000/yr | |

---

## 9. PSA Distributions

### 9.1 Distribution Selection Rationale

| Parameter Type | Distribution | Rationale |
|----------------|--------------|-----------|
| Costs | Gamma | Non-negative, right-skewed |
| Probabilities | Beta | Bounded 0-1 |
| Days lost | Uniform | Range-based estimates |
| Disability % | Beta | Bounded 0-1 |

### 9.2 Gamma Distribution Parameterization

For costs with mean μ and standard deviation σ:

$$\alpha = \frac{\mu^2}{\sigma^2}, \quad \beta = \frac{\sigma^2}{\mu}$$

### 9.3 Complete PSA Parameter Table

| Parameter | Base Case | Distribution | α | β (or SD) |
|-----------|-----------|--------------|---|-----------|
| **Drug Costs (US)** | | | | |
| IXA-001 monthly | $500 | Gamma | 25 | 20 |
| Spironolactone monthly | $15 | Gamma | 9 | 1.67 |
| SGLT2i monthly | $450 | Gamma | 25 | 18 |
| Background monthly | $75 | Gamma | 9 | 8.33 |
| K+ binder monthly | $500 | Gamma | 25 | 20 |
| **Acute Events (US)** | | | | |
| MI acute | $25,000 | Gamma | 25 | 1,000 |
| Ischemic stroke | $15,200 | Gamma | 25.7 | 592 |
| Hemorrhagic stroke | $22,500 | Gamma | 20.25 | 1,111 |
| HF admission | $18,000 | Gamma | 20.25 | 889 |
| AF acute | $8,500 | Gamma | 18.06 | 471 |
| TIA | $2,100 | Gamma | 17.64 | 119 |
| **Annual Costs (US)** | | | | |
| Controlled HTN | $1,200 | Gamma | 25 | 48 |
| Uncontrolled HTN | $1,800 | Gamma | 25 | 72 |
| Post-MI | $5,500 | Gamma | 30.25 | 182 |
| Post-stroke | $12,000 | Gamma | 16 | 750 |
| Chronic HF | $15,000 | Gamma | 14.06 | 1,067 |
| ESRD | $90,000 | Gamma | 36 | 2,500 |
| **Indirect Costs** | | | | |
| Daily wage (US) | $240 | Gamma | 36 | 6.67 |
| Absenteeism MI (days) | 7 | Uniform | 5 | 14 |
| Absenteeism stroke (days) | 30 | Uniform | 14 | 60 |
| Disability stroke | 0.20 | Beta | 20 | 80 |
| Disability HF | 0.15 | Beta | 15 | 85 |

---

## 10. Inflation and Currency Adjustments

### 10.1 Inflation Indices

| Country | Index | 2022→2024 Factor |
|---------|-------|------------------|
| US | Medical CPI | 1.08 |
| UK | NHS Cost Inflation Index | 1.06 |

### 10.2 Historical Cost Adjustment

For costs from prior years:

$$Cost_{2024} = Cost_{original} \times \frac{Index_{2024}}{Index_{original}}$$

### 10.3 Currency Conversion (if needed)

| Conversion | Rate | Source |
|------------|------|--------|
| USD → GBP | 0.80 | Average 2024 exchange rate |
| GBP → USD | 1.25 | Average 2024 exchange rate |

**Note:** Country-specific costs are preferred over currency conversion to capture local practice patterns and pricing.

---

## 11. References

### Primary Cost Sources

1. **HCUP National Inpatient Sample**. Healthcare Cost and Utilization Project (HCUP). Agency for Healthcare Research and Quality. 2022.

2. **NHS Reference Costs 2022-23**. NHS England. https://www.england.nhs.uk/costing-in-the-nhs/national-cost-collection/

3. **NADAC (National Average Drug Acquisition Cost)**. Medicaid.gov. 2024. https://data.medicaid.gov/nadac

4. **NHS Drug Tariff**. NHS Business Services Authority. April 2024.

5. **USRDS Annual Data Report 2023**. United States Renal Data System. Chapter 9: Healthcare Expenditures.

6. **Medicare Clinical Laboratory Fee Schedule**. CMS. 2024.

### Published Literature

7. **Moran AE**, et al. Cost-effectiveness of hypertension therapy according to 2014 guidelines. *JAMA*. 2015;312(20):2069-2082.

8. **Sim JJ**, et al. Resistant hypertension and healthcare costs. *J Am Heart Assoc*. 2015;4(12):e002404.

9. **Valderrama AL**, et al. Direct medical costs of uncontrolled hypertension. *J Am Soc Hypertens*. 2014;8(4):210-219.

10. **Kauf TL**, et al. The cost of acute myocardial infarction in the 1990s. *Am Heart J*. 2006;152(4):678-684.

11. **Wang G**, et al. The cost of stroke in the United States. *Stroke*. 2014;45(1):29-35.

12. **Luengo-Fernandez R**, et al. Population-based study of costs of stroke care in England. *Stroke*. 2013;44(5):1287-1294.

13. **Heidenreich PA**, et al. Forecasting the future of cardiovascular disease. *Circ Heart Fail*. 2013;126(5):1001-1010.

14. **Dunlay SM**, et al. Lifetime costs of medical care after heart failure diagnosis. *Circ Heart Fail*. 2011;4(1):68-75.

15. **Kim MH**, et al. Estimation of total incremental health care costs in atrial fibrillation. *Circ Cardiovasc Qual Outcomes*. 2011;4(3):313-320.

16. **Vupputuri S**, et al. The economic burden of chronic kidney disease. *Kidney Int*. 2014;86(3):619-624.

17. **Kerr M**, et al. Estimating the financial cost of chronic kidney disease to the NHS in England. *Nephrol Dial Transplant*. 2012;27(suppl_3):iii73-iii80.

18. **Smith DH**, et al. Cost of medical care for chronic kidney disease. *Am J Kidney Dis*. 2004;44(2):261-271.

### Indirect Cost References

19. **Greiner W**, et al. Productivity loss after acute coronary syndrome. *Eur J Health Econ*. 2004;5(4):324-330.

20. **Dewilde S**, et al. Work absence and return to work after stroke. *BMJ Open*. 2017;7(6):e014163.

21. **Tanaka E**, et al. Long-term economic impact of stroke. *Stroke*. 2011;42(11):3034-3039.

22. **Patel A**, et al. Productivity costs of stroke in the United Kingdom. *Stroke*. 2020;51(5):1429-1436.

### Methodology

23. **Husereau D**, et al. Consolidated Health Economic Evaluation Reporting Standards 2022 (CHEERS 2022). *BMJ*. 2022;376:e067975.

24. **Drummond MF**, et al. *Methods for the Economic Evaluation of Health Care Programmes*. 4th ed. Oxford University Press. 2015.

25. **NICE**. Guide to the methods of technology appraisal 2013 (PMG9).

---

## Appendix A: Code Reference

**File:** `src/costs/costs.py`

| Function | Purpose |
|----------|---------|
| `get_drug_cost()` | Calculate monthly drug cost by treatment arm |
| `get_total_cost()` | Sum chronic management costs by state |
| `get_event_cost()` | Return one-time acute event cost |
| `get_productivity_loss()` | Calculate chronic disability cost |
| `get_acute_absenteeism_cost()` | Calculate one-time absenteeism cost |

---

## Appendix B: Cost Input Checklist for Model Updates

When updating cost inputs:

- [ ] Verify price year matches model documentation
- [ ] Update inflation factors if using historical data
- [ ] Check NADAC/NHS Tariff for current drug prices
- [ ] Verify HCUP/NHS Reference Cost codes still apply
- [ ] Update PSA distributions if uncertainty changes
- [ ] Document all sources in this report
- [ ] Run model validation after cost updates

---

**Document Version:** 1.0
**Last Updated:** February 2026
**Author:** HEOR Technical Documentation Team
