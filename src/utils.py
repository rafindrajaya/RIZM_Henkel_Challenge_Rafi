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
from typing import Dict, Any, Optional, Tuple

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
    elec_cols = [c for c in ["grid_electricity", "solar_pv", "pv_ppa", "wind_ppa"] if c in n.generators_t.p.columns]
    elec_gen = n.generators_t.p[elec_cols] if elec_cols else pd.DataFrame(index=n.snapshots)
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
    if "pv_ppa" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["pv_ppa"], name="PV PPA", stackgroup="elec", fillcolor="#ffbb78"), row=1, col=1)
    if "wind_ppa" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["wind_ppa"], name="Wind PPA", stackgroup="elec", fillcolor="#98df8a"), row=1, col=1)
    if "gas_chp" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["gas_chp"]), name="CHP Elec", stackgroup="elec", fillcolor="#e6550d"), row=1, col=1)
    if "bess_discharger" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["bess_discharger"]), name="BESS Discharge", stackgroup="elec", fillcolor="#9ecae1"), row=1, col=1)

    # 2. HT Steam
    if "gas_chp" in n.links_t.p2.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p2["gas_chp"]), name="CHP Steam", stackgroup="steam", fillcolor="#e6550d"), row=2, col=1)
    if "gas_boiler" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["gas_boiler"]), name="Gas Boiler", stackgroup="steam", fillcolor="#fd8d3c"), row=2, col=1)
    if "electric_boiler" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["electric_boiler"]), name="E-Boiler", stackgroup="steam", fillcolor="#74c476"), row=2, col=1)

    # 3. LT Heat
    if "heat_pump" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["heat_pump"]), name="HTHP Heat", stackgroup="heat", fillcolor="#2ca02c"), row=3, col=1)
    if "steam_to_heat_exchanger" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["steam_to_heat_exchanger"]), name="Steam-HX Heat", stackgroup="heat", fillcolor="#bcbd22"), row=3, col=1)
    if "tes_discharger" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["tes_discharger"]), name="TES Discharge", stackgroup="heat", fillcolor="#a1d99b"), row=3, col=1)

    fig.update_layout(height=800, title_text=title, template="plotly_white", hovermode="x unified")
    return fig


def plot_market_prices_interactive(
    results: Dict[str, Any],
    title: str = "Grid Spot Market Price Dynamics"
):
    """
    Generates an interactive Plotly line chart displaying effective Electricity
    and Natural Gas spot market price profiles [EUR/MWh] for a solved PyPSA network.
    Automatically reflects configuration settings (e.g. Sec19 grid fee discount, CO2 tax).
    """
    n = results["network"]
    snapshots = n.snapshots

    elec_price = None
    if "grid_electricity" in n.generators_t.marginal_cost.columns:
        elec_price = n.generators_t.marginal_cost["grid_electricity"] * 1000.0
    elif "grid_electricity" in n.generators.index:
        mc = float(n.generators.loc["grid_electricity", "marginal_cost"]) * 1000.0
        elec_price = pd.Series(mc, index=snapshots)

    gas_price = None
    if "grid_gas" in n.generators_t.marginal_cost.columns:
        gas_price = n.generators_t.marginal_cost["grid_gas"] * 1000.0
    elif "grid_gas" in n.generators.index:
        mc = float(n.generators.loc["grid_gas", "marginal_cost"]) * 1000.0
        gas_price = pd.Series(mc, index=snapshots)

    if not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(12, 5))
        if elec_price is not None:
            ax.plot(snapshots, elec_price, label="Electricity Spot Price [EUR/MWh]", color="#3182bd", linewidth=1.5)
        if gas_price is not None:
            ax.plot(snapshots, gas_price, label="Natural Gas Spot Price [EUR/MWh]", color="#e6550d", linewidth=1.5)
        ax.set_title(title)
        ax.set_ylabel("Price [EUR/MWh]")
        ax.set_xlabel("Timestamp")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    fig = go.Figure()
    if elec_price is not None:
        fig.add_trace(go.Scatter(x=snapshots, y=elec_price, name="Grid Electricity Price [€/MWh]", line=dict(color="#3182bd", width=2)))
    if gas_price is not None:
        fig.add_trace(go.Scatter(x=snapshots, y=gas_price, name="Natural Gas Price [€/MWh]", line=dict(color="#e6550d", width=2)))

    fig.update_layout(
        title=title,
        xaxis_title="Timestamp",
        yaxis_title="Spot Price [EUR / MWh]",
        template="plotly_white",
        hovermode="x unified"
    )
    return fig


# Backward-compatibility alias
plot_dispatch_with_market_prices_interactive = plot_market_prices_interactive



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


def get_period_effective_tonnage(res: Any, annual_tonnage: float = 450000.0) -> float:
    """
    Calculates period-adjusted production tonnage based on network snapshot length and weighting.
    
    If the network was solved for N snapshots without objective weighting annualization,
    annual tonnage is scaled down proportionally to (N / 8760).
    If objective weighting is already annualized (8760 / N), full annual tonnage is returned.
    """
    if isinstance(res, dict) and "network" in res:
        n = res["network"]
        if hasattr(n, "snapshots"):
            num_snapshots = len(n.snapshots)
            if num_snapshots > 0:
                obj_weight = float(n.snapshot_weightings.objective.iloc[0]) if hasattr(n.snapshot_weightings.objective, "iloc") else float(n.snapshot_weightings.objective)
                # If objective weighting already scales to 8760h (investment mode), use full annual tonnage
                if abs(obj_weight - (8760.0 / num_snapshots)) < 1e-3:
                    return annual_tonnage
                # Otherwise scale annual tonnage proportionally to solved period duration
                return annual_tonnage * (num_snapshots / 8760.0)
    return annual_tonnage


def calculate_curtailment_metrics(res: Dict[str, Any]) -> Tuple[float, float]:
    """Calculates curtailed electricity (%) and curtailed heat (%) from PyPSA network results."""
    if not isinstance(res, dict) or "network" not in res:
        return 0.0, 0.0

    n = res["network"]

    # 1. Calculate Electricity Generation & Curtailment
    tot_elec_generated = 0.0
    tot_elec_curtailed = 0.0

    if hasattr(n, "generators_t") and hasattr(n.generators_t, "p"):
        for gen in n.generators.index:
            if gen in ["grid_electricity", "grid_gas"] or gen.endswith("_dump"):
                continue
            p_actual = float(n.generators_t.p[gen].sum()) if gen in n.generators_t.p.columns else 0.0
            p_opt = float(n.generators.loc[gen, "p_nom_opt" if "p_nom_opt" in n.generators.columns else "p_nom"])
            if hasattr(n.generators_t, "p_max_pu") and gen in n.generators_t.p_max_pu.columns:
                p_potential = float((n.generators_t.p_max_pu[gen] * p_opt).sum())
            else:
                p_potential = p_actual

            tot_elec_generated += p_potential
            curt = max(0.0, p_potential - p_actual)
            tot_elec_curtailed += curt

        if "grid_electricity" in n.generators_t.p.columns:
            tot_elec_generated += float(n.generators_t.p["grid_electricity"].sum())

    if hasattr(n, "links_t") and hasattr(n.links_t, "p0") and "gas_chp" in n.links.index:
        eta_el = float(n.links.loc["gas_chp", "efficiency"]) if "efficiency" in n.links.columns else 0.25
        chp_gas_in = float(n.links_t.p0["gas_chp"].sum()) if "gas_chp" in n.links_t.p0.columns else 0.0
        tot_elec_generated += chp_gas_in * eta_el

    elec_curtailment_pct = (tot_elec_curtailed / tot_elec_generated * 100.0) if tot_elec_generated > 0 else 0.0

    # 2. Calculate Thermal Heat & Steam Generation & Curtailment
    tot_heat_generated = 0.0
    tot_heat_curtailed = 0.0

    if hasattr(n, "generators_t") and hasattr(n.generators_t, "p"):
        for dump_gen in ["steam_dump", "heat_dump"]:
            if dump_gen in n.generators_t.p.columns:
                dump_val = -float(n.generators_t.p[dump_gen].sum())
                if dump_val > 0:
                    tot_heat_curtailed += dump_val

    if hasattr(n, "links_t") and hasattr(n.links_t, "p0"):
        if "gas_chp" in n.links.index:
            eta_th = float(n.links.loc["gas_chp", "efficiency2"]) if "efficiency2" in n.links.columns else 0.50
            chp_gas_in = float(n.links_t.p0["gas_chp"].sum()) if "gas_chp" in n.links_t.p0.columns else 0.0
            tot_heat_generated += chp_gas_in * eta_th

        if "gas_boiler" in n.links.index:
            eta_th = float(n.links.loc["gas_boiler", "efficiency"]) if "efficiency" in n.links.columns else 0.90
            boiler_gas_in = float(n.links_t.p0["gas_boiler"].sum()) if "gas_boiler" in n.links_t.p0.columns else 0.0
            tot_heat_generated += boiler_gas_in * eta_th

        if "electric_boiler" in n.links.index:
            eboiler_out = float(n.links_t.p1["electric_boiler"].sum()) if "electric_boiler" in n.links_t.p1.columns else 0.0
            tot_heat_generated += eboiler_out

        if "heat_pump" in n.links.index:
            hthp_out = float(n.links_t.p1["heat_pump"].sum()) if "heat_pump" in n.links_t.p1.columns else 0.0
            tot_heat_generated += hthp_out

    tot_heat_potential = tot_heat_generated + tot_heat_curtailed
    heat_curtailment_pct = (tot_heat_curtailed / tot_heat_potential * 100.0) if tot_heat_potential > 0 else 0.0

    return round(elec_curtailment_pct, 2), round(heat_curtailment_pct, 2)


def create_summary_dataframe(results_dict: Dict[str, Dict[str, Any]], annual_tonnage: float = 450000.0) -> pd.DataFrame:
    """Compiles scenario results into a clean financial comparison table (EUR/ton, OPEX, CAPEX, CO2, Curtailment)."""
    rows = []
    for scenario_name, res in results_dict.items():
        tot_cost = res["total_cost_eur"]
        eff_tonnage = get_period_effective_tonnage(res, annual_tonnage=annual_tonnage)
        cost_per_ton = tot_cost / eff_tonnage if eff_tonnage > 0 else 0.0
        elec_curt_pct, heat_curt_pct = calculate_curtailment_metrics(res)
        rows.append({
            "Scenario": scenario_name,
            "Total Cost (EUR)": tot_cost,
            "Cost per Ton (EUR/ton)": cost_per_ton,
            "OPEX (EUR)": res["opex_eur"],
            "Annualized CAPEX (EUR)": res["capex_annualized_eur"],
            "Emissions (tCO2)": res["emissions_t_co2"],
            "Peak Grid Demand (MW)": res["peak_grid_demand_kw"] / 1000.0,
            "Curtailed Elec (%)": elec_curt_pct,
            "Curtailed Heat (%)": heat_curt_pct,
            "Sec19 Compliant": not res["sec19_violation"],
        })

    df_summary = pd.DataFrame(rows).set_index("Scenario")
    return df_summary


def plot_scenario_cost_per_ton_interactive(
    scenarios: Dict[str, Any],
    annual_tonnage: float = 450000.0,
    title: str = "Unit Production Cost Comparison (€/ton)"
):
    """
    Generates a modular bar chart comparing EUR/ton across arbitrary scenarios (2, 3, or N scenarios).
    Automatically scales production tonnage to match the period duration of each solved scenario.
    
    Parameters
    ----------
    scenarios : Dict[str, Any]
        Mapping of Scenario Name -> (PyPSA results dict OR numeric float/int EUR/ton value).
        Examples:
            # 2 Scenarios:
            plot_scenario_cost_per_ton_interactive({"Baseline": 145.20, "Operation Hub": meta_op})
            
            # 3 Scenarios:
            plot_scenario_cost_per_ton_interactive({"Baseline": 145.20, "Operation Hub": meta_op, "Decision Hub": meta_inv})
    annual_tonnage : float
        Annual production output in tons (default 450,000 tons/year).
    title : str
        Chart title.
    """
    labels = []
    values = []

    for name, val in scenarios.items():
        labels.append(name)
        eff_tonnage = get_period_effective_tonnage(val, annual_tonnage=annual_tonnage)
        if isinstance(val, (int, float)):
            # If input is large (> 10,000), interpret as total cost EUR; otherwise treat directly as EUR/ton
            cost_per_ton = float(val) / eff_tonnage if float(val) > 10000.0 else float(val)
        elif isinstance(val, dict):
            if "total_cost_eur" in val:
                cost_per_ton = float(val["total_cost_eur"]) / eff_tonnage if eff_tonnage > 0 else 0.0
            elif "cost_per_ton" in val:
                cost_per_ton = float(val["cost_per_ton"])
            else:
                cost_per_ton = 0.0
        else:
            cost_per_ton = 0.0
        values.append(cost_per_ton)

    colors = ["#e6550d", "#3182bd", "#2ca02c", "#74c476", "#fd8d3c", "#9ecae1"]
    bar_colors = [colors[i % len(colors)] for i in range(len(labels))]

    if not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(labels, values, color=bar_colors)
        ax.set_ylabel("EUR / ton")
        ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.5)
        for i, v in enumerate(values):
            ax.text(i, v + (max(values) * 0.01 if values else 1.0), f"€{v:.2f}/t", ha="center", fontweight="bold")
        plt.tight_layout()
        return fig

    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            marker_color=bar_colors,
            text=[f"€{v:.2f} / ton" for v in values],
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Unit Cost: €%{y:.2f} / ton<extra></extra>"
        )
    ])
    fig.update_layout(
        title=title,
        yaxis_title="Unit Cost [EUR / ton]",
        xaxis_title="Scenario Tiers",
        template="plotly_white"
    )
    return fig


def create_pypsa_asset_sizing_table(results_or_net: Any) -> pd.DataFrame:
    """Extracts optimal asset capacities from a solved PyPSA network or results dict."""
    n = results_or_net.get("network", results_or_net) if isinstance(results_or_net, dict) else getattr(results_or_net, "network", results_or_net)

    asset_rows = []
    if hasattr(n, "generators") and not n.generators.empty:
        for name, row in n.generators.iterrows():
            p_opt = float(getattr(row, "p_nom_opt", getattr(row, "p_nom", 0.0)))
            # Exclude grid imports and emergency dump generators
            if p_opt > 0 and name not in ["grid_electricity", "grid_gas"] and not name.endswith("_dump"):
                asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{p_opt:,.2f}", "Unit": "kWp" if "pv" in name.lower() else "kW"})

    if hasattr(n, "links") and not n.links.empty:
        for name, row in n.links.iterrows():
            p_opt = float(getattr(row, "p_nom_opt", getattr(row, "p_nom", 0.0)))
            if p_opt > 0 and name != "steam_to_heat_exchanger":
                unit = "kW" if "bess" in name.lower() else "kW_th"
                asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{p_opt:,.2f}", "Unit": unit})

    if hasattr(n, "stores") and not n.stores.empty:
        for name, row in n.stores.iterrows():
            e_opt = float(getattr(row, "e_nom_opt", getattr(row, "e_nom", 0.0)))
            if e_opt > 0:
                unit = "kWh_th" if "tes" in name.lower() else "kWh"
                asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{e_opt:,.2f}", "Unit": unit})

    return pd.DataFrame(asset_rows)


def explore_network_interactive(results_or_net: Any, active_only: bool = True):
    """
    Generates an interactive Folium web map of the PyPSA topology pre- or post-solve using n.explore().
    
    Parameters
    ----------
    results_or_net : Any
        PyPSA network instance or dictionary containing 'network'.
    active_only : bool, default True
        If True and the network is solved, extendable components with zero optimal built capacity
        (p_nom_opt <= 1e-3 or e_nom_opt <= 1e-3) will be excluded from the interactive map display.
    """
    n = results_or_net.get("network", results_or_net) if isinstance(results_or_net, dict) else getattr(results_or_net, "network", results_or_net)

    # Make a copy if active_only filtering is requested to avoid mutating the original network
    if active_only:
        n_disp = n.copy()
        # Remove extendable generators with zero capacity built
        if hasattr(n_disp, "generators") and "p_nom_opt" in n_disp.generators.columns:
            unbuilt_gens = n_disp.generators[
                (n_disp.generators.get("p_nom_extendable", False)) & (n_disp.generators.p_nom_opt <= 1e-3)
            ].index
            for g in list(unbuilt_gens):
                n_disp.remove("Generator", g)

        # Remove extendable links with zero capacity built
        if hasattr(n_disp, "links") and "p_nom_opt" in n_disp.links.columns:
            unbuilt_links = n_disp.links[
                (n_disp.links.get("p_nom_extendable", False)) & (n_disp.links.p_nom_opt <= 1e-3)
            ].index
            for l in list(unbuilt_links):
                n_disp.remove("Link", l)

        # Remove extendable stores with zero capacity built
        if hasattr(n_disp, "stores") and "e_nom_opt" in n_disp.stores.columns:
            unbuilt_stores = n_disp.stores[
                (n_disp.stores.get("e_nom_extendable", False)) & (n_disp.stores.e_nom_opt <= 1e-3)
            ].index
            for s in list(unbuilt_stores):
                n_disp.remove("Store", s)
    else:
        n_disp = n

    # Ensure buses have default coordinates if unassigned
    default_coords = {
        "b_elec": (6.8320, 51.1720),
        "b_gas": (6.8310, 51.1710),
        "b_steam_ht": (6.8340, 51.1730),
        "b_heat_lt": (6.8350, 51.1715),
        "bess_bus": (6.8325, 51.1725),
        "tes_bus": (6.8355, 51.1710),
    }
    for bus_name, (x, y) in default_coords.items():
        if bus_name in n_disp.buses.index:
            if pd.isna(n_disp.buses.loc[bus_name, "x"]) or n_disp.buses.loc[bus_name, "x"] == 0:
                n_disp.buses.loc[bus_name, "x"] = x
            if pd.isna(n_disp.buses.loc[bus_name, "y"]) or n_disp.buses.loc[bus_name, "y"] == 0:
                n_disp.buses.loc[bus_name, "y"] = y

    return n_disp.explore()


def plot_network_topology_static(
    results_or_net: Any, title: str = "Henkel Holthausen PyPSA Topology Diagram"
) -> plt.Figure:
    """
    Generates a clean 2D static schematic diagram of the PyPSA topology using native n.plot().

    Parameters
    ----------
    results_or_net : Any
        PyPSA network instance or dictionary containing 'network'.
    title : str
        Title for the plot figure.
    """
    n = results_or_net.get("network", results_or_net) if isinstance(results_or_net, dict) else getattr(results_or_net, "network", results_or_net)

    # Assign diagram layout coordinates (x, y) to site buses if unassigned
    coords = {
        "b_elec": (0.0, 2.0),
        "b_gas": (-2.0, 2.0),
        "b_steam_ht": (0.0, 0.0),
        "b_heat_lt": (0.0, -2.0),
        "bess_bus": (2.0, 2.0),
        "tes_bus": (2.0, -2.0),
    }
    for bus, (x, y) in coords.items():
        if bus in n.buses.index:
            n.buses.loc[bus, "x"] = x
            n.buses.loc[bus, "y"] = y

    fig, ax = plt.subplots(figsize=(9, 6))
    n.plot(
        ax=ax,
        bus_colors={
            "b_elec": "#3182bd",
            "b_gas": "#6baed6",
            "b_steam_ht": "#d62728",
            "b_heat_lt": "#2ca02c",
            "bess_bus": "#9ecae1",
            "tes_bus": "#a1d99b",
        },
        bus_sizes=0.04,
        link_widths=2.5,
        line_widths=2.5,
        title=title,
    )
    plt.tight_layout()
    return fig


def plot_network_topology_graph(
    results_or_net: Any, title: str = "Henkel Holthausen PyPSA Topology NetworkX Graph"
) -> plt.Figure:
    """
    Generates a static NetworkX directed graph representation using PyPSA's native n.graph().

    Parameters
    ----------
    results_or_net : Any
        PyPSA network instance or dictionary containing 'network'.
    title : str
        Title for the plot figure.
    """
    import networkx as nx

    n = results_or_net.get("network", results_or_net) if isinstance(results_or_net, dict) else getattr(results_or_net, "network", results_or_net)

    G = n.graph()
    fig, ax = plt.subplots(figsize=(9, 6))
    pos = nx.spring_layout(G, seed=42)

    nx.draw_networkx(
        G,
        pos,
        ax=ax,
        with_labels=True,
        node_color="#3182bd",
        node_size=2500,
        font_color="white",
        font_size=10,
        font_weight="bold",
        edge_color="gray",
        arrows=True,
        arrowsize=20,
    )

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    return fig


def plot_network_schematic(
    results_or_net: Any, title: str = "Henkel Holthausen Energy System Schematic Diagram"
) -> plt.Figure:
    """
    Renders an explicit block diagram schematic showing Buses, Energy Conversion Assets
    (CHP, Gas Boiler, E-Boiler, HTHP), Supply Generators (Grid, Solar), and Demand Sinks.
    Only active components (with capacity > 0) are rendered. Dynamic sizing labels are extracted directly from PyPSA.

    Parameters
    ----------
    results_or_net : Any
        PyPSA network instance or dictionary containing 'network'.
    title : str
        Title for the plot figure.
    """
    n = results_or_net.get("network", results_or_net) if isinstance(results_or_net, dict) else getattr(results_or_net, "network", results_or_net)

    fig, ax = plt.subplots(figsize=(12, 7))

    # Helper function to check component capacity from PyPSA network
    def get_component_capacity(comp_type: str, name: str) -> float:
        df = getattr(n, comp_type, pd.DataFrame())
        if df.empty:
            return 0.0

        target_name = name
        if name not in df.index:
            alias = name.replace("_store", "").replace("_gen", "")
            if alias in df.index:
                target_name = alias
            else:
                return 0.0

        row = df.loc[target_name]

        is_ext = bool(row.get("p_nom_extendable", False)) if comp_type != "stores" else bool(row.get("e_nom_extendable", False))

        if is_ext:
            opt_col = "e_nom_opt" if comp_type == "stores" else "p_nom_opt"
            if opt_col in row.index and not pd.isna(row[opt_col]) and float(row[opt_col]) > 1e-3:
                return float(row[opt_col])

        # Fallback to fixed p_nom / e_nom
        nom_col = "e_nom" if comp_type == "stores" else "p_nom"
        val = row.get(nom_col, 0.0)
        return float(val) if not pd.isna(val) else 0.0

    # Layout node templates
    nodes = {
        # Supply Generators
        "grid_gas": {"pos": (1, 8.5), "color": "#6baed6", "label": "Grid Gas\n(Import)"},
        "grid_electricity": {"pos": (1, 6.2), "color": "#3182bd", "label": "Grid Power\n(Import)"},
        "pv_ppa": {"pos": (1, 4.2), "color": "#ffbb78", "type": "generators", "prefix": "Solar PPA", "unit": "MW"},
        "solar_pv": {"pos": (1, 2.2), "color": "#fec44f", "type": "generators", "prefix": "Rooftop PV", "unit": "MWp"},
        "wind_ppa": {"pos": (1, 0.2), "color": "#98df8a", "type": "generators", "prefix": "Wind PPA", "unit": "MW"},

        # Central Energy Buses
        "b_gas": {"pos": (4, 8), "color": "#6baed6", "label": "Gas Bus\n[b_gas]", "is_bus": True},
        "b_elec": {"pos": (4, 5), "color": "#3182bd", "label": "Electricity Bus\n[b_elec]", "is_bus": True},
        "b_steam_ht": {"pos": (7, 6.5), "color": "#d62728", "label": "Steam Bus (16 bar)\n[b_steam_ht]", "is_bus": True},
        "b_heat_lt": {"pos": (7, 2.5), "color": "#2ca02c", "label": "Heat Bus (~80°C)\n[b_heat_lt]", "is_bus": True},

        # Conversion Assets / Links
        "gas_chp": {"pos": (5.5, 7.5), "color": "#e6550d", "type": "links", "custom_chp": True},
        "gas_boiler": {"pos": (5.5, 8.8), "color": "#fd8d3c", "type": "links", "prefix": "Gas Boiler", "unit": "MW_th", "custom_boiler": True},
        "electric_boiler": {"pos": (5.5, 5), "color": "#74c476", "type": "links", "prefix": "Electric Boiler", "unit": "MW_th"},
        "heat_pump": {"pos": (5.5, 3.5), "color": "#2ca02c", "type": "links", "prefix": "HTHP Heat Pump", "unit": "MW_th"},
        "steam_to_heat_exchanger": {"pos": (7, 4.5), "color": "#98df8a", "type": "links", "label": "Steam Exchanger\n(95% Eff)"},

        # Storage & Demand Sinks
        "bess": {"pos": (4, 3.5), "color": "#9ecae1", "type": "stores", "prefix": "BESS Storage", "unit": "MWh"},
        "tes": {"pos": (7, 1), "color": "#a1d99b", "type": "stores", "prefix": "TES Storage", "unit": "MWh_th"},
        "demand_elec": {"pos": (10, 5), "color": "#1f77b4", "label": "Elec Demand\n(60 MW_el)"},
        "demand_steam": {"pos": (10, 6.5), "color": "#d62728", "label": "Steam Demand\n(160 MW_th)"},
        "demand_heat": {"pos": (10, 2.5), "color": "#2ca02c", "label": "Heat Demand\n(60 MW_th)"},
    }

    # Filter active components present in network with capacity > 0
    active_nodes = {}
    for name, info in nodes.items():
        if info.get("is_bus", False):
            if name in n.buses.index:
                active_nodes[name] = info
        elif name in ["grid_gas", "grid_electricity", "demand_elec", "demand_steam", "demand_heat"]:
            if name in n.generators.index or name in n.loads.index:
                active_nodes[name] = info
        elif "type" in info:
            cap = get_component_capacity(info["type"], name)
            if cap > 1e-3:
                comp_df = getattr(n, info["type"], pd.DataFrame())
                target_idx = name if name in comp_df.index else name.replace("_store", "").replace("_gen", "")
                row = comp_df.loc[target_idx]
                # Format label dynamically with exact PyPSA capacity
                if info.get("custom_chp", False):
                    eta_el = float(row.get("efficiency", 0.25))
                    eta_th = float(row.get("efficiency2", 0.50))
                    chp_el = cap * eta_el
                    chp_th = cap * eta_th
                    info["label"] = f"Gas CHP\n({chp_el/1000:.1f} MW_el / {chp_th/1000:.1f} MW_th)"
                elif info.get("custom_boiler", False):
                    eta_th = float(row.get("efficiency", 0.90))
                    boiler_th = cap * eta_th
                    info["label"] = f"Gas Boiler\n({boiler_th/1000:.2f} MW_th)"
                elif "prefix" in info:
                    unit = info.get("unit", "MW")
                    if info["type"] == "stores":
                        display_val = cap / 1000.0 if cap >= 1000.0 else cap
                        unit_str = unit if cap >= 1000.0 else unit.replace("MWh", "kWh")
                        info["label"] = f"{info['prefix']}\n({display_val:.2f} {unit_str})"
                    else:
                        info["label"] = f"{info['prefix']}\n({cap/1000:.2f} {unit})"
                active_nodes[name] = info

    # Draw boxes for active nodes
    for name, info in active_nodes.items():
        x, y = info["pos"]
        is_bus = info.get("is_bus", False)
        box_style = "round,pad=0.3" if not is_bus else "square,pad=0.2"

        ax.text(
            x, y, info["label"],
            ha="center", va="center",
            fontsize=8.5, fontweight="bold", color="white" if is_bus else "black",
            bbox=dict(boxstyle=box_style, facecolor=info["color"], edgecolor="black", alpha=0.9, lw=1.5)
        )

    # Connections / Flow Arrows
    connections = [
        ("grid_gas", "b_gas"),
        ("grid_electricity", "b_elec"),
        ("pv_ppa", "b_elec"),
        ("solar_pv", "b_elec"),
        ("wind_ppa", "b_elec"),
        ("b_gas", "gas_chp"),
        ("b_gas", "gas_boiler"),
        ("gas_chp", "b_steam_ht"),
        ("gas_chp", "b_elec"),
        ("gas_boiler", "b_steam_ht"),
        ("b_elec", "electric_boiler"),
        ("electric_boiler", "b_steam_ht"),
        ("b_elec", "heat_pump"),
        ("heat_pump", "b_heat_lt"),
        ("b_steam_ht", "steam_to_heat_exchanger"),
        ("steam_to_heat_exchanger", "b_heat_lt"),
        ("b_elec", "demand_elec"),
        ("b_steam_ht", "demand_steam"),
        ("b_heat_lt", "demand_heat"),
        ("b_elec", "bess"),
        ("b_heat_lt", "tes"),
    ]

    for src, dst in connections:
        if src in active_nodes and dst in active_nodes:
            x1, y1 = active_nodes[src]["pos"]
            x2, y2 = active_nodes[dst]["pos"]
            ax.annotate(
                "", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color="gray", lw=1.8, mutation_scale=15),
            )

    ax.set_xlim(-0.5, 11.5)
    ax.set_ylim(-0.5, 10.0)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    return fig

