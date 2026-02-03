"""
Streamlit Web Interface for Hypertension Microsimulation Model.

Cost-Effectiveness Analysis comparing IXA-001 vs Spironolactone
in adults with resistant hypertension.
"""

import streamlit as st
import numpy as np
import pandas as pd
from typing import Optional, Dict, List
from io import BytesIO
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import run_cea, CEAResults, Treatment
from src.population import PopulationParams, PopulationGenerator
from src.patient import Patient, CardiacState, RenalState, NeuroState
from src.simulation import Simulation, SimulationConfig, SimulationResults
from src.risk_assessment import BaselineRiskProfile

# Page configuration
st.set_page_config(
    page_title="CEA Microsimulation - IXA-001",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1F4E79;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .risk-high { color: #dc3545; font-weight: bold; }
    .risk-moderate { color: #fd7e14; }
    .risk-low { color: #28a745; }
</style>
""", unsafe_allow_html=True)


def format_currency(value: float, symbol: str = "$") -> str:
    """Format currency value."""
    if abs(value) >= 1_000_000:
        return f"{symbol}{value/1_000_000:,.1f}M"
    elif abs(value) >= 1_000:
        return f"{symbol}{value/1_000:,.1f}K"
    else:
        return f"{symbol}{value:,.0f}"


def run_simulation_with_params(
    n_patients: int,
    time_horizon: int,
    perspective: str,
    seed: int,
    discount_rate: float,
    pop_params: PopulationParams
) -> tuple:
    """Run the CEA simulation with custom population parameters."""

    # Update population params
    pop_params.n_patients = n_patients
    pop_params.seed = seed

    # Create simulation config
    config = SimulationConfig(
        n_patients=n_patients,
        time_horizon_months=time_horizon * 12,
        seed=seed,
        cost_perspective=perspective,
        discount_rate=discount_rate,
        show_progress=False
    )

    sim = Simulation(config)

    # Generate population for IXA-001 arm
    generator = PopulationGenerator(pop_params)
    patients_ixa = generator.generate()

    # Store baseline risk profiles before simulation
    baseline_profiles_ixa = [p.baseline_risk_profile for p in patients_ixa]

    results_ixa = sim.run(patients_ixa, Treatment.IXA_001)

    # Regenerate for comparator arm with same seed
    pop_params_comp = PopulationParams(
        n_patients=n_patients, seed=seed,
        age_mean=pop_params.age_mean, age_sd=pop_params.age_sd,
        prop_male=pop_params.prop_male,
        sbp_mean=pop_params.sbp_mean, sbp_sd=pop_params.sbp_sd,
        egfr_mean=pop_params.egfr_mean, egfr_sd=pop_params.egfr_sd,
        uacr_mean=pop_params.uacr_mean, uacr_sd=pop_params.uacr_sd,
        total_chol_mean=pop_params.total_chol_mean, hdl_chol_mean=pop_params.hdl_chol_mean,
        bmi_mean=pop_params.bmi_mean, bmi_sd=pop_params.bmi_sd,
        diabetes_prev=pop_params.diabetes_prev, smoker_prev=pop_params.smoker_prev,
        dyslipidemia_prev=pop_params.dyslipidemia_prev,
        prior_mi_prev=pop_params.prior_mi_prev, prior_stroke_prev=pop_params.prior_stroke_prev,
        heart_failure_prev=pop_params.heart_failure_prev,
        adherence_prob=pop_params.adherence_prob,
    )
    generator_comp = PopulationGenerator(pop_params_comp)
    patients_spi = generator_comp.generate()
    baseline_profiles_spi = [p.baseline_risk_profile for p in patients_spi]

    results_spi = sim.run(patients_spi, Treatment.SPIRONOLACTONE)

    cea = CEAResults(intervention=results_ixa, comparator=results_spi)
    cea.calculate_icer()

    return cea, patients_ixa, patients_spi, baseline_profiles_ixa


def analyze_subgroups(patients: List[Patient], results: SimulationResults, profiles: List[BaselineRiskProfile]) -> Dict:
    """Analyze results by subgroups."""
    subgroup_data = {
        'framingham': {'Low': [], 'Borderline': [], 'Intermediate': [], 'High': []},
        'kdigo': {'Low': [], 'Moderate': [], 'High': [], 'Very High': []},
        'gcua': {'I': [], 'II': [], 'III': [], 'IV': [], 'Moderate': [], 'Low': []},
        'age': {'<60': [], '60-70': [], '70-80': [], '80+': []},
        'ckd_stage': {'Stage 1-2': [], 'Stage 3a': [], 'Stage 3b': [], 'Stage 4': [], 'ESRD': []},
    }

    for i, (patient, profile) in enumerate(zip(patients, profiles)):
        patient_data = results.patient_results[i] if i < len(results.patient_results) else {}

        # Framingham category
        if profile.framingham_category:
            if profile.framingham_category in subgroup_data['framingham']:
                subgroup_data['framingham'][profile.framingham_category].append(patient_data)

        # KDIGO risk level
        if profile.kdigo_risk_level:
            if profile.kdigo_risk_level in subgroup_data['kdigo']:
                subgroup_data['kdigo'][profile.kdigo_risk_level].append(patient_data)

        # GCUA phenotype
        if profile.gcua_phenotype:
            if profile.gcua_phenotype in subgroup_data['gcua']:
                subgroup_data['gcua'][profile.gcua_phenotype].append(patient_data)

        # Age groups
        age = patient_data.get('age', patient.age)
        if age < 60:
            subgroup_data['age']['<60'].append(patient_data)
        elif age < 70:
            subgroup_data['age']['60-70'].append(patient_data)
        elif age < 80:
            subgroup_data['age']['70-80'].append(patient_data)
        else:
            subgroup_data['age']['80+'].append(patient_data)

        # CKD stage
        renal = patient_data.get('renal_state', patient.renal_state.value if hasattr(patient.renal_state, 'value') else str(patient.renal_state))
        if 'stage_1_2' in str(renal).lower() or 'ckd_stage_1_2' in str(renal).lower():
            subgroup_data['ckd_stage']['Stage 1-2'].append(patient_data)
        elif 'stage_3a' in str(renal).lower():
            subgroup_data['ckd_stage']['Stage 3a'].append(patient_data)
        elif 'stage_3b' in str(renal).lower():
            subgroup_data['ckd_stage']['Stage 3b'].append(patient_data)
        elif 'stage_4' in str(renal).lower():
            subgroup_data['ckd_stage']['Stage 4'].append(patient_data)
        elif 'esrd' in str(renal).lower():
            subgroup_data['ckd_stage']['ESRD'].append(patient_data)

    return subgroup_data


def generate_excel_report(cea: CEAResults, pop_params: PopulationParams,
                          subgroup_data: Dict, currency: str) -> BytesIO:
    """Generate comprehensive Excel report."""
    import tempfile
    import os
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils.dataframe import dataframe_to_rows

    wb = Workbook()

    # Style definitions
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # ========== Sheet 1: Executive Summary ==========
    ws = wb.active
    ws.title = "Executive Summary"

    summary_data = [
        ["Cost-Effectiveness Analysis: IXA-001 vs Spironolactone"],
        [""],
        ["Key Results"],
        ["Metric", "Value"],
        ["Incremental Costs", f"{currency}{cea.incremental_costs:,.0f}"],
        ["Incremental QALYs", f"{cea.incremental_qalys:.3f}"],
        ["ICER", f"{currency}{cea.icer:,.0f}/QALY" if cea.icer else "Dominant"],
        [""],
        ["Population Characteristics"],
        ["Mean Age", f"{pop_params.age_mean:.0f} years"],
        ["% Male", f"{pop_params.prop_male*100:.0f}%"],
        ["Mean SBP", f"{pop_params.sbp_mean:.0f} mmHg"],
        ["Mean eGFR", f"{pop_params.egfr_mean:.0f} mL/min/1.73m²"],
        ["Diabetes Prevalence", f"{pop_params.diabetes_prev*100:.0f}%"],
        ["Prior MI Prevalence", f"{pop_params.prior_mi_prev*100:.0f}%"],
        ["Heart Failure Prevalence", f"{pop_params.heart_failure_prev*100:.0f}%"],
    ]

    for row in summary_data:
        ws.append(row)

    ws['A1'].font = Font(bold=True, size=16)
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 25

    # ========== Sheet 2: Detailed Outcomes ==========
    ws2 = wb.create_sheet("Detailed Outcomes")

    outcomes = [
        ["Outcome", "IXA-001", "Spironolactone", "Difference"],
        ["Mean Total Costs", f"{currency}{cea.intervention.mean_costs:,.0f}",
         f"{currency}{cea.comparator.mean_costs:,.0f}", f"{currency}{cea.incremental_costs:,.0f}"],
        ["Mean Direct Costs", f"{currency}{cea.intervention.mean_costs - cea.intervention.total_indirect_costs/cea.intervention.n_patients:,.0f}",
         f"{currency}{cea.comparator.mean_costs - cea.comparator.total_indirect_costs/cea.comparator.n_patients:,.0f}", "-"],
        ["Mean Indirect Costs", f"{currency}{cea.intervention.total_indirect_costs/cea.intervention.n_patients:,.0f}",
         f"{currency}{cea.comparator.total_indirect_costs/cea.comparator.n_patients:,.0f}", "-"],
        ["Mean QALYs", f"{cea.intervention.mean_qalys:.3f}", f"{cea.comparator.mean_qalys:.3f}", f"{cea.incremental_qalys:.3f}"],
        ["Mean Life Years", f"{cea.intervention.mean_life_years:.2f}", f"{cea.comparator.mean_life_years:.2f}",
         f"{cea.intervention.mean_life_years - cea.comparator.mean_life_years:.2f}"],
        [""],
        ["Clinical Events (per 1000)"],
        ["MI Events", cea.intervention.mi_events, cea.comparator.mi_events,
         cea.intervention.mi_events - cea.comparator.mi_events],
        ["Stroke Events", cea.intervention.stroke_events, cea.comparator.stroke_events,
         cea.intervention.stroke_events - cea.comparator.stroke_events],
        ["  - Ischemic", cea.intervention.ischemic_stroke_events, cea.comparator.ischemic_stroke_events, "-"],
        ["  - Hemorrhagic", cea.intervention.hemorrhagic_stroke_events, cea.comparator.hemorrhagic_stroke_events, "-"],
        ["TIA Events", cea.intervention.tia_events, cea.comparator.tia_events, "-"],
        ["Heart Failure", cea.intervention.hf_events, cea.comparator.hf_events, "-"],
        ["CV Deaths", cea.intervention.cv_deaths, cea.comparator.cv_deaths, "-"],
        ["Non-CV Deaths", cea.intervention.non_cv_deaths, cea.comparator.non_cv_deaths, "-"],
        [""],
        ["Renal Events"],
        ["CKD Stage 4 Progression", cea.intervention.ckd_4_events, cea.comparator.ckd_4_events, "-"],
        ["ESRD Events", cea.intervention.esrd_events, cea.comparator.esrd_events, "-"],
        [""],
        ["Cognitive Events"],
        ["Dementia Cases", cea.intervention.dementia_cases, cea.comparator.dementia_cases, "-"],
        [""],
        ["Medication & Adherence"],
        ["SGLT2 Users", cea.intervention.sglt2_users, cea.comparator.sglt2_users, "-"],
        [""],
        ["BP Control"],
        ["Time Controlled (patient-years)", f"{cea.intervention.time_controlled:.1f}",
         f"{cea.comparator.time_controlled:.1f}", "-"],
        ["Time Uncontrolled (patient-years)", f"{cea.intervention.time_uncontrolled:.1f}",
         f"{cea.comparator.time_uncontrolled:.1f}", "-"],
    ]

    for row in outcomes:
        ws2.append(row)

    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill

    for col in ['A', 'B', 'C', 'D']:
        ws2.column_dimensions[col].width = 25

    # ========== Sheet 3: Subgroup Analysis ==========
    ws3 = wb.create_sheet("Subgroup Analysis")

    ws3.append(["Subgroup Analysis by Risk Category"])
    ws3.append([""])

    # Framingham subgroups
    ws3.append(["By Framingham CVD Risk"])
    ws3.append(["Category", "N Patients", "Mean Costs", "Mean QALYs"])
    for cat, patients in subgroup_data['framingham'].items():
        n = len(patients)
        if n > 0:
            mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients]) if patients else 0
            mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients]) if patients else 0
            ws3.append([cat, n, f"{currency}{mean_costs:,.0f}", f"{mean_qalys:.3f}"])

    ws3.append([""])
    ws3.append(["By KDIGO Risk Level"])
    ws3.append(["Category", "N Patients", "Mean Costs", "Mean QALYs"])
    for cat, patients in subgroup_data['kdigo'].items():
        n = len(patients)
        if n > 0:
            mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients]) if patients else 0
            mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients]) if patients else 0
            ws3.append([cat, n, f"{currency}{mean_costs:,.0f}", f"{mean_qalys:.3f}"])

    ws3.append([""])
    ws3.append(["By GCUA Phenotype"])
    ws3.append(["Phenotype", "N Patients", "Mean Costs", "Mean QALYs"])
    for cat, patients in subgroup_data['gcua'].items():
        n = len(patients)
        if n > 0:
            mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients]) if patients else 0
            mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients]) if patients else 0
            ws3.append([cat, n, f"{currency}{mean_costs:,.0f}", f"{mean_qalys:.3f}"])

    ws3.append([""])
    ws3.append(["By Age Group"])
    ws3.append(["Age Group", "N Patients", "Mean Costs", "Mean QALYs"])
    for cat, patients in subgroup_data['age'].items():
        n = len(patients)
        if n > 0:
            mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients]) if patients else 0
            mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients]) if patients else 0
            ws3.append([cat, n, f"{currency}{mean_costs:,.0f}", f"{mean_qalys:.3f}"])

    ws3.column_dimensions['A'].width = 20
    ws3.column_dimensions['B'].width = 15
    ws3.column_dimensions['C'].width = 15
    ws3.column_dimensions['D'].width = 15

    # ========== Sheet 4: WTP Analysis ==========
    ws4 = wb.create_sheet("WTP Analysis")

    ws4.append(["Willingness-to-Pay Analysis"])
    ws4.append([""])
    ws4.append(["WTP Threshold", "NMB IXA-001", "NMB Spironolactone", "Incremental NMB", "Cost-Effective?"])

    for wtp in [0, 25000, 50000, 75000, 100000, 150000, 200000]:
        nmb_ixa = cea.intervention.mean_qalys * wtp - cea.intervention.mean_costs
        nmb_spi = cea.comparator.mean_qalys * wtp - cea.comparator.mean_costs
        inc_nmb = nmb_ixa - nmb_spi
        ce = "Yes" if inc_nmb > 0 else "No"
        ws4.append([f"{currency}{wtp:,}/QALY", f"{currency}{nmb_ixa:,.0f}",
                   f"{currency}{nmb_spi:,.0f}", f"{currency}{inc_nmb:,.0f}", ce])

    for cell in ws4[3]:
        cell.font = header_font
        cell.fill = header_fill

    for col in ['A', 'B', 'C', 'D', 'E']:
        ws4.column_dimensions[col].width = 20

    # ========== Sheet 5: Population Parameters ==========
    ws5 = wb.create_sheet("Population Parameters")

    params_data = [
        ["Population Configuration"],
        [""],
        ["Demographics"],
        ["Parameter", "Value"],
        ["Mean Age (years)", pop_params.age_mean],
        ["Age SD", pop_params.age_sd],
        ["% Male", f"{pop_params.prop_male*100:.0f}%"],
        ["Mean BMI", pop_params.bmi_mean],
        [""],
        ["Clinical Parameters"],
        ["Mean SBP (mmHg)", pop_params.sbp_mean],
        ["SBP SD", pop_params.sbp_sd],
        ["Mean eGFR (mL/min/1.73m²)", pop_params.egfr_mean],
        ["eGFR SD", pop_params.egfr_sd],
        ["Mean UACR (mg/g)", pop_params.uacr_mean],
        ["Mean Total Cholesterol", pop_params.total_chol_mean],
        ["Mean HDL Cholesterol", pop_params.hdl_chol_mean],
        [""],
        ["Comorbidity Prevalence"],
        ["Diabetes", f"{pop_params.diabetes_prev*100:.0f}%"],
        ["Current Smoker", f"{pop_params.smoker_prev*100:.0f}%"],
        ["Dyslipidemia", f"{pop_params.dyslipidemia_prev*100:.0f}%"],
        ["Prior MI", f"{pop_params.prior_mi_prev*100:.0f}%"],
        ["Prior Stroke", f"{pop_params.prior_stroke_prev*100:.0f}%"],
        ["Heart Failure", f"{pop_params.heart_failure_prev*100:.0f}%"],
        [""],
        ["Treatment"],
        ["Mean Antihypertensives", pop_params.mean_antihypertensives],
        ["Adherence Probability", f"{pop_params.adherence_prob*100:.0f}%"],
    ]

    for row in params_data:
        ws5.append(row)

    ws5.column_dimensions['A'].width = 30
    ws5.column_dimensions['B'].width = 20

    # Save to BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def display_key_metrics(cea: CEAResults, currency: str):
    """Display key CEA metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Incremental Costs",
            value=format_currency(cea.incremental_costs, currency),
        )

    with col2:
        st.metric(
            label="Incremental QALYs",
            value=f"{cea.incremental_qalys:.3f}",
        )

    with col3:
        if cea.icer is not None:
            st.metric(
                label="ICER",
                value=f"{currency}{cea.icer:,.0f}/QALY",
            )
        else:
            st.metric(
                label="ICER",
                value="Dominant" if cea.incremental_qalys > 0 else "Dominated",
            )

    with col4:
        if cea.icer is not None:
            if cea.icer < 50000:
                interpretation = "Highly Cost-Effective"
            elif cea.icer < 100000:
                interpretation = "Cost-Effective"
            elif cea.icer < 150000:
                interpretation = "Borderline"
            else:
                interpretation = "Not Cost-Effective"
        else:
            interpretation = "Dominant" if cea.incremental_qalys > 0 else "Dominated"

        st.metric(
            label="Interpretation",
            value=interpretation,
        )


def display_detailed_costs(cea: CEAResults, currency: str):
    """Display detailed cost breakdown."""
    st.markdown("### Cost Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**IXA-001**")
        direct_ixa = cea.intervention.mean_costs - (cea.intervention.total_indirect_costs / cea.intervention.n_patients)
        indirect_ixa = cea.intervention.total_indirect_costs / cea.intervention.n_patients

        cost_data_ixa = pd.DataFrame({
            'Category': ['Direct Costs', 'Indirect Costs (Productivity)', 'Total'],
            'Amount': [f"{currency}{direct_ixa:,.0f}", f"{currency}{indirect_ixa:,.0f}",
                      f"{currency}{cea.intervention.mean_costs:,.0f}"]
        })
        st.dataframe(cost_data_ixa, hide_index=True, use_container_width=True)

    with col2:
        st.markdown("**Spironolactone**")
        direct_spi = cea.comparator.mean_costs - (cea.comparator.total_indirect_costs / cea.comparator.n_patients)
        indirect_spi = cea.comparator.total_indirect_costs / cea.comparator.n_patients

        cost_data_spi = pd.DataFrame({
            'Category': ['Direct Costs', 'Indirect Costs (Productivity)', 'Total'],
            'Amount': [f"{currency}{direct_spi:,.0f}", f"{currency}{indirect_spi:,.0f}",
                      f"{currency}{cea.comparator.mean_costs:,.0f}"]
        })
        st.dataframe(cost_data_spi, hide_index=True, use_container_width=True)


def display_outcomes_table(cea: CEAResults, currency: str):
    """Display outcomes comparison table."""
    st.markdown("### Clinical Outcomes Comparison")

    data = {
        "Outcome": [
            "Mean Total Costs",
            "Mean QALYs",
            "Mean Life Years",
            "MI Events (per 1000)",
            "Stroke Events (per 1000)",
            "  - Ischemic Stroke",
            "  - Hemorrhagic Stroke",
            "TIA Events (per 1000)",
            "Heart Failure Events",
            "CV Deaths",
            "Non-CV Deaths",
            "CKD Stage 4 Progression",
            "ESRD Events",
            "Dementia Cases",
        ],
        "IXA-001": [
            f"{currency}{cea.intervention.mean_costs:,.0f}",
            f"{cea.intervention.mean_qalys:.3f}",
            f"{cea.intervention.mean_life_years:.2f}",
            cea.intervention.mi_events,
            cea.intervention.stroke_events,
            cea.intervention.ischemic_stroke_events,
            cea.intervention.hemorrhagic_stroke_events,
            cea.intervention.tia_events,
            cea.intervention.hf_events,
            cea.intervention.cv_deaths,
            cea.intervention.non_cv_deaths,
            cea.intervention.ckd_4_events,
            cea.intervention.esrd_events,
            cea.intervention.dementia_cases,
        ],
        "Spironolactone": [
            f"{currency}{cea.comparator.mean_costs:,.0f}",
            f"{cea.comparator.mean_qalys:.3f}",
            f"{cea.comparator.mean_life_years:.2f}",
            cea.comparator.mi_events,
            cea.comparator.stroke_events,
            cea.comparator.ischemic_stroke_events,
            cea.comparator.hemorrhagic_stroke_events,
            cea.comparator.tia_events,
            cea.comparator.hf_events,
            cea.comparator.cv_deaths,
            cea.comparator.non_cv_deaths,
            cea.comparator.ckd_4_events,
            cea.comparator.esrd_events,
            cea.comparator.dementia_cases,
        ],
        "Difference": [
            f"{currency}{cea.incremental_costs:,.0f}",
            f"{cea.incremental_qalys:.3f}",
            f"{cea.intervention.mean_life_years - cea.comparator.mean_life_years:.2f}",
            cea.intervention.mi_events - cea.comparator.mi_events,
            cea.intervention.stroke_events - cea.comparator.stroke_events,
            cea.intervention.ischemic_stroke_events - cea.comparator.ischemic_stroke_events,
            cea.intervention.hemorrhagic_stroke_events - cea.comparator.hemorrhagic_stroke_events,
            cea.intervention.tia_events - cea.comparator.tia_events,
            cea.intervention.hf_events - cea.comparator.hf_events,
            cea.intervention.cv_deaths - cea.comparator.cv_deaths,
            cea.intervention.non_cv_deaths - cea.comparator.non_cv_deaths,
            cea.intervention.ckd_4_events - cea.comparator.ckd_4_events,
            cea.intervention.esrd_events - cea.comparator.esrd_events,
            cea.intervention.dementia_cases - cea.comparator.dementia_cases,
        ],
    }

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def display_medication_adherence(cea: CEAResults):
    """Display medication and adherence metrics."""
    st.markdown("### Medication & BP Control")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("SGLT2 Users (IXA-001)", cea.intervention.sglt2_users)
    with col2:
        st.metric("SGLT2 Users (Spiro)", cea.comparator.sglt2_users)
    with col3:
        pct_controlled_ixa = (cea.intervention.time_controlled /
                              (cea.intervention.time_controlled + cea.intervention.time_uncontrolled) * 100
                              if (cea.intervention.time_controlled + cea.intervention.time_uncontrolled) > 0 else 0)
        st.metric("% Time BP Controlled (IXA)", f"{pct_controlled_ixa:.1f}%")
    with col4:
        pct_controlled_spi = (cea.comparator.time_controlled /
                              (cea.comparator.time_controlled + cea.comparator.time_uncontrolled) * 100
                              if (cea.comparator.time_controlled + cea.comparator.time_uncontrolled) > 0 else 0)
        st.metric("% Time BP Controlled (Spiro)", f"{pct_controlled_spi:.1f}%")


def display_subgroup_analysis(subgroup_data: Dict, currency: str):
    """Display subgroup analysis results."""
    st.markdown("### Subgroup Analysis")

    tab1, tab2, tab3, tab4 = st.tabs(["Framingham Risk", "KDIGO Risk", "GCUA Phenotype", "Age Group"])

    with tab1:
        st.markdown("**By Framingham CVD Risk Category**")
        fram_data = []
        for cat in ['Low', 'Borderline', 'Intermediate', 'High']:
            patients = subgroup_data['framingham'][cat]
            n = len(patients)
            if n > 0:
                mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients])
                mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients])
                fram_data.append({
                    'Category': cat,
                    'N Patients': n,
                    'Mean Costs': f"{currency}{mean_costs:,.0f}",
                    'Mean QALYs': f"{mean_qalys:.3f}"
                })
        if fram_data:
            st.dataframe(pd.DataFrame(fram_data), hide_index=True, use_container_width=True)
        else:
            st.info("No Framingham risk data available")

    with tab2:
        st.markdown("**By KDIGO Risk Level**")
        kdigo_data = []
        for cat in ['Low', 'Moderate', 'High', 'Very High']:
            patients = subgroup_data['kdigo'][cat]
            n = len(patients)
            if n > 0:
                mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients])
                mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients])
                kdigo_data.append({
                    'Risk Level': cat,
                    'N Patients': n,
                    'Mean Costs': f"{currency}{mean_costs:,.0f}",
                    'Mean QALYs': f"{mean_qalys:.3f}"
                })
        if kdigo_data:
            st.dataframe(pd.DataFrame(kdigo_data), hide_index=True, use_container_width=True)
        else:
            st.info("No KDIGO risk data available")

    with tab3:
        st.markdown("**By GCUA Phenotype** (Age 60+, eGFR >60)")
        gcua_data = []
        phenotype_names = {
            'I': 'Accelerated Ager', 'II': 'Silent Renal',
            'III': 'Vascular Dominant', 'IV': 'Senescent',
            'Moderate': 'Moderate Risk', 'Low': 'Low Risk'
        }
        for cat in ['I', 'II', 'III', 'IV', 'Moderate', 'Low']:
            patients = subgroup_data['gcua'][cat]
            n = len(patients)
            if n > 0:
                mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients])
                mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients])
                gcua_data.append({
                    'Phenotype': f"{cat} ({phenotype_names.get(cat, '')})",
                    'N Patients': n,
                    'Mean Costs': f"{currency}{mean_costs:,.0f}",
                    'Mean QALYs': f"{mean_qalys:.3f}"
                })
        if gcua_data:
            st.dataframe(pd.DataFrame(gcua_data), hide_index=True, use_container_width=True)
        else:
            st.info("No GCUA phenotype data available (requires age 60+, eGFR >60)")

    with tab4:
        st.markdown("**By Age Group**")
        age_data = []
        for cat in ['<60', '60-70', '70-80', '80+']:
            patients = subgroup_data['age'][cat]
            n = len(patients)
            if n > 0:
                mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients])
                mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients])
                age_data.append({
                    'Age Group': cat,
                    'N Patients': n,
                    'Mean Costs': f"{currency}{mean_costs:,.0f}",
                    'Mean QALYs': f"{mean_qalys:.3f}"
                })
        if age_data:
            st.dataframe(pd.DataFrame(age_data), hide_index=True, use_container_width=True)


def display_patient_trajectories(patients: List[Patient], results: SimulationResults):
    """Display individual patient trajectory analysis."""
    st.markdown("### Patient Trajectories")

    if not results.patient_results:
        st.warning("No individual patient data available")
        return

    # Sample of patient outcomes
    sample_size = min(100, len(results.patient_results))
    sample_data = results.patient_results[:sample_size]

    # Create trajectory summary
    trajectory_df = pd.DataFrame(sample_data)

    if not trajectory_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Outcome Distribution (Sample)**")
            if 'cumulative_costs' in trajectory_df.columns:
                st.bar_chart(trajectory_df['cumulative_costs'].head(50))
                st.caption("Cumulative Costs by Patient")

        with col2:
            if 'cumulative_qalys' in trajectory_df.columns:
                st.bar_chart(trajectory_df['cumulative_qalys'].head(50))
                st.caption("Cumulative QALYs by Patient")

        # State distribution
        st.markdown("**Final State Distribution**")
        col3, col4 = st.columns(2)

        with col3:
            if 'cardiac_state' in trajectory_df.columns:
                cardiac_counts = trajectory_df['cardiac_state'].value_counts()
                st.dataframe(cardiac_counts.reset_index().rename(
                    columns={'index': 'Cardiac State', 'cardiac_state': 'Count'}
                ), hide_index=True)

        with col4:
            if 'renal_state' in trajectory_df.columns:
                renal_counts = trajectory_df['renal_state'].value_counts()
                st.dataframe(renal_counts.reset_index().rename(
                    columns={'index': 'Renal State', 'renal_state': 'Count'}
                ), hide_index=True)


def display_risk_stratification(profiles: List[BaselineRiskProfile]):
    """Display baseline risk stratification summary."""
    st.markdown("### Baseline Risk Stratification")

    # Count by category
    framingham_counts = {'Low': 0, 'Borderline': 0, 'Intermediate': 0, 'High': 0}
    kdigo_counts = {'Low': 0, 'Moderate': 0, 'High': 0, 'Very High': 0}
    gcua_counts = {'I': 0, 'II': 0, 'III': 0, 'IV': 0, 'Moderate': 0, 'Low': 0}

    for p in profiles:
        if p.framingham_category in framingham_counts:
            framingham_counts[p.framingham_category] += 1
        if p.kdigo_risk_level in kdigo_counts:
            kdigo_counts[p.kdigo_risk_level] += 1
        if p.gcua_phenotype in gcua_counts:
            gcua_counts[p.gcua_phenotype] += 1

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Framingham CVD Risk**")
        fram_df = pd.DataFrame([
            {'Category': k, 'N': v, '%': f"{v/len(profiles)*100:.1f}%"}
            for k, v in framingham_counts.items() if v > 0
        ])
        if not fram_df.empty:
            st.dataframe(fram_df, hide_index=True)

    with col2:
        st.markdown("**KDIGO Risk Level**")
        kdigo_df = pd.DataFrame([
            {'Level': k, 'N': v, '%': f"{v/len(profiles)*100:.1f}%"}
            for k, v in kdigo_counts.items() if v > 0
        ])
        if not kdigo_df.empty:
            st.dataframe(kdigo_df, hide_index=True)

    with col3:
        st.markdown("**GCUA Phenotype**")
        gcua_df = pd.DataFrame([
            {'Phenotype': k, 'N': v, '%': f"{v/len(profiles)*100:.1f}%"}
            for k, v in gcua_counts.items() if v > 0
        ])
        if not gcua_df.empty:
            st.dataframe(gcua_df, hide_index=True)
        else:
            st.info("GCUA applies to age 60+, eGFR >60")


def display_event_charts(cea: CEAResults):
    """Display event comparison charts."""
    st.markdown("### Event Comparison Charts")

    col1, col2 = st.columns(2)

    with col1:
        cardiac_data = pd.DataFrame({
            "Event": ["MI", "Stroke", "TIA", "HF", "CV Death"],
            "IXA-001": [
                cea.intervention.mi_events,
                cea.intervention.stroke_events,
                cea.intervention.tia_events,
                cea.intervention.hf_events,
                cea.intervention.cv_deaths,
            ],
            "Spironolactone": [
                cea.comparator.mi_events,
                cea.comparator.stroke_events,
                cea.comparator.tia_events,
                cea.comparator.hf_events,
                cea.comparator.cv_deaths,
            ],
        })
        st.bar_chart(cardiac_data.set_index("Event"), use_container_width=True)
        st.caption("Cardiac Events (per 1000 patients)")

    with col2:
        renal_data = pd.DataFrame({
            "Event": ["CKD Stage 4", "ESRD"],
            "IXA-001": [
                cea.intervention.ckd_4_events,
                cea.intervention.esrd_events,
            ],
            "Spironolactone": [
                cea.comparator.ckd_4_events,
                cea.comparator.esrd_events,
            ],
        })
        st.bar_chart(renal_data.set_index("Event"), use_container_width=True)
        st.caption("Renal Events (per 1000 patients)")


def display_ce_plane(cea: CEAResults, currency: str):
    """Display cost-effectiveness plane."""
    st.markdown("### Cost-Effectiveness Plane")

    chart_data = pd.DataFrame({
        "Incremental QALYs": [cea.incremental_qalys],
        "Incremental Costs": [cea.incremental_costs],
    })

    st.scatter_chart(chart_data, x="Incremental QALYs", y="Incremental Costs", use_container_width=True)

    if cea.incremental_qalys > 0 and cea.incremental_costs < 0:
        st.success("**Quadrant: Southeast (Dominant)** - IXA-001 is more effective and less costly")
    elif cea.incremental_qalys > 0 and cea.incremental_costs > 0:
        st.info(f"**Quadrant: Northeast** - IXA-001 is more effective but more costly (ICER: {currency}{cea.icer:,.0f}/QALY)")
    elif cea.incremental_qalys < 0 and cea.incremental_costs < 0:
        st.warning("**Quadrant: Southwest** - IXA-001 is less effective but less costly")
    else:
        st.error("**Quadrant: Northwest (Dominated)** - IXA-001 is less effective and more costly")


def display_wtp_analysis(cea: CEAResults, currency: str):
    """Display willingness-to-pay analysis."""
    st.markdown("### Willingness-to-Pay Analysis")

    wtp_thresholds = [0, 25000, 50000, 75000, 100000, 150000, 200000]

    data = []
    for wtp in wtp_thresholds:
        nmb_ixa = cea.intervention.mean_qalys * wtp - cea.intervention.mean_costs
        nmb_spi = cea.comparator.mean_qalys * wtp - cea.comparator.mean_costs
        incremental_nmb = nmb_ixa - nmb_spi
        ce = "Yes" if incremental_nmb > 0 else "No"

        data.append({
            "WTP Threshold": f"{currency}{wtp:,}/QALY",
            "NMB IXA-001": f"{currency}{nmb_ixa:,.0f}",
            "NMB Spironolactone": f"{currency}{nmb_spi:,.0f}",
            "Incremental NMB": f"{currency}{incremental_nmb:,.0f}",
            "Cost-Effective?": ce,
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    """Main application entry point."""
    # Header
    st.markdown('<p class="main-header">Cost-Effectiveness Microsimulation</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">IXA-001 vs Spironolactone in Resistant Hypertension</p>', unsafe_allow_html=True)

    # ============== SIDEBAR ==============
    st.sidebar.markdown("## Simulation Parameters")

    n_patients = st.sidebar.slider(
        "Cohort Size (per arm)", min_value=100, max_value=5000, value=1000, step=100,
        help="Number of patients to simulate in each treatment arm"
    )

    time_horizon = st.sidebar.slider(
        "Time Horizon (years)", min_value=5, max_value=50, value=40, step=5,
        help="Duration of the simulation"
    )

    perspective = st.sidebar.selectbox(
        "Cost Perspective", options=["US", "UK"], index=0,
        help="Healthcare system perspective for costs"
    )
    currency = "$" if perspective == "US" else "£"

    discount_rate = st.sidebar.slider(
        "Discount Rate (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.5,
        help="Annual discount rate for costs and QALYs"
    ) / 100.0

    seed = st.sidebar.number_input(
        "Random Seed", min_value=1, max_value=99999, value=42,
        help="Seed for reproducibility"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Population Configuration")

    # Demographics
    with st.sidebar.expander("Demographics", expanded=False):
        age_mean = st.slider("Mean Age (years)", 40, 80, 62)
        age_sd = st.slider("Age SD", 5, 20, 10)
        prop_male = st.slider("% Male", 0, 100, 55) / 100.0
        bmi_mean = st.slider("Mean BMI", 20.0, 45.0, 30.5, step=0.5)

    # Clinical Parameters
    with st.sidebar.expander("Clinical Parameters", expanded=False):
        st.markdown("**Blood Pressure**")
        sbp_mean = st.slider("Mean SBP (mmHg)", 140, 180, 155)
        sbp_sd = st.slider("SBP SD", 5, 25, 15)

        st.markdown("**Renal Function**")
        egfr_mean = st.slider("Mean eGFR", 30, 90, 68)
        egfr_sd = st.slider("eGFR SD", 10, 30, 20)
        uacr_mean = st.slider("Mean UACR (mg/g)", 10, 300, 50)

        st.markdown("**Lipids**")
        total_chol_mean = st.slider("Mean Total Cholesterol", 150, 280, 200)
        hdl_chol_mean = st.slider("Mean HDL Cholesterol", 30, 80, 48)

    # Cardiac History
    with st.sidebar.expander("Cardiac History (%)", expanded=False):
        prior_mi_prev = st.slider("Prior MI", 0, 30, 10) / 100.0
        prior_stroke_prev = st.slider("Prior Stroke", 0, 20, 5) / 100.0
        heart_failure_prev = st.slider("Heart Failure", 0, 25, 8) / 100.0

    # Comorbidities
    with st.sidebar.expander("Comorbidities (%)", expanded=False):
        diabetes_prev = st.slider("Diabetes", 0, 60, 35) / 100.0
        smoker_prev = st.slider("Current Smoker", 0, 40, 15) / 100.0
        dyslipidemia_prev = st.slider("Dyslipidemia", 0, 80, 60) / 100.0

    # Treatment & Adherence
    with st.sidebar.expander("Treatment & Adherence", expanded=False):
        adherence_prob = st.slider("Treatment Adherence (%)", 50, 100, 75) / 100.0
        mean_antihypertensives = st.slider("Mean Antihypertensives", 2, 6, 4)

    # Build population params
    pop_params = PopulationParams(
        n_patients=n_patients, seed=seed,
        age_mean=age_mean, age_sd=age_sd,
        prop_male=prop_male,
        sbp_mean=sbp_mean, sbp_sd=sbp_sd,
        egfr_mean=egfr_mean, egfr_sd=egfr_sd,
        uacr_mean=uacr_mean, uacr_sd=80.0,
        total_chol_mean=total_chol_mean, hdl_chol_mean=hdl_chol_mean,
        bmi_mean=bmi_mean, bmi_sd=5.5,
        diabetes_prev=diabetes_prev, smoker_prev=smoker_prev,
        dyslipidemia_prev=dyslipidemia_prev,
        prior_mi_prev=prior_mi_prev, prior_stroke_prev=prior_stroke_prev,
        heart_failure_prev=heart_failure_prev,
        adherence_prob=adherence_prob,
        mean_antihypertensives=mean_antihypertensives,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.markdown("""
    This microsimulation model evaluates the cost-effectiveness of
    **IXA-001** (aldosterone synthase inhibitor) compared to
    **Spironolactone** in adults with resistant hypertension.

    **Outcomes modeled:**
    - Cardiovascular events (MI, stroke, HF)
    - Renal progression (CKD, ESRD)
    - Cognitive decline (MCI, Dementia)
    - Mortality (CV and non-CV)
    - Quality-adjusted life years (QALYs)
    """)

    # Run simulation button
    if st.sidebar.button("Run Simulation", type="primary", use_container_width=True):
        with st.spinner(f"Running microsimulation ({n_patients:,} patients per arm, {time_horizon} years)..."):
            cea_results, patients_ixa, patients_spi, profiles = run_simulation_with_params(
                n_patients, time_horizon, perspective, seed, discount_rate, pop_params
            )
            st.session_state.cea_results = cea_results
            st.session_state.currency = currency
            st.session_state.pop_params = pop_params
            st.session_state.patients_ixa = patients_ixa
            st.session_state.profiles = profiles
            st.session_state.subgroup_data = analyze_subgroups(patients_ixa, cea_results.intervention, profiles)

    # ============== MAIN CONTENT ==============
    if "cea_results" in st.session_state:
        cea = st.session_state.cea_results
        currency = st.session_state.currency
        pp = st.session_state.pop_params
        profiles = st.session_state.profiles
        subgroup_data = st.session_state.subgroup_data

        # Key metrics
        display_key_metrics(cea, currency)

        st.divider()

        # Tabs for different views
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 Outcomes",
            "💰 Costs",
            "📈 Charts",
            "🎯 Subgroups",
            "🔬 Risk Stratification",
            "👤 Trajectories",
            "📥 Export"
        ])

        with tab1:
            display_outcomes_table(cea, currency)
            st.divider()
            display_medication_adherence(cea)

        with tab2:
            display_detailed_costs(cea, currency)
            st.divider()
            display_wtp_analysis(cea, currency)

        with tab3:
            display_event_charts(cea)
            st.divider()
            display_ce_plane(cea, currency)

        with tab4:
            display_subgroup_analysis(subgroup_data, currency)

        with tab5:
            display_risk_stratification(profiles)

        with tab6:
            display_patient_trajectories(st.session_state.patients_ixa, cea.intervention)

        with tab7:
            st.markdown("### Export Results")
            st.markdown("Download comprehensive Excel report with all analysis results.")

            excel_buffer = generate_excel_report(cea, pp, subgroup_data, currency)
            st.download_button(
                label="Download Excel Report",
                data=excel_buffer,
                file_name="CEA_Microsimulation_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

            st.markdown("""
            **Report Contents:**
            - Executive Summary
            - Detailed Outcomes (Direct/Indirect Costs, Events)
            - Subgroup Analysis (Framingham, KDIGO, GCUA, Age)
            - Willingness-to-Pay Analysis
            - Population Parameters
            """)

        # Summary box
        st.divider()
        st.markdown("### Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            **Simulation Parameters:**
            - Cohort size: {n_patients:,} patients per arm
            - Time horizon: {time_horizon} years
            - Perspective: {perspective}
            - Discount rate: {discount_rate*100:.1f}% per annum
            """)

        with col2:
            st.markdown(f"""
            **Population Characteristics:**
            - Mean age: {pp.age_mean:.0f} years (SD {pp.age_sd:.0f})
            - Male: {pp.prop_male*100:.0f}%
            - Mean SBP: {pp.sbp_mean:.0f} mmHg
            - Mean eGFR: {pp.egfr_mean:.0f} mL/min
            - Diabetes: {pp.diabetes_prev*100:.0f}%
            - Prior MI: {pp.prior_mi_prev*100:.0f}%
            - Heart Failure: {pp.heart_failure_prev*100:.0f}%
            """)

        with col3:
            events_avoided = cea.comparator.stroke_events - cea.intervention.stroke_events
            mi_avoided = cea.comparator.mi_events - cea.intervention.mi_events

            st.markdown(f"""
            **Key Findings:**
            - Strokes avoided: {events_avoided:,}
            - MIs avoided: {mi_avoided:,}
            - Additional QALYs: {cea.incremental_qalys:.2f}
            - Additional cost: {currency}{cea.incremental_costs:,.0f}
            """)

    else:
        st.info("👈 Configure parameters and click **Run Simulation** to start the analysis.")


if __name__ == "__main__":
    main()
