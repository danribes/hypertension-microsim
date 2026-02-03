"""
Pre-computed Scenarios Manager.

Stores and retrieves pre-computed scenario results for instant access.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class PrecomputedScenarios:
    """Container for pre-computed scenario results."""

    def __init__(self):
        self.scenarios: Dict[str, Dict[str, Any]] = {}

    def add_scenario(self, name: str, results: Dict[str, Any], params: Optional[Dict] = None):
        """Add a scenario to the collection."""
        self.scenarios[name] = {
            "scenario_name": name,
            "results": results,
            "params": params or {},
            "computed_at": datetime.now().isoformat(),
        }

    def get_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a scenario by name."""
        return self.scenarios.get(name)

    def list_scenarios(self) -> List[str]:
        """List all available scenarios."""
        return list(self.scenarios.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.scenarios

    def save(self, filepath: str):
        """Save scenarios to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.scenarios, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "PrecomputedScenarios":
        """Load scenarios from JSON file."""
        instance = cls()
        with open(filepath, 'r') as f:
            instance.scenarios = json.load(f)
        return instance

    def to_excel_format(self) -> Dict[str, Any]:
        """Convert to format suitable for Excel template."""
        excel_data = {}

        for name, data in self.scenarios.items():
            results = data.get("results", {})
            params = data.get("params", {})

            excel_data[name] = {
                "scenario_name": data.get("scenario_name", name),
                "icer": results.get("icer"),
                "incremental_costs": results.get("incremental_costs"),
                "incremental_qalys": results.get("incremental_qalys"),
                "ixa_mean_costs": results.get("ixa_mean_costs"),
                "ixa_mean_qalys": results.get("ixa_mean_qalys"),
                "spiro_mean_costs": results.get("spiro_mean_costs"),
                "spiro_mean_qalys": results.get("spiro_mean_qalys"),
                "ixa_mi_events": results.get("ixa_mi_events"),
                "ixa_stroke_events": results.get("ixa_stroke_events"),
                "ixa_hf_events": results.get("ixa_hf_events"),
                "ixa_esrd_events": results.get("ixa_esrd_events"),
                "ixa_cv_deaths": results.get("ixa_cv_deaths"),
                "spiro_mi_events": results.get("spiro_mi_events"),
                "spiro_stroke_events": results.get("spiro_stroke_events"),
                "spiro_hf_events": results.get("spiro_hf_events"),
                "spiro_esrd_events": results.get("spiro_esrd_events"),
                "spiro_cv_deaths": results.get("spiro_cv_deaths"),
                "strokes_avoided": results.get("strokes_avoided"),
                "ixa_monthly_cost": params.get("ixa_monthly_cost", 500),
                "timestamp": data.get("computed_at"),
            }

        return excel_data


class ScenarioManager:
    """
    Manages scenario computation and storage.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.scenarios = PrecomputedScenarios()

    def compute_base_case(self, n_patients: int = 1000, seed: int = 42) -> Dict[str, Any]:
        """Compute base case scenario."""
        from src.simulation import run_cea

        print("Computing base case scenario...")
        cea = run_cea(n_patients=n_patients, seed=seed)

        results = {
            "icer": cea.icer,
            "incremental_costs": cea.incremental_costs,
            "incremental_qalys": cea.incremental_qalys,
            "ixa_mean_costs": cea.intervention.mean_costs,
            "ixa_mean_qalys": cea.intervention.mean_qalys,
            "spiro_mean_costs": cea.comparator.mean_costs,
            "spiro_mean_qalys": cea.comparator.mean_qalys,
            "ixa_mi_events": cea.intervention.mi_events,
            "ixa_stroke_events": cea.intervention.stroke_events,
            "ixa_hf_events": cea.intervention.hf_events,
            "ixa_esrd_events": cea.intervention.esrd_events,
            "ixa_cv_deaths": cea.intervention.cv_deaths,
            "spiro_mi_events": cea.comparator.mi_events,
            "spiro_stroke_events": cea.comparator.stroke_events,
            "spiro_hf_events": cea.comparator.hf_events,
            "spiro_esrd_events": cea.comparator.esrd_events,
            "spiro_cv_deaths": cea.comparator.cv_deaths,
            "strokes_avoided": cea.comparator.stroke_events - cea.intervention.stroke_events,
        }

        self.scenarios.add_scenario("base_case", results, {"ixa_monthly_cost": 500})
        return results

    def compute_price_sensitivity(
        self,
        prices: List[float] = None,
        n_patients: int = 1000,
        seed: int = 42
    ) -> List[Dict[str, Any]]:
        """Compute scenarios for different IXA-001 prices."""
        from src.simulation import run_cea
        from src.treatment import TREATMENT_EFFECTS
        from src.patient import Treatment

        if prices is None:
            prices = [300, 400, 500, 600, 700, 800]

        results = []
        original_cost = TREATMENT_EFFECTS[Treatment.IXA_001].monthly_cost

        for price in prices:
            print(f"Computing price scenario: ${price}/month...")

            # Update treatment cost
            TREATMENT_EFFECTS[Treatment.IXA_001].monthly_cost = price

            cea = run_cea(n_patients=n_patients, seed=seed)

            result = {
                "monthly_price": price,
                "annual_cost": price * 12,
                "icer": cea.icer,
                "incremental_costs": cea.incremental_costs,
                "incremental_qalys": cea.incremental_qalys,
            }
            results.append(result)

            # Add to scenarios
            self.scenarios.add_scenario(
                f"price_{price}",
                {
                    "icer": cea.icer,
                    "incremental_costs": cea.incremental_costs,
                    "incremental_qalys": cea.incremental_qalys,
                    "ixa_mean_costs": cea.intervention.mean_costs,
                    "ixa_mean_qalys": cea.intervention.mean_qalys,
                    "spiro_mean_costs": cea.comparator.mean_costs,
                    "spiro_mean_qalys": cea.comparator.mean_qalys,
                    "strokes_avoided": cea.comparator.stroke_events - cea.intervention.stroke_events,
                },
                {"ixa_monthly_cost": price}
            )

        # Restore original cost
        TREATMENT_EFFECTS[Treatment.IXA_001].monthly_cost = original_cost

        return results

    def save_scenarios(self, filename: str = "precomputed_scenarios.json"):
        """Save all scenarios to file."""
        filepath = self.cache_dir / filename
        self.scenarios.save(str(filepath))
        print(f"Scenarios saved to: {filepath}")
        return str(filepath)

    def load_scenarios(self, filename: str = "precomputed_scenarios.json") -> bool:
        """Load scenarios from file."""
        filepath = self.cache_dir / filename
        if filepath.exists():
            self.scenarios = PrecomputedScenarios.load(str(filepath))
            print(f"Loaded {len(self.scenarios.scenarios)} scenarios from: {filepath}")
            return True
        return False

    def get_excel_data(self) -> Dict[str, Any]:
        """Get scenarios in Excel-compatible format."""
        return self.scenarios.to_excel_format()


def compute_all_scenarios(n_patients: int = 1000, seed: int = 42) -> ScenarioManager:
    """
    Compute all standard scenarios.

    This is the main function to pre-compute scenarios for the Excel interface.
    """
    manager = ScenarioManager()

    print("\n" + "=" * 60)
    print("COMPUTING PRE-DEFINED SCENARIOS")
    print("=" * 60)

    # Base case
    print("\n[1/2] Base Case")
    manager.compute_base_case(n_patients=n_patients, seed=seed)

    # Price sensitivity
    print("\n[2/2] Price Sensitivity")
    manager.compute_price_sensitivity(
        prices=[300, 400, 500, 600, 700, 800],
        n_patients=n_patients,
        seed=seed
    )

    # Save results
    manager.save_scenarios()

    print("\n" + "=" * 60)
    print("ALL SCENARIOS COMPUTED AND SAVED")
    print("=" * 60)

    return manager
