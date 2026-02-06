#!/usr/bin/env python3
"""
Probabilistic Sensitivity Analysis (PSA) Demo

This script demonstrates the complete PSA workflow for the IXA-001 microsimulation,
including:
1. Cholesky decomposition for correlated parameters
2. Nested-loop PSA with Common Random Numbers
3. Output generation (CE plane, CEAC, EVPI)

Usage:
    python run_psa_demo.py [--iterations N] [--patients N] [--seed N]

Example:
    python run_psa_demo.py --iterations 100 --patients 200 --seed 42
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd

from src.psa import (
    run_psa, print_psa_summary, PSARunner,
    get_default_parameter_distributions, get_default_correlation_groups,
    CholeskySampler, ParameterDistribution, CorrelationGroup
)
from src.simulation import SimulationConfig


def demonstrate_cholesky_sampling():
    """Demonstrate Cholesky decomposition for correlated parameters."""
    print("\n" + "="*70)
    print("DEMONSTRATION: CHOLESKY DECOMPOSITION FOR CORRELATED PARAMETERS")
    print("="*70)

    # Get default distributions and correlations
    distributions = get_default_parameter_distributions()
    correlation_groups = get_default_correlation_groups()

    print("\n1. DEFINED CORRELATION GROUPS:")
    print("-" * 50)

    for group_name, group in correlation_groups.items():
        print(f"\n{group_name.upper()}:")
        print(f"  Parameters: {group.parameters}")
        print(f"  Correlation Matrix:")
        for i, row in enumerate(group.correlation_matrix):
            print(f"    {group.parameters[i][:20]:20s}: {row}")

    # Create sampler and demonstrate
    sampler = CholeskySampler(distributions, correlation_groups, seed=42)

    print("\n2. SAMPLING 10,000 CORRELATED PARAMETER SETS:")
    print("-" * 50)

    samples = sampler.sample(n_samples=10000)

    # Verify correlations for acute costs group
    acute_costs_params = correlation_groups['acute_costs'].parameters
    print("\nActual correlations achieved (Acute Costs group):")

    actual_corr = np.corrcoef([samples[p] for p in acute_costs_params])
    target_corr = correlation_groups['acute_costs'].correlation_matrix

    for i in range(len(acute_costs_params)):
        for j in range(i+1, len(acute_costs_params)):
            print(f"  {acute_costs_params[i][:15]:15s} vs {acute_costs_params[j][:15]:15s}: "
                  f"Target={target_corr[i,j]:.2f}, Actual={actual_corr[i,j]:.2f}")

    # Show sample statistics
    print("\n3. SAMPLE STATISTICS:")
    print("-" * 50)

    key_params = ['ixa_sbp_mean', 'cost_mi_acute', 'utility_post_mi', 'rr_stroke_per_10mmhg']
    for param in key_params:
        if param in samples:
            values = samples[param]
            print(f"\n{param}:")
            print(f"  Mean:   {np.mean(values):.3f}")
            print(f"  SD:     {np.std(values):.3f}")
            print(f"  Min:    {np.min(values):.3f}")
            print(f"  Max:    {np.max(values):.3f}")
            print(f"  95% CI: ({np.percentile(values, 2.5):.3f}, {np.percentile(values, 97.5):.3f})")


def run_quick_psa(n_iterations: int = 50, n_patients: int = 100, seed: int = 42):
    """Run a quick PSA for demonstration."""
    print("\n" + "="*70)
    print("RUNNING PROBABILISTIC SENSITIVITY ANALYSIS")
    print("="*70)

    print(f"\nConfiguration:")
    print(f"  Parameter samples (outer loop): {n_iterations}")
    print(f"  Patients per iteration (inner loop): {n_patients}")
    print(f"  Time horizon: 40 years")
    print(f"  Using Common Random Numbers: Yes")
    print(f"  Using Cholesky for correlated parameters: Yes")

    print("\nRunning PSA...")
    results = run_psa(
        n_patients=n_patients,
        n_iterations=n_iterations,
        time_horizon_years=40,
        seed=seed,
        perspective="US",
        show_progress=True
    )

    return results


def analyze_results(results):
    """Analyze and display PSA results."""
    # Print summary
    print_psa_summary(results)

    # Generate CEAC data
    print("\nCOST-EFFECTIVENESS ACCEPTABILITY CURVE DATA:")
    print("-" * 50)
    ceac = results.generate_ceac(wtp_range=np.array([0, 25000, 50000, 75000, 100000, 150000, 200000]))
    print(ceac.to_string(index=False))

    # Calculate EVPI at key thresholds
    print("\n\nEXPECTED VALUE OF PERFECT INFORMATION (EVPI):")
    print("-" * 50)
    print("(Per patient in target population)")

    for wtp in [50000, 100000, 150000]:
        evpi = results.calculate_evpi(wtp)
        print(f"  At ${wtp:,}/QALY: ${evpi:,.2f}")

    # Population-level EVPI (assuming 11,000 eligible patients per 1M plan members)
    print("\nPopulation EVPI (11,000 eligible patients):")
    for wtp in [50000, 100000, 150000]:
        evpi = results.calculate_evpi(wtp, population_size=11000)
        print(f"  At ${wtp:,}/QALY: ${evpi/1e6:,.2f} million")

    # Parameter importance
    print("\n\nPARAMETER IMPORTANCE (Correlation with NMB at $100K/QALY):")
    print("-" * 50)
    importance = results.parameter_importance(wtp_threshold=100000)
    print(importance.head(10).to_string(index=False))

    return results


def export_results(results, output_dir: str = "."):
    """Export results to CSV files."""
    print("\n\nEXPORTING RESULTS:")
    print("-" * 50)

    # Full iteration data
    df = results.to_dataframe()
    df.to_csv(os.path.join(output_dir, "psa_iterations.csv"), index=False)
    print(f"  Saved: psa_iterations.csv ({len(df)} rows)")

    # CEAC data
    ceac = results.generate_ceac()
    ceac.to_csv(os.path.join(output_dir, "psa_ceac.csv"), index=False)
    print(f"  Saved: psa_ceac.csv ({len(ceac)} rows)")

    # EVPI data
    evpi = results.generate_evpi_curve(population_size=11000)
    evpi.to_csv(os.path.join(output_dir, "psa_evpi.csv"), index=False)
    print(f"  Saved: psa_evpi.csv ({len(evpi)} rows)")

    # Summary statistics
    summary = results.get_summary_statistics()
    pd.DataFrame([summary]).to_csv(os.path.join(output_dir, "psa_summary.csv"), index=False)
    print(f"  Saved: psa_summary.csv")


def try_plotting(results):
    """Attempt to generate plots if matplotlib is available."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt

        from src.psa import plot_ce_plane, plot_ceac, plot_evpi

        print("\n\nGENERATING PLOTS:")
        print("-" * 50)

        # CE Plane
        fig1 = plot_ce_plane(results)
        if fig1:
            fig1.savefig("psa_ce_plane.png", dpi=150, bbox_inches='tight')
            print("  Saved: psa_ce_plane.png")
            plt.close(fig1)

        # CEAC
        fig2 = plot_ceac(results)
        if fig2:
            fig2.savefig("psa_ceac.png", dpi=150, bbox_inches='tight')
            print("  Saved: psa_ceac.png")
            plt.close(fig2)

        # EVPI
        fig3 = plot_evpi(results, population_size=11000)
        if fig3:
            fig3.savefig("psa_evpi.png", dpi=150, bbox_inches='tight')
            print("  Saved: psa_evpi.png")
            plt.close(fig3)

    except ImportError:
        print("\nNote: matplotlib not available. Skipping plot generation.")
        print("Install with: pip install matplotlib")


def main():
    parser = argparse.ArgumentParser(
        description="Run Probabilistic Sensitivity Analysis for IXA-001 CEA"
    )
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=100,
        help="Number of PSA iterations (parameter samples). Default: 100"
    )
    parser.add_argument(
        "--patients", "-p",
        type=int,
        default=200,
        help="Patients per iteration. Default: 200"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=42,
        help="Random seed for reproducibility. Default: 42"
    )
    parser.add_argument(
        "--demo-cholesky",
        action="store_true",
        help="Demonstrate Cholesky decomposition only"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export results to CSV files"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("IXA-001 PROBABILISTIC SENSITIVITY ANALYSIS")
    print("Hypertension Microsimulation Model")
    print("="*70)

    # Always demonstrate Cholesky first
    if args.demo_cholesky:
        demonstrate_cholesky_sampling()
        return

    # Show Cholesky demo briefly
    demonstrate_cholesky_sampling()

    # Run PSA
    results = run_quick_psa(
        n_iterations=args.iterations,
        n_patients=args.patients,
        seed=args.seed
    )

    # Analyze results
    analyze_results(results)

    # Export if requested
    if args.export:
        export_results(results)

    # Try plotting
    try_plotting(results)

    print("\n" + "="*70)
    print("PSA COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
