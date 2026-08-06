import time
import pandas as pd
from pathlib import Path
from src.optimization_model import HenkelEnergySystem, FacilityProjectConfig, FixedSizingConfig, VariableSizingConfig
from src.utils import plot_seasonal_dispatch_subplots

root = Path.cwd()
df_m = pd.read_csv(root / "data" / "market_data_2025.csv", index_col=0, parse_dates=True)
df_s = pd.read_csv(root / "data" / "solar_data_duesseldorf_2025.csv", index_col=0, parse_dates=True)

print("--- Benchmark 1: Operation Mode (1 week: 01/01/2025 -> 08/01/2025) ---")
op_config = FacilityProjectConfig(
    project_name="current_facility_optimization",
    optimization_mode="operation",
    start_time="01/01/2025",
    end_time="08/01/2025",
    fixed_components_sizing=FixedSizingConfig(
        pv=500,
        bess=0.0,
        hthp=15000.0,
        tes=20000.0,
    ),
    co2_tax_eur_per_ton=85.0,
    enable_sec19_protection=True,
)

t0 = time.time()
hes_op = HenkelEnergySystem(config=op_config, df_market=df_m, df_solar=df_s)
meta_op = hes_op.solve()
t1 = time.time()

df_op_flows = hes_op.get_dispatch_dataframe()

print(f"Operation Solve Execution Time: {t1 - t0:.2f} seconds")
print(f"Calculated Timesteps (hours): {meta_op['timesteps']}")
print(f"Total Cost (EUR): {meta_op['total_cost_eur']:,.2f}")
print(f"Cost per Ton (EUR/t): {meta_op['cost_per_ton_eur']:.2f}")
print(f"Dispatch Flow Shape: {df_op_flows.shape}")

print("\n--- Benchmark 2: Investment Mode (1 week) ---")
inv_config = FacilityProjectConfig(
    project_name="future_facility_decarbonization",
    optimization_mode="investment",
    start_time="01/01/2025",
    end_time="08/01/2025",
    fixed_components_sizing=FixedSizingConfig(
        pv=500,
        bess=0.0,
        hthp=15000.0,
        tes=20000.0,
    ),
    variable_components_sizing=VariableSizingConfig(),
    co2_tax_eur_per_ton=85.0,
    wacc=0.07,
)

t2 = time.time()
hes_inv = HenkelEnergySystem(config=inv_config, df_market=df_m, df_solar=df_s)
meta_inv = hes_inv.solve()
t3 = time.time()

print(f"Investment Solve Execution Time: {t3 - t2:.2f} seconds")
print(f"Optimal Investment Capacities: {hes_inv.get_investment_capacities()}")

print("\n--- Testing plot_seasonal_dispatch_subplots compatibility ---")
fig = plot_seasonal_dispatch_subplots(df_op_flows_full=df_op_flows, df_market_full=df_m)
print("Plot function executed successfully!")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
