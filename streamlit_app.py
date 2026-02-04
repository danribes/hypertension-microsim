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


def run_simulation_with_progress(
    n_patients: int,
    time_horizon: int,
    perspective: str,
    seed: int,
    discount_rate: float,
    pop_params: PopulationParams,
    status_container
) -> tuple:
    """Run the CEA simulation with progress indicators."""
    import time

    # Update population params
    pop_params.n_patients = n_patients
    pop_params.seed = seed

    total_cycles = time_horizon * 12  # Monthly cycles

    # Create simulation config
    config = SimulationConfig(
        n_patients=n_patients,
        time_horizon_months=total_cycles,
        seed=seed,
        cost_perspective=perspective,
        discount_rate=discount_rate,
        show_progress=False
    )

    # ===== Phase 1: Generate IXA-001 Population =====
    status_container.update(label="Phase 1/5: Generating IXA-001 population...", state="running")
    generator = PopulationGenerator(pop_params)
    patients_ixa = generator.generate()
    baseline_profiles_ixa = [p.baseline_risk_profile for p in patients_ixa]

    # ===== Phase 2: Run IXA-001 Simulation =====
    status_container.update(label="Phase 2/5: Simulating IXA-001 arm...", state="running")
    progress_bar = status_container.progress(0, text="Initializing simulation...")

    sim = Simulation(config)

    # Run simulation with progress updates
    results_ixa = _run_simulation_with_callback(
        sim, patients_ixa, Treatment.IXA_001, total_cycles, progress_bar, "IXA-001"
    )

    # ===== Phase 3: Generate Spironolactone Population =====
    status_container.update(label="Phase 3/5: Generating Spironolactone population...", state="running")
    progress_bar.progress(0, text="Generating comparator population...")

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

    # ===== Phase 4: Run Spironolactone Simulation =====
    status_container.update(label="Phase 4/5: Simulating Spironolactone arm...", state="running")
    progress_bar.progress(0, text="Initializing comparator simulation...")

    results_spi = _run_simulation_with_callback(
        sim, patients_spi, Treatment.SPIRONOLACTONE, total_cycles, progress_bar, "Spironolactone"
    )

    # ===== Phase 5: Calculate Results =====
    status_container.update(label="Phase 5/5: Calculating cost-effectiveness...", state="running")
    progress_bar.progress(100, text="Computing ICER and outcomes...")

    cea = CEAResults(intervention=results_ixa, comparator=results_spi)
    cea.calculate_icer()

    status_container.update(label="Simulation complete!", state="complete")

    return cea, patients_ixa, patients_spi, baseline_profiles_ixa


def _run_simulation_with_callback(sim, patients, treatment, total_cycles, progress_bar, arm_name):
    """Run simulation with progress updates."""
    from src.patient import Treatment as TreatmentEnum

    results = SimulationResults(treatment=treatment, n_patients=len(patients))

    # Assign treatment to all patients
    for patient in patients:
        sim.treatment_mgr.assign_treatment(patient, treatment)
        if patient.on_sglt2_inhibitor:
            results.sglt2_users += 1

    n_cycles = int(sim.config.time_horizon_months / sim.config.cycle_length_months)
    update_interval = max(1, n_cycles // 20)  # Update progress ~20 times

    for cycle in range(n_cycles):
        # Update progress bar periodically
        if cycle % update_interval == 0:
            progress_pct = int((cycle / n_cycles) * 100)
            years_simulated = cycle / 12
            progress_bar.progress(
                progress_pct,
                text=f"Simulating {arm_name}: Year {years_simulated:.1f}/{sim.config.time_horizon_months/12:.0f} ({progress_pct}%)"
            )

        for patient in patients:
            if not patient.is_alive:
                continue

            # Check adherence
            if sim.adherence_transition.check_adherence_change(patient):
                sim.treatment_mgr.update_effect_for_adherence(patient)

            # Safety checks for Spironolactone
            is_quarterly = (int(patient.time_in_simulation) % 3 == 0)
            if is_quarterly and patient.treatment == TreatmentEnum.SPIRONOLACTONE:
                patient.accrue_costs(sim.costs.lab_test_cost_k)
                if sim.treatment_mgr.check_safety_stop_rules(patient):
                    sim.treatment_mgr.assign_treatment(patient, TreatmentEnum.STANDARD_CARE)
                    patient.hyperkalemia_history += 1

            # Neuro progression
            old_neuro = patient.neuro_state
            sim.neuro_transition.check_neuro_progression(patient)
            if patient.neuro_state != old_neuro and patient.neuro_state.value == "dementia":
                results.dementia_cases += 1

            # Cardiac events
            probs = sim.transition_calc.calculate_transitions(patient)
            new_event = sim.transition_calc.sample_event(patient, probs)

            if new_event:
                if new_event == "NON_CV_DEATH":
                    results.non_cv_deaths += 1
                    patient.cardiac_state = "non_cv_death"
                else:
                    sim._record_event(new_event, results)
                    patient.transition_cardiac(new_event)

                    from src.costs.costs import get_event_cost, get_acute_absenteeism_cost
                    event_cost = get_event_cost(new_event.value, sim.costs)
                    absenteeism_cost = get_acute_absenteeism_cost(new_event.value, sim.costs, patient.age)

                    years = patient.time_in_simulation / 12
                    discount = 1 / ((1 + sim.config.discount_rate) ** years)

                    patient.accrue_costs(event_cost * discount)
                    results.total_costs += event_cost * discount
                    results.total_indirect_costs += absenteeism_cost * discount

            if not patient.is_alive:
                continue

            # Accrue outcomes
            sim._accrue_outcomes(patient, results)

            # Update SBP
            patient.update_sbp(patient._treatment_effect_mmhg, sim.rng)

            # Advance time and check renal
            old_renal = patient.renal_state
            patient.advance_time(sim.config.cycle_length_months)

            from src.patient import RenalState
            if patient.renal_state != old_renal:
                if patient.renal_state == RenalState.ESRD:
                    results.esrd_events += 1
                elif patient.renal_state == RenalState.CKD_STAGE_4:
                    results.ckd_4_events += 1

            # Check discontinuation
            if sim.treatment_mgr.check_discontinuation(patient):
                patient.treatment = TreatmentEnum.STANDARD_CARE

    # Final progress update
    progress_bar.progress(100, text=f"{arm_name} simulation complete!")

    # Store patient results
    for patient in patients:
        results.patient_results.append(patient.to_dict())

    results.calculate_means()
    return results


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
    """Generate comprehensive Excel report with charts and formatting."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle
    from openpyxl.chart import BarChart, PieChart, Reference, LineChart
    from openpyxl.chart.label import DataLabelList
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # ===== Style definitions =====
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    subheader_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
    alt_row_fill = PatternFill(start_color="D6DCE4", end_color="D6DCE4", fill_type="solid")
    highlight_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    warning_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    title_font = Font(bold=True, size=18, color="1F4E79")
    subtitle_font = Font(bold=True, size=14, color="2E75B6")
    border = Border(
        left=Side(style='thin', color='B4B4B4'),
        right=Side(style='thin', color='B4B4B4'),
        top=Side(style='thin', color='B4B4B4'),
        bottom=Side(style='thin', color='B4B4B4')
    )
    center_align = Alignment(horizontal='center', vertical='center')
    currency_sym = currency

    def apply_table_style(ws, start_row, end_row, num_cols):
        """Apply alternating row colors and borders to a table."""
        for row_idx in range(start_row, end_row + 1):
            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = border
                if row_idx == start_row:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = center_align
                elif (row_idx - start_row) % 2 == 0:
                    cell.fill = alt_row_fill

    # ========== Sheet 1: Executive Summary ==========
    ws = wb.active
    ws.title = "Executive Summary"

    # Title
    ws.merge_cells('A1:D1')
    ws['A1'] = "Cost-Effectiveness Analysis Report"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:D2')
    ws['A2'] = "IXA-001 vs Spironolactone in Resistant Hypertension"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center')

    # Key Results Box
    ws['A4'] = "KEY RESULTS"
    ws['A4'].font = Font(bold=True, size=12, color="FFFFFF")
    ws['A4'].fill = header_fill
    ws.merge_cells('A4:B4')

    results_data = [
        ["Incremental Costs", f"{currency_sym}{cea.incremental_costs:,.0f}"],
        ["Incremental QALYs", f"{cea.incremental_qalys:.3f}"],
        ["ICER", f"{currency_sym}{cea.icer:,.0f}/QALY" if cea.icer else "Dominant"],
        ["Interpretation", "Cost-Effective" if (cea.icer and cea.icer < 100000) or cea.incremental_qalys > 0 else "Review Required"],
    ]

    for i, (label, value) in enumerate(results_data, start=5):
        ws.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws.cell(row=i, column=2, value=value)
        if "Dominant" in str(value) or "Cost-Effective" in str(value):
            ws.cell(row=i, column=2).fill = highlight_fill

    # Population Summary
    ws['A10'] = "POPULATION CHARACTERISTICS"
    ws['A10'].font = Font(bold=True, size=12, color="FFFFFF")
    ws['A10'].fill = header_fill
    ws.merge_cells('A10:B10')

    pop_data = [
        ["Cohort Size", f"{pop_params.n_patients:,} per arm"],
        ["Mean Age", f"{pop_params.age_mean:.0f} years (SD {pop_params.age_sd:.0f})"],
        ["% Male", f"{pop_params.prop_male*100:.0f}%"],
        ["Mean SBP", f"{pop_params.sbp_mean:.0f} mmHg"],
        ["Mean eGFR", f"{pop_params.egfr_mean:.0f} mL/min/1.73m²"],
        ["Diabetes", f"{pop_params.diabetes_prev*100:.0f}%"],
        ["Prior MI", f"{pop_params.prior_mi_prev*100:.0f}%"],
        ["Heart Failure", f"{pop_params.heart_failure_prev*100:.0f}%"],
    ]

    for i, (label, value) in enumerate(pop_data, start=11):
        ws.cell(row=i, column=1, value=label)
        ws.cell(row=i, column=2, value=value)
        if i % 2 == 0:
            ws.cell(row=i, column=1).fill = alt_row_fill
            ws.cell(row=i, column=2).fill = alt_row_fill

    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 25

    # ========== Sheet 2: Clinical Events with Chart ==========
    ws2 = wb.create_sheet("Clinical Events")

    ws2['A1'] = "Clinical Events Comparison"
    ws2['A1'].font = title_font

    # Events table for chart
    events_header = ["Event", "IXA-001", "Spironolactone"]
    events_data = [
        ["MI", cea.intervention.mi_events, cea.comparator.mi_events],
        ["Stroke", cea.intervention.stroke_events, cea.comparator.stroke_events],
        ["TIA", cea.intervention.tia_events, cea.comparator.tia_events],
        ["Heart Failure", cea.intervention.hf_events, cea.comparator.hf_events],
        ["CV Death", cea.intervention.cv_deaths, cea.comparator.cv_deaths],
        ["CKD Stage 4", cea.intervention.ckd_4_events, cea.comparator.ckd_4_events],
        ["ESRD", cea.intervention.esrd_events, cea.comparator.esrd_events],
    ]

    ws2.append([])  # Row 2
    ws2.append(events_header)  # Row 3
    for row in events_data:
        ws2.append(row)

    apply_table_style(ws2, 3, 3 + len(events_data), 3)

    # Create bar chart for events
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "clustered"
    chart.title = "Clinical Events per 1000 Patients"
    chart.y_axis.title = "Number of Events"
    chart.x_axis.title = "Event Type"
    chart.style = 10

    data = Reference(ws2, min_col=2, min_row=3, max_col=3, max_row=3 + len(events_data))
    cats = Reference(ws2, min_col=1, min_row=4, max_row=3 + len(events_data))
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.shape = 4
    chart.width = 15
    chart.height = 10

    ws2.add_chart(chart, "E3")

    # Events avoided summary
    ws2['A14'] = "EVENTS AVOIDED WITH IXA-001"
    ws2['A14'].font = subtitle_font

    avoided_data = [
        ["Event", "Events Avoided"],
        ["Strokes", cea.comparator.stroke_events - cea.intervention.stroke_events],
        ["MIs", cea.comparator.mi_events - cea.intervention.mi_events],
        ["CV Deaths", cea.comparator.cv_deaths - cea.intervention.cv_deaths],
        ["ESRD Cases", cea.comparator.esrd_events - cea.intervention.esrd_events],
    ]

    for i, row in enumerate(avoided_data, start=15):
        for j, val in enumerate(row, start=1):
            cell = ws2.cell(row=i, column=j, value=val)
            if i == 15:
                cell.font = header_font
                cell.fill = subheader_fill
            elif j == 2 and isinstance(val, (int, float)) and val > 0:
                cell.fill = highlight_fill

    ws2.column_dimensions['A'].width = 20
    ws2.column_dimensions['B'].width = 15
    ws2.column_dimensions['C'].width = 15

    # ========== Sheet 3: Cost Analysis with Chart ==========
    ws3 = wb.create_sheet("Cost Analysis")

    ws3['A1'] = "Cost Breakdown Analysis"
    ws3['A1'].font = title_font

    # Cost data for chart
    direct_ixa = cea.intervention.mean_costs - (cea.intervention.total_indirect_costs / cea.intervention.n_patients)
    indirect_ixa = cea.intervention.total_indirect_costs / cea.intervention.n_patients
    direct_spi = cea.comparator.mean_costs - (cea.comparator.total_indirect_costs / cea.comparator.n_patients)
    indirect_spi = cea.comparator.total_indirect_costs / cea.comparator.n_patients

    cost_header = ["Cost Category", "IXA-001", "Spironolactone"]
    cost_data = [
        ["Direct Costs", direct_ixa, direct_spi],
        ["Indirect Costs", indirect_ixa, indirect_spi],
        ["Total Costs", cea.intervention.mean_costs, cea.comparator.mean_costs],
    ]

    ws3.append([])
    ws3.append(cost_header)
    for row in cost_data:
        ws3.append([row[0], row[1], row[2]])

    apply_table_style(ws3, 3, 3 + len(cost_data), 3)

    # Format as currency
    for row in range(4, 4 + len(cost_data)):
        for col in [2, 3]:
            cell = ws3.cell(row=row, column=col)
            if isinstance(cell.value, (int, float)):
                cell.value = f"{currency_sym}{cell.value:,.0f}"

    # Create cost comparison bar chart
    chart2 = BarChart()
    chart2.type = "col"
    chart2.grouping = "clustered"
    chart2.title = "Mean Costs per Patient"
    chart2.y_axis.title = f"Cost ({currency_sym})"
    chart2.style = 12

    # Need numeric data for chart - create separate data area
    ws3['E3'] = "Chart Data"
    ws3['E4'] = "Direct"
    ws3['E5'] = "Indirect"
    ws3['F3'] = "IXA-001"
    ws3['F4'] = direct_ixa
    ws3['F5'] = indirect_ixa
    ws3['G3'] = "Spironolactone"
    ws3['G4'] = direct_spi
    ws3['G5'] = indirect_spi

    data2 = Reference(ws3, min_col=6, min_row=3, max_col=7, max_row=5)
    cats2 = Reference(ws3, min_col=5, min_row=4, max_row=5)
    chart2.add_data(data2, titles_from_data=True)
    chart2.set_categories(cats2)
    chart2.width = 12
    chart2.height = 8

    ws3.add_chart(chart2, "A9")

    # Incremental cost summary
    ws3['A20'] = "INCREMENTAL ANALYSIS"
    ws3['A20'].font = subtitle_font

    inc_data = [
        ["Metric", "Value"],
        ["Incremental Direct Costs", f"{currency_sym}{direct_ixa - direct_spi:,.0f}"],
        ["Incremental Indirect Costs", f"{currency_sym}{indirect_ixa - indirect_spi:,.0f}"],
        ["Total Incremental Costs", f"{currency_sym}{cea.incremental_costs:,.0f}"],
        ["Incremental QALYs", f"{cea.incremental_qalys:.3f}"],
        ["ICER", f"{currency_sym}{cea.icer:,.0f}/QALY" if cea.icer else "Dominant"],
    ]

    for i, row in enumerate(inc_data, start=21):
        for j, val in enumerate(row, start=1):
            cell = ws3.cell(row=i, column=j, value=val)
            if i == 21:
                cell.font = header_font
                cell.fill = header_fill

    ws3.column_dimensions['A'].width = 25
    ws3.column_dimensions['B'].width = 20
    ws3.column_dimensions['C'].width = 20

    # ========== Sheet 4: Subgroup Analysis with Chart ==========
    ws4 = wb.create_sheet("Subgroup Analysis")

    ws4['A1'] = "Subgroup Analysis"
    ws4['A1'].font = title_font

    # Age group data for chart
    ws4['A3'] = "By Age Group"
    ws4['A3'].font = subtitle_font

    ws4.append(["Age Group", "N Patients", "Mean Costs", "Mean QALYs"])
    age_start_row = 5
    age_row = age_start_row

    for cat in ['<60', '60-70', '70-80', '80+']:
        patients = subgroup_data['age'].get(cat, [])
        n = len(patients)
        if n > 0:
            mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients])
            mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients])
            ws4.append([cat, n, mean_costs, mean_qalys])
            age_row += 1

    apply_table_style(ws4, age_start_row - 1, age_row - 1, 4)

    # Create age group chart
    if age_row > age_start_row:
        chart3 = BarChart()
        chart3.type = "col"
        chart3.title = "Outcomes by Age Group"
        chart3.y_axis.title = "Mean QALYs"
        chart3.style = 11

        data3 = Reference(ws4, min_col=4, min_row=age_start_row - 1, max_row=age_row - 1)
        cats3 = Reference(ws4, min_col=1, min_row=age_start_row, max_row=age_row - 1)
        chart3.add_data(data3, titles_from_data=True)
        chart3.set_categories(cats3)
        chart3.width = 10
        chart3.height = 7

        ws4.add_chart(chart3, "F3")

    # Framingham Risk
    current_row = age_row + 2
    ws4.cell(row=current_row, column=1, value="By Framingham CVD Risk").font = subtitle_font
    current_row += 1
    ws4.cell(row=current_row, column=1, value="Category")
    ws4.cell(row=current_row, column=2, value="N Patients")
    ws4.cell(row=current_row, column=3, value="Mean Costs")
    ws4.cell(row=current_row, column=4, value="Mean QALYs")
    fram_header_row = current_row

    for cat in ['Low', 'Borderline', 'Intermediate', 'High']:
        patients = subgroup_data['framingham'].get(cat, [])
        n = len(patients)
        if n > 0:
            current_row += 1
            mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients])
            mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients])
            ws4.cell(row=current_row, column=1, value=cat)
            ws4.cell(row=current_row, column=2, value=n)
            ws4.cell(row=current_row, column=3, value=f"{currency_sym}{mean_costs:,.0f}")
            ws4.cell(row=current_row, column=4, value=f"{mean_qalys:.3f}")

    apply_table_style(ws4, fram_header_row, current_row, 4)

    # KDIGO Risk
    current_row += 2
    ws4.cell(row=current_row, column=1, value="By KDIGO Risk Level").font = subtitle_font
    current_row += 1
    kdigo_header_row = current_row
    ws4.cell(row=current_row, column=1, value="Risk Level")
    ws4.cell(row=current_row, column=2, value="N Patients")
    ws4.cell(row=current_row, column=3, value="Mean Costs")
    ws4.cell(row=current_row, column=4, value="Mean QALYs")

    for cat in ['Low', 'Moderate', 'High', 'Very High']:
        patients = subgroup_data['kdigo'].get(cat, [])
        n = len(patients)
        if n > 0:
            current_row += 1
            mean_costs = np.mean([p.get('cumulative_costs', 0) for p in patients])
            mean_qalys = np.mean([p.get('cumulative_qalys', 0) for p in patients])
            ws4.cell(row=current_row, column=1, value=cat)
            ws4.cell(row=current_row, column=2, value=n)
            ws4.cell(row=current_row, column=3, value=f"{currency_sym}{mean_costs:,.0f}")
            ws4.cell(row=current_row, column=4, value=f"{mean_qalys:.3f}")

    apply_table_style(ws4, kdigo_header_row, current_row, 4)

    ws4.column_dimensions['A'].width = 20
    ws4.column_dimensions['B'].width = 15
    ws4.column_dimensions['C'].width = 15
    ws4.column_dimensions['D'].width = 15

    # ========== Sheet 5: WTP Analysis with Chart ==========
    ws5 = wb.create_sheet("WTP Analysis")

    ws5['A1'] = "Willingness-to-Pay Analysis"
    ws5['A1'].font = title_font

    ws5.append([])
    wtp_header = ["WTP Threshold", "NMB IXA-001", "NMB Spironolactone", "Incremental NMB", "Cost-Effective?"]
    ws5.append(wtp_header)

    wtp_values = [0, 25000, 50000, 75000, 100000, 150000, 200000]
    wtp_start_row = 4

    for wtp in wtp_values:
        nmb_ixa = cea.intervention.mean_qalys * wtp - cea.intervention.mean_costs
        nmb_spi = cea.comparator.mean_qalys * wtp - cea.comparator.mean_costs
        inc_nmb = nmb_ixa - nmb_spi
        ce = "Yes" if inc_nmb > 0 else "No"
        ws5.append([wtp, nmb_ixa, nmb_spi, inc_nmb, ce])

    apply_table_style(ws5, 3, 3 + len(wtp_values), 5)

    # Format currency columns
    for row in range(4, 4 + len(wtp_values)):
        ws5.cell(row=row, column=1).value = f"{currency_sym}{ws5.cell(row=row, column=1).value:,}/QALY"
        for col in [2, 3, 4]:
            val = ws5.cell(row=row, column=col).value
            if isinstance(val, (int, float)):
                ws5.cell(row=row, column=col).value = f"{currency_sym}{val:,.0f}"
        # Highlight cost-effective rows
        if ws5.cell(row=row, column=5).value == "Yes":
            for col in range(1, 6):
                ws5.cell(row=row, column=col).fill = highlight_fill

    # Create WTP line chart
    # Need numeric data for chart
    ws5['G3'] = "WTP"
    ws5['H3'] = "Inc NMB"
    for i, wtp in enumerate(wtp_values, start=4):
        ws5.cell(row=i, column=7, value=wtp)
        nmb_ixa = cea.intervention.mean_qalys * wtp - cea.intervention.mean_costs
        nmb_spi = cea.comparator.mean_qalys * wtp - cea.comparator.mean_costs
        ws5.cell(row=i, column=8, value=nmb_ixa - nmb_spi)

    chart4 = LineChart()
    chart4.title = "Incremental NMB vs WTP Threshold"
    chart4.y_axis.title = f"Incremental NMB ({currency_sym})"
    chart4.x_axis.title = f"WTP ({currency_sym}/QALY)"
    chart4.style = 10

    data4 = Reference(ws5, min_col=8, min_row=3, max_row=3 + len(wtp_values))
    cats4 = Reference(ws5, min_col=7, min_row=4, max_row=3 + len(wtp_values))
    chart4.add_data(data4, titles_from_data=True)
    chart4.set_categories(cats4)
    chart4.width = 12
    chart4.height = 8

    ws5.add_chart(chart4, "A14")

    for col in ['A', 'B', 'C', 'D', 'E']:
        ws5.column_dimensions[col].width = 18

    # ========== Sheet 6: Population Parameters ==========
    ws6 = wb.create_sheet("Parameters")

    ws6['A1'] = "Simulation Parameters"
    ws6['A1'].font = title_font

    ws6['A3'] = "DEMOGRAPHICS"
    ws6['A3'].font = Font(bold=True, color="FFFFFF")
    ws6['A3'].fill = header_fill
    ws6.merge_cells('A3:B3')

    demo_data = [
        ["Mean Age (years)", f"{pop_params.age_mean:.0f} (SD {pop_params.age_sd:.0f})"],
        ["% Male", f"{pop_params.prop_male*100:.0f}%"],
        ["Mean BMI", f"{pop_params.bmi_mean:.1f}"],
    ]

    for i, (label, value) in enumerate(demo_data, start=4):
        ws6.cell(row=i, column=1, value=label)
        ws6.cell(row=i, column=2, value=value)

    ws6['A8'] = "CLINICAL PARAMETERS"
    ws6['A8'].font = Font(bold=True, color="FFFFFF")
    ws6['A8'].fill = header_fill
    ws6.merge_cells('A8:B8')

    clinical_data = [
        ["Mean SBP (mmHg)", f"{pop_params.sbp_mean:.0f} (SD {pop_params.sbp_sd:.0f})"],
        ["Mean eGFR (mL/min/1.73m²)", f"{pop_params.egfr_mean:.0f} (SD {pop_params.egfr_sd:.0f})"],
        ["Mean UACR (mg/g)", f"{pop_params.uacr_mean:.0f}"],
        ["Mean Total Cholesterol", f"{pop_params.total_chol_mean:.0f}"],
        ["Mean HDL Cholesterol", f"{pop_params.hdl_chol_mean:.0f}"],
    ]

    for i, (label, value) in enumerate(clinical_data, start=9):
        ws6.cell(row=i, column=1, value=label)
        ws6.cell(row=i, column=2, value=value)

    ws6['A15'] = "COMORBIDITIES"
    ws6['A15'].font = Font(bold=True, color="FFFFFF")
    ws6['A15'].fill = header_fill
    ws6.merge_cells('A15:B15')

    comorbid_data = [
        ["Diabetes", f"{pop_params.diabetes_prev*100:.0f}%"],
        ["Current Smoker", f"{pop_params.smoker_prev*100:.0f}%"],
        ["Dyslipidemia", f"{pop_params.dyslipidemia_prev*100:.0f}%"],
        ["Prior MI", f"{pop_params.prior_mi_prev*100:.0f}%"],
        ["Prior Stroke", f"{pop_params.prior_stroke_prev*100:.0f}%"],
        ["Heart Failure", f"{pop_params.heart_failure_prev*100:.0f}%"],
    ]

    for i, (label, value) in enumerate(comorbid_data, start=16):
        ws6.cell(row=i, column=1, value=label)
        ws6.cell(row=i, column=2, value=value)

    ws6['A23'] = "TREATMENT"
    ws6['A23'].font = Font(bold=True, color="FFFFFF")
    ws6['A23'].fill = header_fill
    ws6.merge_cells('A23:B23')

    treatment_data = [
        ["Mean Antihypertensives", f"{pop_params.mean_antihypertensives}"],
        ["Adherence Probability", f"{pop_params.adherence_prob*100:.0f}%"],
    ]

    for i, (label, value) in enumerate(treatment_data, start=24):
        ws6.cell(row=i, column=1, value=label)
        ws6.cell(row=i, column=2, value=value)

    ws6.column_dimensions['A'].width = 30
    ws6.column_dimensions['B'].width = 25

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
        with st.status(f"Running microsimulation ({n_patients:,} patients per arm, {time_horizon} years)...", expanded=True) as status:
            cea_results, patients_ixa, patients_spi, profiles = run_simulation_with_progress(
                n_patients, time_horizon, perspective, seed, discount_rate, pop_params, status
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
