# Task Analysis: IXA-001 Cost-Effectiveness and Budget Impact Models

**Date:** February 3, 2026
**RFP Source:** Genesis Research Group - Associate Director Interview Task
**Client:** Atlantis (fictional)
**Product:** IXA-001 (Selective Aldosterone Synthase Inhibitor) for Resistant Hypertension

---

## Executive Summary

Based on the RFP requirements, Atlantis requires **two deliverables** for IXA-001 market access:

| Deliverable | Status | Details |
|-------------|--------|---------|
| **Cost-Effectiveness Model (CEA)** | ✅ **Largely Complete** | Both Python microsimulation and Excel Markov models exist |
| **Budget Impact Model (BIM)** | ❌ **Not Yet Developed** | This is the missing component |

---

## Part 1: What's Already Fulfilled (CEA Model)

### 1.1 Python Microsimulation Model

The `src/` directory contains a comprehensive individual-level microsimulation with:

| Component | Status | Implementation |
|-----------|--------|----------------|
| Model Architecture | ✅ | Individual-level state-transition (Monte Carlo) |
| Cycle Length | ✅ | Monthly cycles over 40-year horizon |
| Health States - Cardiac | ✅ | MI, Ischemic Stroke, Hemorrhagic Stroke, TIA, HF, CV Death |
| Health States - Renal | ✅ | CKD Stages 1-2, 3A, 3B, 4, ESRD, Renal Death |
| Health States - Neuro | ✅ | Normal Cognition, MCI, Dementia |
| Risk Equations | ✅ | AHA PREVENT 2024 equations |
| Treatment Effects | ✅ | IXA-001 (20 mmHg), Spironolactone (9 mmHg) |
| Cost Inputs | ✅ | US and UK perspectives |
| Utility Values | ✅ | EQ-5D based with disease-specific disutilities |
| Discounting | ✅ | 3% per annum |
| ICER Calculation | ✅ | **$61,419/QALY** (cost-effective) |

**Key Files:**
- `src/patient.py` - Patient data structure with 60+ attributes
- `src/simulation.py` - Core simulation engine
- `src/transitions.py` - Event probability calculations
- `src/treatment.py` - Treatment effects and discontinuation
- `src/costs/costs.py` - Cost parameters
- `src/utilities.py` - QALY calculations
- `src/risks/prevent.py` - PREVENT CVD risk equations

### 1.2 Excel Markov Model

The `DANRIBES_HTN_Model.xlsx` file contains a 69-sheet comprehensive model:

| Component | Status | Sheets |
|-----------|--------|--------|
| Model Structure | ✅ | Health States, Tunnel States, HTN Model Health States |
| Transition Probabilities | ✅ | Transition Probabilities, Risk eq 1, Risk eq 2 |
| Cost Inputs | ✅ | Cost Inputs (US), Cost Inputs UK, Cost input Japan |
| Utility Inputs | ✅ | QoL Inputs, Utility Inputs, Baseline Utility |
| Sensitivity Analysis | ✅ | Sensitivity Analysis, Tornado Diagram, PSA, CEAC |
| Results | ✅ | Executive Summary, Results Breakdown, Detailed results |
| Markov Traces | ✅ | Markov IXA-001, Markov SoC, Markov NoTx |

### 1.3 Harmonization Completed

Both models have been aligned on key parameters:

| Parameter | Original Discrepancy | Harmonized Value |
|-----------|---------------------|------------------|
| Diabetes Prevalence | Excel 100%, Python 35% | Both 35% |
| CV Death Rate | 10x difference | Aligned (~1-3% annual) |
| Stroke Types | Python combined | Split: Ischemic (85%) + Hemorrhagic (15%) |
| TIA State | Missing in Python | Added to both models |
| Cognitive States | Missing in Excel | Added MCI and Dementia |
| IXA-001 Discontinuation | Python 8%, Excel 12% | Both 12% |
| Risk Equation Form | Incompatible coefficients | Log-transformed in both |

### 1.4 CEA Results Summary

```
============================================================
COST-EFFECTIVENESS ANALYSIS RESULTS
============================================================

Outcome                                IXA-001       Spironolactone
--------------------------------------------------------------------
Mean Costs                     $       137,393 $           121,688
Mean QALYs                               7.389               7.134
Mean Life Years                          10.11                9.84
--------------------------------------------------------------------
Stroke (Total)                              73                 110
  - Ischemic Stroke                         60                  92
  - Hemorrhagic Stroke                      13                  18
Progression to ESRD                         52                  72
--------------------------------------------------------------------
Incremental Costs:             $        15,706
Incremental QALYs:                       0.256
ICER ($/QALY):                 $        61,419
============================================================

Interpretation: IXA-001 is cost-effective (ICER < $100,000/QALY)
```

---

## Part 2: Budget Impact Model (BIM) - Not Yet Developed

### 2.1 Why BIM is Different from CEA

| Aspect | CEA (Completed) | BIM (Needed) |
|--------|-----------------|--------------|
| **Core Question** | Is it good value for money? | What will it cost my budget? |
| **Time Horizon** | Lifetime (40 years) | Short-term (1-5 years) |
| **Perspective** | Healthcare system/Societal | Payer budget holder |
| **Key Output** | ICER ($/QALY) | Total budget impact ($) |
| **Discounting** | Yes (3%) | Usually no |
| **Population** | Hypothetical cohort | Actual plan membership |
| **Use Case** | HTA submissions (NICE, ICER) | Payer negotiations, formulary decisions |

### 2.2 BIM Requirements from RFP

From the task brief:
> "A user-friendly budget impact model that will be suitable for use in face-to-face discussions with payers initially in the US but will then be adapted for use in EU5 markets."

**Key Requirements:**
1. User-friendly interface (for non-technical payers)
2. Face-to-face discussion ready (clear visuals, scenario toggles)
3. US market first
4. Adaptable for EU5 (UK, Germany, France, Italy, Spain)

### 2.3 Proposed BIM Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    BUDGET IMPACT MODEL                       │
│                   IXA-001 in Resistant HTN                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  POPULATION  │───▶│   MARKET     │───▶│    COST      │   │
│  │    MODULE    │    │    MODULE    │    │    MODULE    │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  • Plan size         • Current Tx mix    • Drug costs       │
│  • HTN prevalence    • IXA-001 uptake    • Admin costs      │
│  • Resistant HTN %   • Displacement      • Monitoring       │
│  • Eligible patients • Scenario curves   • Avoided events   │
│                                                              │
│                           │                                  │
│                           ▼                                  │
│                  ┌──────────────────┐                        │
│                  │     OUTPUTS      │                        │
│                  └──────────────────┘                        │
│                  • Total Budget Impact                       │
│                  • Incremental Cost                          │
│                  • PMPM Impact                               │
│                  • Year-by-Year Breakdown                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 BIM Module Specifications

#### Module 1: Population Sizing

**Inputs Required:**
| Parameter | US Default | Source |
|-----------|------------|--------|
| Total plan membership | 1,000,000 lives | User input |
| Adult proportion (≥18) | 78% | Census data |
| Hypertension prevalence | 30% | NHANES |
| Resistant HTN (of HTN) | 12% | Published literature |
| Uncontrolled (of resistant) | 50% | Clinical estimates |

**Calculation:**
```
Eligible Population = Plan Size × Adult % × HTN Prevalence × Resistant % × Uncontrolled %
Example: 1,000,000 × 0.78 × 0.30 × 0.12 × 0.50 = 14,040 eligible patients
```

#### Module 2: Market Dynamics

**Current Market Shares (Baseline):**
| Treatment | Market Share |
|-----------|--------------|
| Spironolactone | 60% |
| Other MRAs (eplerenone) | 15% |
| No 4th-line therapy | 25% |

**IXA-001 Uptake Scenarios:**
| Scenario | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|----------|--------|--------|--------|--------|--------|
| Conservative | 5% | 10% | 15% | 18% | 20% |
| Moderate | 10% | 20% | 30% | 35% | 40% |
| Optimistic | 15% | 30% | 45% | 50% | 55% |

**Displacement Assumptions:**
- 70% displaced from spironolactone
- 20% displaced from other MRAs
- 10% new treatment (previously untreated)

#### Module 3: Cost Calculations

**Per-Patient Annual Costs:**

| Cost Component | IXA-001 | Spironolactone | No 4th-line |
|----------------|---------|----------------|-------------|
| Drug cost | $6,000 | $180 | $0 |
| Monitoring (K+ labs) | $180 | $240 | $120 |
| Office visits | $300 | $300 | $300 |
| AE management | $100 | $300 | $0 |
| **Subtotal** | **$6,580** | **$1,020** | **$420** |
| Avoided CV events | -$1,200* | - | - |
| **Net Annual Cost** | **$5,380** | **$1,020** | **$420** |

*Avoided events calculated from CEA model event rate differentials

#### Module 4: Budget Impact Calculation

**Formula:**
```
Annual Budget Impact =
    Σ (Patients in Treatment i × Cost of Treatment i) [New World]
  - Σ (Patients in Treatment i × Cost of Treatment i) [Current World]
```

**Key Outputs:**
1. **Total Budget Impact**: Aggregate cost difference by year
2. **Incremental PMPM**: Cost per member per month
3. **Cost per Treated Patient**: For formulary justification
4. **Break-even Analysis**: When avoided events offset drug costs

### 2.5 Recommended Excel File Structure

```
Sheet 1:  COVER & INSTRUCTIONS
          - Model overview
          - Quick start guide
          - Version control

Sheet 2:  INPUT DASHBOARD (Primary User Interface)
          - Plan size input
          - Country selector (US/UK/DE/FR/IT/ES)
          - Uptake scenario dropdown
          - IXA-001 price input
          - Time horizon selector (1-5 years)

Sheet 3:  POPULATION CALCULATIONS
          - Epidemiology inputs by country
          - Eligible population calculation
          - Subgroup breakdowns

Sheet 4:  MARKET SHARE PROJECTIONS
          - Baseline market shares
          - Uptake curves by scenario
          - Displacement matrix

Sheet 5:  DRUG COSTS
          - Unit costs by country
          - Dosing assumptions
          - Annual cost calculations

Sheet 6:  MEDICAL COSTS
          - Monitoring costs
          - AE management costs
          - Administration costs

Sheet 7:  AVOIDED EVENTS (Linked to CEA)
          - Event rates from CEA model
          - Event costs
          - Offset calculations

Sheet 8:  RESULTS DASHBOARD
          - Total budget impact (table)
          - Year-over-year chart
          - PMPM display
          - Key messages for payer discussions

Sheet 9:  SENSITIVITY ANALYSIS
          - One-way sensitivity (tornado)
          - Price threshold analysis
          - Uptake scenario comparison

Sheet 10: SCENARIO COMPARISON
          - Side-by-side scenario results
          - Best/base/worst case

Sheet 11: COUNTRY ADAPTATION
          - EU5 specific inputs
          - Currency conversion
          - Country-specific epidemiology

Sheet 12: TECHNICAL DOCUMENTATION
          - Data sources
          - Methodology
          - Limitations
          - References
```

### 2.6 BIM Implementation Roadmap

| Phase | Step | Task | Deliverable |
|-------|------|------|-------------|
| **1. Design** | 1.1 | Define BIM scope and input requirements | Input specification document |
| | 1.2 | Design user interface mockup | UI wireframe |
| | 1.3 | Identify data sources | Data source matrix |
| **2. Build** | 2.1 | Build population module | Excel population sheet |
| | 2.2 | Build market dynamics module | Uptake and displacement logic |
| | 2.3 | Build cost module | Drug + medical cost calculations |
| | 2.4 | Link to CEA for avoided events | Event rate import |
| | 2.5 | Build results dashboard | Charts and summary tables |
| **3. Validate** | 3.1 | Internal QC and testing | QC checklist |
| | 3.2 | Face validity review | Clinical advisor sign-off |
| | 3.3 | Stress testing (edge cases) | Test report |
| **4. Adapt** | 4.1 | EU5 market adaptation | Country-specific inputs |
| | 4.2 | Currency and cost localization | Multi-currency support |
| **5. Document** | 5.1 | Technical documentation | Methods report |
| | 5.2 | User guide | Quick start guide |

---

## Part 3: Summary and Recommendations

### 3.1 Current State

| Component | Completion | Quality |
|-----------|------------|---------|
| CEA - Python Microsimulation | 95% | Production-ready |
| CEA - Excel Markov Model | 90% | Functional, harmonized |
| Model Harmonization | 100% | Complete |
| Budget Impact Model | 0% | Not started |
| Proposal Document | 0% | Not started |

### 3.2 Recommended Next Steps

1. **Immediate**: Build Budget Impact Model (Excel-based)
2. **Short-term**: Develop 10-15 slide proposal presentation
3. **Medium-term**: Validate BIM with US market data
4. **Long-term**: Adapt BIM for EU5 markets

### 3.3 Key Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| BIM complexity vs. user-friendliness | High | Focus on dashboard simplicity; hide calculations |
| Data gaps for EU5 markets | Medium | Use published epidemiology; allow user overrides |
| Avoided events uncertainty | Medium | Include sensitivity analysis; conservative defaults |
| Price sensitivity | High | Build price threshold analysis; scenario comparison |

---

## Appendix: Data Sources for BIM

### Epidemiology
- NHANES (US hypertension prevalence)
- Health Survey for England (UK)
- ESC Guidelines (European prevalence)
- Published resistant HTN literature (Carey et al., Circulation 2018)

### Costs
- RED BOOK / WAC (US drug pricing)
- CMS Fee Schedule (US medical costs)
- MIMS / BNF (UK drug pricing)
- NHS Reference Costs (UK medical costs)

### Market Data
- IQVIA claims data (market shares)
- Symphony Health (prescription volumes)
- Internal Atlantis market research

---

*Report generated: February 3, 2026*
