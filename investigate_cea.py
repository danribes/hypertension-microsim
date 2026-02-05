"""
Investigate CEA discrepancy between diagnostic and full run.
Key question: Why does year-by-year show IXA advantage but full CEA shows IXA dominated?
"""
import sys
sys.path.insert(0, 'src')

import copy
import numpy as np
from population import PopulationGenerator, PopulationParams
from simulation import Simulation, SimulationConfig, SimulationResults
from patient import Treatment

def run_controlled_cea(n_patients=500, horizon_years=20, seed=42):
    """
    Run CEA with strict seed control and population identity verification.
    """
    print(f"\n{'='*70}")
    print(f"CONTROLLED CEA: {horizon_years}-YEAR HORIZON, N={n_patients}, SEED={seed}")
    print('='*70)
    
    # Generate base population ONCE with fixed seed
    pop_params = PopulationParams(n_patients=n_patients, seed=seed)
    generator = PopulationGenerator(pop_params)
    base_patients = generator.generate()
    
    # Filter to PA patients only
    pa_patients = [p for p in base_patients if getattr(p, 'secondary_htn_cause', None) == 'PA']
    print(f"PA patients in population: {len(pa_patients)}")
    
    if len(pa_patients) < 50:
        # Use full population if not enough PA patients
        print("Using full population (not enough PA patients)")
        pa_patients = base_patients[:200]
    
    # Verify patient identity before deep copy
    print(f"\nPatient verification before simulation:")
    print(f"  Patient 0 age: {pa_patients[0].age}")
    print(f"  Patient 0 baseline SBP: {pa_patients[0].baseline_sbp}")
    print(f"  Patient 0 eGFR: {pa_patients[0].egfr}")
    
    # Create simulation with SAME seed for both arms
    config = SimulationConfig(
        n_patients=len(pa_patients),
        time_horizon_months=horizon_years * 12,
        seed=seed,  # Same seed
        show_progress=False
    )
    
    # Run IXA-001 arm first
    print(f"\nRunning IXA-001 arm...")
    sim_ixa = Simulation(config)
    # Note: run() does deep copy internally
    results_ixa = sim_ixa.run(pa_patients, Treatment.IXA_001)
    
    # Run Spironolactone arm 
    # Create new Simulation instance to reset RNG state
    print(f"Running Spironolactone arm...")
    sim_spi = Simulation(config)  # Fresh simulation with same seed
    results_spi = sim_spi.run(pa_patients, Treatment.SPIRONOLACTONE)
    
    # Print detailed results
    print(f"\n{'Metric':<30} {'IXA-001':>15} {'Spironolactone':>15} {'Delta':>15}")
    print("-" * 75)
    
    delta_qalys = results_ixa.mean_qalys - results_spi.mean_qalys
    delta_costs = results_ixa.mean_costs - results_spi.mean_costs
    
    print(f"{'Mean QALYs':<30} {results_ixa.mean_qalys:>15.4f} {results_spi.mean_qalys:>15.4f} {delta_qalys:>+15.4f}")
    print(f"{'Mean Costs ($)':<30} {results_ixa.mean_costs:>15,.0f} {results_spi.mean_costs:>15,.0f} {delta_costs:>+15,.0f}")
    print(f"{'Mean Life Years':<30} {results_ixa.mean_life_years:>15.2f} {results_spi.mean_life_years:>15.2f} {results_ixa.mean_life_years - results_spi.mean_life_years:>+15.2f}")
    
    print(f"\n{'MI Events':<30} {results_ixa.mi_events:>15} {results_spi.mi_events:>15} {results_ixa.mi_events - results_spi.mi_events:>+15}")
    print(f"{'Stroke Events':<30} {results_ixa.stroke_events:>15} {results_spi.stroke_events:>15} {results_ixa.stroke_events - results_spi.stroke_events:>+15}")
    print(f"{'HF Events':<30} {results_ixa.hf_events:>15} {results_spi.hf_events:>15} {results_ixa.hf_events - results_spi.hf_events:>+15}")
    print(f"{'CV Deaths':<30} {results_ixa.cv_deaths:>15} {results_spi.cv_deaths:>15} {results_ixa.cv_deaths - results_spi.cv_deaths:>+15}")
    print(f"{'Non-CV Deaths':<30} {results_ixa.non_cv_deaths:>15} {results_spi.non_cv_deaths:>15} {results_ixa.non_cv_deaths - results_spi.non_cv_deaths:>+15}")
    print(f"{'Total Deaths':<30} {results_ixa.total_deaths:>15} {results_spi.total_deaths:>15} {results_ixa.total_deaths - results_spi.total_deaths:>+15}")
    
    # ICER calculation
    if abs(delta_qalys) > 0.001:
        if delta_qalys > 0 and delta_costs > 0:
            icer = delta_costs / delta_qalys
            print(f"\nICER: ${icer:,.0f}/QALY")
        elif delta_qalys > 0 and delta_costs < 0:
            print(f"\nIXA-001 is DOMINANT (lower cost, higher QALYs)")
        elif delta_qalys < 0 and delta_costs > 0:
            print(f"\nIXA-001 is DOMINATED (higher cost, lower QALYs)")
        else:
            icer = delta_costs / delta_qalys
            print(f"\nCost-saving trade-off: ${abs(icer):,.0f}/QALY lost")
    else:
        print(f"\nQALY difference too small for meaningful ICER")
    
    return {
        'horizon': horizon_years,
        'ixa': results_ixa,
        'spi': results_spi,
        'delta_qalys': delta_qalys,
        'delta_costs': delta_costs
    }

# Run at multiple horizons
print("\n" + "="*80)
print("INVESTIGATING CEA DISCREPANCY: 20-YEAR PA SUBGROUP ANALYSIS")
print("="*80)

horizons = [10, 15, 20]
results_by_horizon = {}

for h in horizons:
    results_by_horizon[h] = run_controlled_cea(n_patients=500, horizon_years=h, seed=42)

print("\n\n" + "="*80)
print("SUMMARY: QALY DIFFERENTIAL BY HORIZON")
print("="*80)
print(f"\n{'Horizon':<15} {'Δ QALYs':>15} {'Δ Costs':>15} {'Status':>20}")
print("-" * 65)
for h in horizons:
    r = results_by_horizon[h]
    if r['delta_qalys'] > 0.001:
        if r['delta_costs'] > 0:
            icer = r['delta_costs'] / r['delta_qalys']
            status = f"ICER ${icer:,.0f}"
        else:
            status = "DOMINANT"
    elif r['delta_qalys'] < -0.001:
        if r['delta_costs'] > 0:
            status = "DOMINATED"
        else:
            status = "COST-SAVING"
    else:
        status = "NO DIFF"
    print(f"{h} years{'':<7} {r['delta_qalys']:>+15.4f} {r['delta_costs']:>+15,.0f} {status:>20}")

