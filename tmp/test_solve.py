import pandas as pd
from pathlib import Path
from src.optimization_model import HenkelEnergySystem, FacilityProjectConfig, FixedSizingConfig, VariableSizingConfig

root = Path.cwd()
df_m = pd.read_csv(root / "data" / "market_data_2025.csv", index_col=0, parse_dates=True)
df_s = pd.read_csv(root / "data" / "solar_data_duesseldorf_2025.csv", index_col=0, parse_dates=True)

# Test Operation Mode
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

print("--- Testing Operation Mode ---")
hes_op = HenkelEnergySystem(config=op_config, df_market=df_m, df_solar=df_s)
meta_op = hes_op.solve(timesteps=168)
df_op_flows = hes_op.get_dispatch_dataframe()
print("OP Total Cost (168h):", meta_op["total_cost_eur"])
print("OP Cost per Ton:", meta_op["cost_per_ton_eur"])
print("OP Flow Dataframe Shape:", df_op_flows.shape)

# Test Investment Mode
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

print("\n--- Testing Investment Mode ---")
hes_inv = HenkelEnergySystem(config=inv_config, df_market=df_m, df_solar=df_s)
meta_inv = hes_inv.solve(timesteps=168)
inv_caps = hes_inv.get_investment_capacities()
print("INV Total Cost (168h):", meta_inv["total_cost_eur"])
print("INV Cost per Ton:", meta_inv["cost_per_ton_eur"])
print("Optimal Investment Capacities:", inv_caps)
print("\nALL SOLVE TESTS PASSED SUCCESSFULLY!")
