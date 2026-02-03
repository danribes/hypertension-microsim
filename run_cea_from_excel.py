#!/usr/bin/env python3
"""
Run CEA Microsimulation from Excel Interface.

This script:
1. Reads inputs from an Excel file
2. Runs the microsimulation
3. Writes results back to the Excel file

Usage:
    python run_cea_from_excel.py --input CEA_Model_Interface.xlsx
    python run_cea_from_excel.py --generate-template
    python run_cea_from_excel.py --precompute-scenarios
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cea_interface.excel_template import CEAExcelTemplate
from cea_interface.bridge import CEABridge, print_results
from cea_interface.scenarios import ScenarioManager, compute_all_scenarios


def generate_template(output_path: str, with_precomputed: bool = True):
    """Generate Excel template, optionally with pre-computed results."""
    print("\n" + "=" * 60)
    print("GENERATING CEA EXCEL TEMPLATE")
    print("=" * 60)

    precomputed = None

    if with_precomputed:
        # Try to load existing scenarios
        manager = ScenarioManager()
        cache_file = Path(__file__).parent / "cea_interface" / "cache" / "precomputed_scenarios.json"

        if cache_file.exists():
            print(f"\nLoading pre-computed scenarios from cache...")
            manager.load_scenarios()
            precomputed = manager.get_excel_data()
            print(f"Loaded {len(precomputed)} scenarios")
        else:
            print("\nNo pre-computed scenarios found.")
            print("Run with --precompute-scenarios first for instant results.")

    template = CEAExcelTemplate()
    result_path = template.generate(output_path, precomputed)

    print(f"\nTemplate generated: {result_path}")
    print("\nNext steps:")
    print("1. Open the Excel file")
    print("2. Go to 'Inputs' sheet to modify parameters")
    print("3. Save the file")
    print("4. Run: python run_cea_from_excel.py --input " + output_path)

    return result_path


def run_from_excel(excel_path: str):
    """Run simulation using inputs from Excel file."""
    print("\n" + "=" * 60)
    print("RUNNING CEA FROM EXCEL")
    print("=" * 60)

    if not Path(excel_path).exists():
        print(f"Error: File not found: {excel_path}")
        print("Generate a template first with: python run_cea_from_excel.py --generate-template")
        return None

    bridge = CEABridge(excel_path)
    results = bridge.run_and_update()

    print_results(results)

    return results


def precompute_scenarios(n_patients: int = 1000):
    """Pre-compute all scenarios for instant results."""
    print("\n" + "=" * 60)
    print("PRE-COMPUTING SCENARIOS")
    print("=" * 60)
    print(f"\nPatients per arm: {n_patients}")
    print("This will take approximately 30-60 minutes...")
    print("Results will be cached for instant access.\n")

    manager = compute_all_scenarios(n_patients=n_patients, seed=42)

    print("\nPre-computation complete!")
    print(f"Scenarios available: {manager.scenarios.list_scenarios()}")

    # Regenerate template with pre-computed results
    output_path = str(Path(__file__).parent / "CEA_Model_Interface.xlsx")
    generate_template(output_path, with_precomputed=True)

    return manager


def main():
    parser = argparse.ArgumentParser(
        description="CEA Microsimulation Excel Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate Excel template (first time setup)
  python run_cea_from_excel.py --generate-template

  # Pre-compute scenarios for instant results (takes 30-60 min)
  python run_cea_from_excel.py --precompute-scenarios

  # Run simulation with custom inputs from Excel
  python run_cea_from_excel.py --input CEA_Model_Interface.xlsx

  # Quick demo with fewer patients (faster, less accurate)
  python run_cea_from_excel.py --precompute-scenarios --patients 100
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Path to Excel file with inputs"
    )

    parser.add_argument(
        "--generate-template", "-g",
        action="store_true",
        help="Generate Excel template file"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="CEA_Model_Interface.xlsx",
        help="Output path for generated template"
    )

    parser.add_argument(
        "--precompute-scenarios", "-p",
        action="store_true",
        help="Pre-compute all scenarios (takes 30-60 minutes)"
    )

    parser.add_argument(
        "--patients", "-n",
        type=int,
        default=1000,
        help="Number of patients per arm (default: 1000)"
    )

    args = parser.parse_args()

    if args.precompute_scenarios:
        precompute_scenarios(n_patients=args.patients)

    elif args.generate_template:
        output_path = str(Path(__file__).parent / args.output)
        generate_template(output_path, with_precomputed=True)

    elif args.input:
        run_from_excel(args.input)

    else:
        # Default: generate template
        print("No arguments provided. Generating template...")
        output_path = str(Path(__file__).parent / args.output)
        generate_template(output_path, with_precomputed=False)

        print("\n" + "-" * 60)
        print("TIP: Run with --precompute-scenarios for instant results")
        print("-" * 60)


if __name__ == "__main__":
    main()
