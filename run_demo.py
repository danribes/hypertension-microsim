#!/usr/bin/env python3
"""
Demo script to run the hypertension microsimulation.

This demonstrates a basic cost-effectiveness analysis comparing
IXA-001 to spironolactone in resistant hypertension.
"""

import sys
sys.path.insert(0, '.')

from src import run_cea, print_cea_results


def main():
    print("Hypertension Microsimulation Model v0.1.0")
    print("=========================================\n")
    
    print("Running cost-effectiveness analysis...")
    print("  - Intervention: IXA-001 (Aldosterone Synthase Inhibitor)")
    print("  - Comparator: Spironolactone")
    print("  - Population: Adults with resistant hypertension")
    print("  - Time horizon: 40 years")
    print("  - Perspective: US payer")
    print()
    
    # Run analysis with 1000 patients per arm
    cea_results = run_cea(
        n_patients=1000,
        time_horizon_years=40,
        seed=42,
        perspective="US"
    )
    
    # Print results
    print_cea_results(cea_results)
    
    # Summary interpretation
    if cea_results.icer is not None:
        if cea_results.icer < 50000:
            print("Interpretation: IXA-001 is highly cost-effective (ICER < $50,000/QALY)")
        elif cea_results.icer < 100000:
            print("Interpretation: IXA-001 is cost-effective (ICER < $100,000/QALY)")
        elif cea_results.icer < 150000:
            print("Interpretation: IXA-001 may be cost-effective (ICER < $150,000/QALY)")
        else:
            print("Interpretation: IXA-001 exceeds typical willingness-to-pay thresholds")
    else:
        if cea_results.incremental_qalys > 0:
            print("Interpretation: IXA-001 is dominant (more effective, lower cost)")
        else:
            print("Interpretation: IXA-001 is dominated (less effective)")


if __name__ == "__main__":
    main()
