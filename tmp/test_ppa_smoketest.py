import sys
from pathlib import Path
import pandas as pd

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.external_api import prepare_data_files
from src.optimization_model import HenkelEnergySystem, FacilityProjectConfig

print("--- 1. Repopulating Data Files with PV & Wind Yield Profiles ---")
m_path, s_path = prepare_data_files(year=2025, force_repopulate=True)

df_solar = pd.read_csv(s_path, index_col=0, parse_dates=True)
print("Solar DF columns:", df_solar.columns.tolist())
assert "pv_normalized_yield" in df_solar.columns
assert "wind_normalized_yield" in df_solar.columns

print("\n--- 2. Testing Operation Hub (Fixed Sizing) 1-Week Smoketest ---")
op_cfg = FacilityProjectConfig(
    optimization_mode="operation",
    start_time="01/01/2025",
    end_time="08/01/2025",
)
op_system = HenkelEnergySystem(config=op_cfg)
op_results = op_system.solve(timesteps=168)
print("Operation Hub Status:", op_results["status"])
print(f"Operation Hub Total Cost (Annualized Eq.): €{op_results['total_cost_eur']:,.2f}")
print(f"  - Elec Spot Cost: €{op_results['elec_cost_eur']:,.2f}")
print(f"  - Gas Cost:       €{op_results['gas_cost_eur']:,.2f}")
print(f"  - PV PPA Cost:    €{op_results['pv_ppa_cost_eur']:,.2f}")
print(f"  - Wind PPA Cost:  €{op_results['wind_ppa_cost_eur']:,.2f}")
print(f"  - CO2 Emissions:  {op_results['emissions_t_co2']:,.2f} tCO2")

print("\n--- 3. Testing Decision Hub (Investment Sizing) 1-Week Smoketest ---")
inv_cfg = FacilityProjectConfig(
    optimization_mode="investment",
    start_time="01/01/2025",
    end_time="08/01/2025",
)
inv_system = HenkelEnergySystem(config=inv_cfg)
inv_results = inv_system.solve(timesteps=168)
print("Decision Hub Status:", inv_results["status"])
print(f"Decision Hub Total Cost (Annualized Eq.): €{inv_results['total_cost_eur']:,.2f}")
print(f"  - OPEX: €{inv_results['opex_eur']:,.2f}")
print(f"  - CAPEX (Annualized): €{inv_results['capex_annualized_eur']:,.2f}")
print(f"  - PV PPA Cost:   €{inv_results['pv_ppa_cost_eur']:,.2f}")
print(f"  - Wind PPA Cost: €{inv_results['wind_ppa_cost_eur']:,.2f}")
print("\nOptimal Sizing Sourced by Solver:")
for k, v in inv_results["optimal_capacities"].items():
    print(f"  - {k}: {v:,.2f} kW/kWh")

print("\nALL SMOKETESTS PASSED SUCCESSFULLY!")
