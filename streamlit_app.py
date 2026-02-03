"""
Streamlit Web Interface for Hypertension Microsimulation Model.

Cost-Effectiveness Analysis comparing IXA-001 vs Spironolactone
in adults with resistant hypertension.
"""

import streamlit as st
import numpy as np
import pandas as pd
from typing import Optional
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import run_cea, CEAResults, Treatment

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
    .metric-positive {
        color: #28a745;
    }
    .metric-negative {
        color: #dc3545;
    }
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


def run_simulation(n_patients: int, time_horizon: int, perspective: str, seed: int) -> CEAResults:
    """Run the CEA simulation with progress indication."""
    return run_cea(
        n_patients=n_patients,
        time_horizon_years=time_horizon,
        seed=seed,
        perspective=perspective
    )


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
        # Cost-effectiveness interpretation
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


def display_outcomes_table(cea: CEAResults, currency: str):
    """Display outcomes comparison table."""
    st.markdown("### Outcomes Comparison")

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


def display_event_charts(cea: CEAResults):
    """Display event comparison charts."""
    st.markdown("### Event Comparison")

    col1, col2 = st.columns(2)

    with col1:
        # Cardiac events
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
        cardiac_melted = cardiac_data.melt(id_vars=["Event"], var_name="Treatment", value_name="Events")
        st.bar_chart(cardiac_data.set_index("Event"), use_container_width=True)
        st.caption("Cardiac Events (per 1000 patients)")

    with col2:
        # Renal events
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

    # Create scatter plot data
    chart_data = pd.DataFrame({
        "Incremental QALYs": [cea.incremental_qalys],
        "Incremental Costs": [cea.incremental_costs],
    })

    st.scatter_chart(chart_data, x="Incremental QALYs", y="Incremental Costs", use_container_width=True)

    # Add interpretation
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

    # Sidebar inputs
    st.sidebar.markdown("## Simulation Parameters")

    n_patients = st.sidebar.slider(
        "Cohort Size (per arm)",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100,
        help="Number of patients to simulate in each treatment arm"
    )

    time_horizon = st.sidebar.slider(
        "Time Horizon (years)",
        min_value=5,
        max_value=50,
        value=40,
        step=5,
        help="Duration of the simulation"
    )

    perspective = st.sidebar.selectbox(
        "Cost Perspective",
        options=["US", "UK"],
        index=0,
        help="Healthcare system perspective for costs"
    )

    currency = "$" if perspective == "US" else "£"

    seed = st.sidebar.number_input(
        "Random Seed",
        min_value=1,
        max_value=99999,
        value=42,
        help="Seed for reproducibility"
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
    - Mortality (CV and non-CV)
    - Quality-adjusted life years (QALYs)
    """)

    # Run simulation button
    if st.sidebar.button("Run Simulation", type="primary", use_container_width=True):
        with st.spinner(f"Running microsimulation ({n_patients:,} patients per arm, {time_horizon} years)..."):
            cea_results = run_simulation(n_patients, time_horizon, perspective, seed)
            st.session_state.cea_results = cea_results
            st.session_state.currency = currency

    # Display results if available
    if "cea_results" in st.session_state:
        cea = st.session_state.cea_results
        currency = st.session_state.currency

        # Key metrics
        display_key_metrics(cea, currency)

        st.divider()

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Outcomes Table",
            "📈 Event Charts",
            "💰 CE Plane",
            "🎯 WTP Analysis"
        ])

        with tab1:
            display_outcomes_table(cea, currency)

        with tab2:
            display_event_charts(cea)

        with tab3:
            display_ce_plane(cea, currency)

        with tab4:
            display_wtp_analysis(cea, currency)

        # Summary box
        st.divider()
        st.markdown("### Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            **Simulation Parameters:**
            - Cohort size: {n_patients:,} patients per arm
            - Time horizon: {time_horizon} years
            - Perspective: {perspective}
            - Discount rate: 3% per annum
            """)

        with col2:
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
