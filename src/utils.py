"""
Utility module for PyPSA Energy System Visual Reporting and Financial Economics Analysis.

Provides interactive Plotly dashboards (for Jupyter Notebooks) alongside matplotlib figure exports based on:
- .agent/skills/pypsa-reporting (diagnostic panels, multi-carrier dispatch stacks, price duration curves)
- .agent/skills/pypsa-asset-economics (diverging net margins, LCOE/LCOH calculation, Sec19 grid fee protection)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, Optional

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


# Carrier Color Palette conforming to pypsa-reporting design system
CARRIER_COLORS = {
    "grid_electricity": "#3182bd",
    "solar_pv": "#fec44f",
    "gas_chp": "#e6550d",
    "grid_gas": "#6baed6",
    "gas_boiler": "#fd8d3c",
    "electric_boiler": "#74c476",
    "heat_pump": "#2ca02c",
    "bess_discharger": "#9ecae1",
    "tes_discharger": "#a1d99b",
    "demand_elec": "#1f77b4",
    "demand_steam": "#d62728",
    "demand_heat": "#2ca02c",
}


def plot_dispatch_stacks(results: Dict[str, Any], title: str = "PyPSA Multi-Carrier Dispatch Stack") -> plt.Figure:
    """Generates a 3-panel matplotlib figure showing dispatch for electricity, HT steam, and LT heat."""
    n = results["network"]
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # 1. Electricity Bus (b_elec)
    ax0 = axes[0]
    elec_gen = n.generators_t.p[["grid_electricity", "solar_pv"]] if "solar_pv" in n.generators_t.p.columns else n.generators_t.p[["grid_electricity"]]
    elec_gen.plot(kind="area", stacked=True, ax=ax0, alpha=0.8, color=[CARRIER_COLORS.get(c, "#333333") for c in elec_gen.columns])
    ax0.set_title("Electricity Supply Stack (b_elec) [kW]")
    ax0.set_ylabel("Power [kW]")
    ax0.grid(True, linestyle="--", alpha=0.5)

    # 2. HT Steam Bus (b_steam_ht)
    ax1 = axes[1]
    steam_cols = []
    if "gas_boiler" in n.links_t.p1.columns:
        steam_cols.append("gas_boiler")
    if "electric_boiler" in n.links_t.p1.columns:
        steam_cols.append("electric_boiler")
    if "gas_chp" in n.links_t.p2.columns:
        steam_df = n.links_t.p2[["gas_chp"]].rename(columns={"gas_chp": "gas_chp_steam"})
        steam_df.plot(kind="area", stacked=True, ax=ax1, alpha=0.8, color="#e6550d")
    ax1.set_title("High-Temperature Steam Supply (b_steam_ht) [kW_th]")
    ax1.set_ylabel("Thermal Power [kW_th]")
    ax1.grid(True, linestyle="--", alpha=0.5)

    # 3. LT Process Heat Bus (b_heat_lt)
    ax2 = axes[2]
    heat_cols = []
    if "heat_pump" in n.links_t.p1.columns:
        heat_cols.append("heat_pump")
    if "steam_to_heat_exchanger" in n.links_t.p1.columns:
        heat_cols.append("steam_to_heat_exchanger")
    if heat_cols:
        n.links_t.p1[heat_cols].plot(kind="area", stacked=True, ax=ax2, alpha=0.8)
    ax2.set_title("Mid-Temperature Process Heat Supply (b_heat_lt) [kW_th]")
    ax2.set_ylabel("Thermal Power [kW_th]")
    ax2.set_xlabel("Timestamp")
    ax2.grid(True, linestyle="--", alpha=0.5)

    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    return fig


def plot_dispatch_stacks_interactive(results: Dict[str, Any], title: str = "Interactive PyPSA Multi-Carrier Dispatch Stack"):
    """Generates an interactive Plotly dashboard for electricity, steam, and heat dispatch."""
    if not HAS_PLOTLY:
        return plot_dispatch_stacks(results, title)

    n = results["network"]
    snapshots = n.snapshots

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Electricity Bus (b_elec) [kW]", "HT Steam Bus (b_steam_ht) [kW_th]", "LT Process Heat Bus (b_heat_lt) [kW_th]"),
        vertical_spacing=0.08,
        shared_xaxes=True,
    )

    # 1. Electricity
    if "grid_electricity" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["grid_electricity"], name="Grid Elec", stackgroup="elec", fillcolor="#3182bd"), row=1, col=1)
    if "solar_pv" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["solar_pv"], name="Solar PV", stackgroup="elec", fillcolor="#fec44f"), row=1, col=1)
    if "gas_chp" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.links_t.p1["gas_chp"], name="CHP Elec", stackgroup="elec", fillcolor="#e6550d"), row=1, col=1)

    # 2. HT Steam
    if "gas_chp" in n.links_t.p2.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.links_t.p2["gas_chp"], name="CHP Steam", stackgroup="steam", fillcolor="#e6550d"), row=2, col=1)
    if "gas_boiler" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.links_t.p1["gas_boiler"], name="Gas Boiler", stackgroup="steam", fillcolor="#fd8d3c"), row=2, col=1)
    if "electric_boiler" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.links_t.p1["electric_boiler"], name="E-Boiler", stackgroup="steam", fillcolor="#74c476"), row=2, col=1)

    # 3. LT Heat
    if "heat_pump" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.links_t.p1["heat_pump"], name="HTHP Heat", stackgroup="heat", fillcolor="#2ca02c"), row=3, col=1)
    if "steam_to_heat_exchanger" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.links_t.p1["steam_to_heat_exchanger"], name="Steam-HX Heat", stackgroup="heat", fillcolor="#bcbd22"), row=3, col=1)

    fig.update_layout(height=800, title_text=title, template="plotly_white", hovermode="x unified")
    return fig


def plot_storage_dynamics_interactive(results: Dict[str, Any], title: str = "BESS & TES State-of-Charge (SOC) Dynamics"):
    """Generates interactive SOC plot for Battery and Thermal Energy Storage."""
    n = results["network"]
    snapshots = n.snapshots

    if not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(12, 5))
        if "bess" in n.stores_t.e.columns:
            ax.plot(snapshots, n.stores_t.e["bess"], label="BESS SOC [kWh]", color="#3182bd", linewidth=2)
        if "tes" in n.stores_t.e.columns:
            ax.plot(snapshots, n.stores_t.e["tes"], label="TES SOC [kWh_th]", color="#2ca02c", linewidth=2)
        ax.set_title(title)
        ax.set_ylabel("Energy Stored [kWh]")
        ax.grid(True, linestyle="--")
        ax.legend()
        return fig

    fig = go.Figure()
    if "bess" in n.stores_t.e.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.stores_t.e["bess"], name="BESS SOC [kWh]", line=dict(color="#3182bd", width=2.5)))
    if "tes" in n.stores_t.e.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.stores_t.e["tes"], name="TES SOC [kWh_th]", line=dict(color="#2ca02c", width=2.5)))

    fig.update_layout(title=title, xaxis_title="Timestamp", yaxis_title="State of Charge [kWh]", template="plotly_white")
    return fig


def plot_price_duration_curves_interactive(results: Dict[str, Any], title: str = "Electricity Spot & Marginal Bus Price Duration Curve"):
    """Plots marginal price duration curve from PyPSA bus shadow prices."""
    n = results["network"]
    snapshots = n.snapshots

    grid_mc = n.generators_t.marginal_cost["grid_electricity"] if "grid_electricity" in n.generators_t.marginal_cost.columns else n.generators.loc["grid_electricity", "marginal_cost"]
    price_series = pd.Series(grid_mc, index=snapshots) * 1000.0  # EUR/MWh
    sorted_prices = price_series.sort_values(ascending=False).values
    hours = np.arange(1, len(sorted_prices) + 1)

    if not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(hours, sorted_prices, color="#d62728", linewidth=2, label="Grid Elec Price [EUR/MWh]")
        ax.set_title(title)
        ax.set_xlabel("Hours")
        ax.set_ylabel("Price [EUR/MWh]")
        ax.grid(True, linestyle="--")
        return fig

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=sorted_prices, name="Grid Electricity Price", line=dict(color="#d62728", width=2.5)))
    fig.update_layout(title=title, xaxis_title="Hours", yaxis_title="Electricity Price [EUR/MWh]", template="plotly_white")
    return fig


def plot_asset_economics_interactive(results: Dict[str, Any], title: str = "PyPSA Asset Financial Economics & Cost Breakdown"):
    """Generates diverging net margin and CAPEX/OPEX cost decomposition bar chart."""
    opex = results["opex_eur"]
    capex = results["capex_annualized_eur"]
    total = results["total_cost_eur"]

    categories = ["OPEX (Energy Imports)", "Annualized CAPEX", "Total Energy Cost"]
    values = [opex, capex, total]

    if not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(categories, values, color=["#3182bd", "#fd8d3c", "#2ca02c"])
        ax.set_ylabel("EUR")
        ax.set_title(title)
        for i, v in enumerate(values):
            ax.text(i, v + 1000, f"€{v:,.0f}", ha="center", fontweight="bold")
        plt.tight_layout()
        return fig

    fig = go.Figure(data=[
        go.Bar(x=categories, y=values, marker_color=["#3182bd", "#fd8d3c", "#2ca02c"], text=[f"€{v:,.0f}" for v in values], textposition="auto")
    ])
    fig.update_layout(title=title, yaxis_title="EUR", template="plotly_white")
    return fig


def plot_sec19_grid_fee_protection_interactive(results: Dict[str, Any], threshold_kw: float = 60000.0, title: str = "Sec19 StromNEV Peak Grid Demand Profile"):
    """Plots hourly grid electricity import profile against 60 MW continuous baseload threshold."""
    n = results["network"]
    snapshots = n.snapshots
    grid_p = n.generators_t.p["grid_electricity"]

    if not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(snapshots, grid_p, label="Grid Elec Import [kW]", color="#3182bd", linewidth=1.5)
        ax.axhline(threshold_kw, color="red", linestyle="--", linewidth=2, label=f"Sec19 Threshold ({threshold_kw/1000:.0f} MW)")
        ax.set_title(title)
        ax.set_ylabel("Grid Power [kW]")
        ax.grid(True, linestyle="--")
        ax.legend()
        return fig

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=snapshots, y=grid_p, name="Grid Import [kW]", line=dict(color="#3182bd", width=2)))
    fig.add_trace(go.Scatter(x=[snapshots[0], snapshots[-1]], y=[threshold_kw, threshold_kw], name="Sec19 Threshold (60 MW)", line=dict(color="red", width=2, dash="dash")))
    fig.update_layout(title=title, xaxis_title="Timestamp", yaxis_title="Grid Import [kW]", template="plotly_white")
    return fig


def create_summary_dataframe(results_dict: Dict[str, Dict[str, Any]], annual_tonnage: float = 450000.0) -> pd.DataFrame:
    """Compiles scenario results into a clean financial comparison table (EUR/ton, OPEX, CAPEX, CO2)."""
    rows = []
    for scenario_name, res in results_dict.items():
        tot_cost = res["total_cost_eur"]
        cost_per_ton = tot_cost / annual_tonnage
        rows.append({
            "Scenario": scenario_name,
            "Total Cost (EUR)": tot_cost,
            "Cost per Ton (EUR/ton)": cost_per_ton,
            "OPEX (EUR)": res["opex_eur"],
            "Annualized CAPEX (EUR)": res["capex_annualized_eur"],
            "Emissions (tCO2)": res["emissions_t_co2"],
            "Peak Grid Demand (MW)": res["peak_grid_demand_kw"] / 1000.0,
            "Sec19 Compliant": not res["sec19_violation"],
        })

    df_summary = pd.DataFrame(rows).set_index("Scenario")
    return df_summary
