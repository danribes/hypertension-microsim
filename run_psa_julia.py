#!/usr/bin/env python3
"""Run a PSA using the Julia backend with parallel execution."""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.simulation import SimulationConfig
from src.psa import PSARunner

def main():
    print("=" * 60)
    print("Hypertension Microsim — Julia Parallel PSA")
    print("=" * 60)

    config = SimulationConfig(
        n_patients=500,
        time_horizon_months=480,  # 40 years
        cycle_length_months=1.0,
        discount_rate=0.03,
        cost_perspective="US",
        show_progress=False,
        use_half_cycle_correction=True,
        use_competing_risks_framework=True,
        use_dynamic_stroke_subtypes=True,
        use_kfre_model=True,
        life_table_country="US",
        economic_perspective="societal",
    )

    n_iterations = 100

    print(f"\nConfig: {config.n_patients} patients × {config.time_horizon_months} months")
    print(f"PSA iterations: {n_iterations}")
    print(f"Total patient-months: {n_iterations * 2 * config.n_patients * config.time_horizon_months:,}")

    # Julia parallel PSA
    print("\n--- Julia Backend (parallel) ---")
    runner = PSARunner(config, seed=42, use_julia_backend=True)

    t0 = time.time()
    results = runner.run(
        n_iterations=n_iterations,
        use_common_random_numbers=True,
        show_progress=False,
        parallel=True,
    )
    elapsed = time.time() - t0

    print(f"Time: {elapsed:.1f}s ({elapsed/n_iterations*1000:.0f}ms per iteration)")
    print(f"Iterations: {results.n_iterations}")

    # Summary statistics
    stats = results.get_summary_statistics()
    import numpy as np

    ixa_costs = np.mean([it.ixa_costs for it in results.iterations])
    ixa_qalys = np.mean([it.ixa_qalys for it in results.iterations])
    comp_costs = np.mean([it.comparator_costs for it in results.iterations])
    comp_qalys = np.mean([it.comparator_qalys for it in results.iterations])

    print(f"\n--- Results ---")
    print(f"IXA-001 mean costs:  ${ixa_costs:,.0f}")
    print(f"IXA-001 mean QALYs:  {ixa_qalys:.3f}")
    print(f"Spiro mean costs:    ${comp_costs:,.0f}")
    print(f"Spiro mean QALYs:    {comp_qalys:.3f}")
    print(f"Delta costs:         ${stats['delta_costs_mean']:,.0f}")
    print(f"Delta QALYs:         {stats['delta_qalys_mean']:.4f}")

    if stats['icer_mean'] is not None:
        print(f"ICER:                ${stats['icer_mean']:,.0f}/QALY")

    # CEAC at common WTP thresholds
    print(f"\n--- CEAC ---")
    for wtp in [50_000, 100_000, 150_000]:
        prob = results.probability_cost_effective(wtp)
        print(f"  WTP ${wtp:>7,}: P(CE) = {prob:.1%}")

    print(f"\nDone.")

if __name__ == "__main__":
    main()
