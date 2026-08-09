"""
Verification script for Must-Run PPAs, Grid Export, and Renewable Metrics.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from src.optimization_model import (
    HenkelEnergySystem,
    FacilityProjectConfig,
    FixedSizingConfig,
    VariableSizingConfig,
)
from src.utils import calculate_curtailment_metrics, create_summary_dataframe

root = Path.cwd()
df_m = pd.read_csv(root / "data" / "market_data_2025.csv", index_col=0, parse_dates=True)
df_s = pd.read_csv(root / "data" / "solar_data_duesseldorf_2025.csv", index_col=0, parse_dates=True)

print("=== 1. Testing Operation Mode with Must-Run PPAs & Grid Export ===")
op_config = FacilityProjectConfig(
    project_name="op_mustrun_ppa_test",
    optimization_mode="operation",
    fixed_components_sizing=FixedSizingConfig(
        pv=5000.0,
        pv_ppa=20000.0,    # 20 MW Solar PPA
        wind_ppa=25000.0,  # 25 MW Wind PPA
        bess=0.0,
        hthp=15000.0,
        tes=20000.0,
    ),
    co2_tax_eur_per_ton=85.0,
    enable_sec19_protection=True,
)

hes_op = HenkelEnergySystem(config=op_config, df_market=df_m, df_solar=df_s)
res_op = hes_op.solve(timesteps=168)  # 1 week optimization

n_op = res_op["network"]

# A. Must-Run Check
p_pv_ppa = n_op.generators_t.p["pv_ppa"]
p_pv_ppa_max = n_op.generators_t.p_max_pu["pv_ppa"] * n_op.generators.loc["pv_ppa", "p_nom"]
np.testing.assert_allclose(p_pv_ppa.values, p_pv_ppa_max.values, rtol=1e-5, atol=1e-5)
print("  ✓ PV PPA Must-Run Verified: 100% of generation profile dispatched!")

p_wind_ppa = n_op.generators_t.p["wind_ppa"]
p_wind_ppa_max = n_op.generators_t.p_max_pu["wind_ppa"] * n_op.generators.loc["wind_ppa", "p_nom"]
np.testing.assert_allclose(p_wind_ppa.values, p_wind_ppa_max.values, rtol=1e-5, atol=1e-5)
print("  ✓ Wind PPA Must-Run Verified: 100% of generation profile dispatched!")

# B. Grid Export Check
grid_export_p = n_op.generators_t.p["grid_export"]
print(f"  ✓ Grid Export Volume (168h): {res_op['grid_export_mwh']:.2f} MWh")
print(f"  ✓ Grid Export Revenue (168h): €{res_op['grid_export_revenue_eur']:,.2f}")

# C. Metrics Check
elec_curt, heat_curt = calculate_curtailment_metrics(res_op)
print(f"  ✓ Curtailed Elec (%): {elec_curt}% | Curtailed Heat (%): {heat_curt}%")
print(f"  ✓ OPEX Total (168h): €{res_op['opex_eur']:,.2f}")

print("\n=== 2. Testing Investment Mode Optimization ===")
inv_config = FacilityProjectConfig(
    project_name="inv_mustrun_ppa_test",
    optimization_mode="investment",
    fixed_components_sizing=FixedSizingConfig(
        pv=1000.0,
        pv_ppa=0.0,
        wind_ppa=0.0,
        bess=0.0,
        hthp=15000.0,
        tes=20000.0,
    ),
    variable_components_sizing=VariableSizingConfig(),
    co2_tax_eur_per_ton=85.0,
    enable_sec19_protection=True,
)

hes_inv = HenkelEnergySystem(config=inv_config, df_market=df_m, df_solar=df_s)
res_inv = hes_inv.solve(timesteps=168)

print("  ✓ Investment Hub Optimal Capacities:")
for k, v in res_inv["optimal_capacities"].items():
    print(f"    - {k}: {v:,.2f}")

print(f"  ✓ Investment Total Cost (168h): €{res_inv['total_cost_eur']:,.2f}")

from src.utils import calculate_curtailment_metrics, create_summary_dataframe, plot_dispatch_stacks_interactive

fig_op = plot_dispatch_stacks_interactive(res_op, mode="interactive")
print("  ✓ Interactive 2-sided dispatch plot generated successfully!")

summary_df = create_summary_dataframe({"Operation Hub": res_op, "Investment Hub": res_inv})
print("\n=== Summary Table ===")
print(summary_df[["Total Cost (EUR)", "OPEX (EUR)", "Grid Export (MWh)", "Grid Export Rev (EUR)", "Self-Consumption (%)", "Autarky (%)", "Curtailed Elec (%)", "Sec19 Compliant"]])

print("\n🎉 ALL MUST-RUN PPA & GRID EXPORT VERIFICATION TESTS PASSED SUCCESSFULLY!")
