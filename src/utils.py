"""
Utility module for PyPSA Energy System Visual Reporting and Financial Economics Analysis.

Provides interactive Plotly dashboards (for Jupyter Notebooks) alongside matplotlib figure exports based on:
- .agent/skills/pypsa-reporting (diagnostic panels, multi-carrier dispatch stacks, price duration curves)
- .agent/skills/pypsa-asset-economics (diverging net margins, LCOE/LCOH calculation, Sec19 grid fee protection)
"""

import warnings
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


def _slice_snapshots_by_window(
    n: Any,
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
    config: Optional[Any] = None,
) -> pd.DatetimeIndex:
    """
    Resolves snapshot datetime index sliced for a duration (default 7 days).
    Validates input date format, issues non-crashing warning if out of bounds,
    and falls back to config.start_time or network first snapshot.
    """
    snapshots = n.snapshots
    if len(snapshots) == 0:
        return snapshots

    # 1. Determine default starting time
    default_start = None
    if config is not None and hasattr(config, "start_time") and config.start_time:
        try:
            default_start = pd.to_datetime(config.start_time, dayfirst=True)
        except Exception:
            pass

    if default_start is None:
        default_start = snapshots[0]

    # Ensure default_start is within snapshot range, else use snapshots[0]
    if default_start < snapshots[0] or default_start > snapshots[-1]:
        default_start = snapshots[0]

    target_start = default_start

    # 2. Parse user-provided start_time if given
    if start_time is not None:
        try:
            parsed_dt = pd.to_datetime(start_time, dayfirst=True)
            # Check if within optimization bounds
            if parsed_dt < snapshots[0] or parsed_dt > snapshots[-1]:
                warnings.warn(
                    f"Specified start_time '{start_time}' ({parsed_dt}) is outside the optimization period "
                    f"[{snapshots[0]} to {snapshots[-1]}]. Falling back to default start_time '{default_start}'.",
                    UserWarning,
                    stacklevel=2,
                )
                target_start = default_start
            else:
                target_start = parsed_dt
        except Exception as e:
            warnings.warn(
                f"Could not parse start_time '{start_time}' ({e}). "
                f"Falling back to default start_time '{default_start}'.",
                UserWarning,
                stacklevel=2,
            )
            target_start = default_start

    # 3. Calculate end time based on duration
    target_end = target_start + pd.Timedelta(days=duration_days)

    # Slice snapshots
    sliced = snapshots[(snapshots >= target_start) & (snapshots <= target_end)]
    if len(sliced) == 0:
        warnings.warn(
            f"No snapshots found between {target_start} and {target_end}. Returning full snapshots.",
            UserWarning,
            stacklevel=2,
        )
        return snapshots
    return sliced


def plot_dispatch_stacks(
    results: Dict[str, Any],
    title: str = "PyPSA Multi-Carrier Dispatch Stack",
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
) -> plt.Figure:
    """
    Generates a static 3-panel Matplotlib line plot figure showing dispatch profiles and load demand
    for electricity, high-temperature steam, and low-temperature process heat.
    Includes complete legend coverage for all activated components.
    """
    n = results["network"]
    config = results.get("config", None)
    snapshots = _slice_snapshots_by_window(n, start_time=start_time, duration_days=duration_days, config=config)

    fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True)

    # ---------------------------------------------------------
    # 1. Electricity Bus (b_elec)
    # ---------------------------------------------------------
    ax0 = axes[0]
    elec_gen_candidates = [
        ("grid_electricity", "Grid Electricity", "#3182bd"),
        ("solar_pv", "Solar PV", "#fec44f"),
        ("pv_ppa", "PV PPA", "#ffbb78"),
        ("wind_ppa", "Wind PPA", "#98df8a"),
    ]
    for gen_id, label_name, color in elec_gen_candidates:
        if hasattr(n, "generators") and gen_id in n.generators.index:
            if hasattr(n, "generators_t") and hasattr(n.generators_t, "p") and gen_id in n.generators_t.p.columns:
                series = n.generators_t.p.loc[snapshots, gen_id]
            else:
                series = pd.Series(0.0, index=snapshots)
            ax0.plot(snapshots, series, label=f"{label_name} [kW]", color=color, linewidth=2.0)

    if hasattr(n, "links") and "gas_chp" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "gas_chp" in n.links_t.p1.columns:
            chp_elec = np.abs(n.links_t.p1.loc[snapshots, "gas_chp"])
        else:
            chp_elec = pd.Series(0.0, index=snapshots)
        ax0.plot(snapshots, chp_elec, label="CHP Electricity [kW]", color="#e6550d", linewidth=2.0)

    if hasattr(n, "links") and "bess_discharger" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "bess_discharger" in n.links_t.p1.columns:
            bess_p = np.abs(n.links_t.p1.loc[snapshots, "bess_discharger"])
        else:
            bess_p = pd.Series(0.0, index=snapshots)
        ax0.plot(snapshots, bess_p, label="BESS Discharge [kW]", color="#9ecae1", linewidth=2.0)

    # Negative Outgoing Sinks & Export
    if hasattr(n, "generators") and "grid_export" in n.generators.index:
        if hasattr(n, "generators_t") and hasattr(n.generators_t, "p") and "grid_export" in n.generators_t.p.columns:
            p_exp = -np.abs(n.generators_t.p.loc[snapshots, "grid_export"])
            ax0.plot(snapshots, p_exp, label="Grid Export [kW]", color="#006d2c", linewidth=2.0, linestyle=":")

    if hasattr(n, "links") and "bess_charger" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p0") and "bess_charger" in n.links_t.p0.columns:
            bess_chg = -np.abs(n.links_t.p0.loc[snapshots, "bess_charger"])
            ax0.plot(snapshots, bess_chg, label="BESS Charge [kW]", color="#756bb1", linewidth=2.0, linestyle=":")

    if hasattr(n, "loads") and "demand_elec" in n.loads.index:
        if hasattr(n, "loads_t") and hasattr(n.loads_t, "p_set") and "demand_elec" in n.loads_t.p_set.columns:
            demand_e = n.loads_t.p_set.loc[snapshots, "demand_elec"]
        elif hasattr(n, "loads_t") and hasattr(n.loads_t, "p") and "demand_elec" in n.loads_t.p.columns:
            demand_e = n.loads_t.p.loc[snapshots, "demand_elec"]
        else:
            demand_e = pd.Series(0.0, index=snapshots)
        ax0.plot(snapshots, demand_e, label="Demand Elec [kW]", color="black", linestyle="--", linewidth=2.5)

    ax0.set_title("Electricity Supply & Outgoing Flow Dynamics (b_elec) [kW]", fontsize=12, fontweight="bold")
    ax0.set_ylabel("Power [kW]", fontsize=10, fontweight="bold")
    ax0.grid(True, linestyle="--", alpha=0.5)
    ax0.legend(bbox_to_anchor=(1.02, 1.0), loc="upper left", frameon=True, fontsize=9)

    # ---------------------------------------------------------
    # 2. HT Steam Bus (b_steam_ht)
    # ---------------------------------------------------------
    ax1 = axes[1]
    if hasattr(n, "links") and "gas_chp" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p2") and "gas_chp" in n.links_t.p2.columns:
            chp_steam = np.abs(n.links_t.p2.loc[snapshots, "gas_chp"])
        else:
            chp_steam = pd.Series(0.0, index=snapshots)
        ax1.plot(snapshots, chp_steam, label="CHP Steam [kW_th]", color="#e6550d", linewidth=2.0)

    if hasattr(n, "links") and "gas_boiler" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "gas_boiler" in n.links_t.p1.columns:
            gb_steam = np.abs(n.links_t.p1.loc[snapshots, "gas_boiler"])
        else:
            gb_steam = pd.Series(0.0, index=snapshots)
        ax1.plot(snapshots, gb_steam, label="Gas Boiler [kW_th]", color="#fd8d3c", linewidth=2.0)

    if hasattr(n, "links") and "electric_boiler" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "electric_boiler" in n.links_t.p1.columns:
            eb_steam = np.abs(n.links_t.p1.loc[snapshots, "electric_boiler"])
        else:
            eb_steam = pd.Series(0.0, index=snapshots)
        ax1.plot(snapshots, eb_steam, label="E-Boiler [kW_th]", color="#74c476", linewidth=2.0)

    if hasattr(n, "loads") and "demand_steam" in n.loads.index:
        if hasattr(n, "loads_t") and hasattr(n.loads_t, "p_set") and "demand_steam" in n.loads_t.p_set.columns:
            demand_s = n.loads_t.p_set.loc[snapshots, "demand_steam"]
        elif hasattr(n, "loads_t") and hasattr(n.loads_t, "p") and "demand_steam" in n.loads_t.p.columns:
            demand_s = n.loads_t.p.loc[snapshots, "demand_steam"]
        else:
            demand_s = pd.Series(0.0, index=snapshots)
        ax1.plot(snapshots, demand_s, label="Demand Steam [kW_th]", color="black", linestyle="--", linewidth=2.5)

    ax1.set_title("High-Temperature Steam Supply & Demand Dynamics (b_steam_ht) [kW_th]", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Thermal Power [kW_th]", fontsize=10, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(bbox_to_anchor=(1.02, 1.0), loc="upper left", frameon=True, fontsize=9)

    # ---------------------------------------------------------
    # 3. LT Process Heat Bus (b_heat_lt)
    # ---------------------------------------------------------
    ax2 = axes[2]
    if hasattr(n, "links") and "heat_pump" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "heat_pump" in n.links_t.p1.columns:
            hp_heat = np.abs(n.links_t.p1.loc[snapshots, "heat_pump"])
        else:
            hp_heat = pd.Series(0.0, index=snapshots)
        ax2.plot(snapshots, hp_heat, label="HTHP Heat [kW_th]", color="#2ca02c", linewidth=2.0)

    if hasattr(n, "links") and "steam_to_heat_exchanger" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "steam_to_heat_exchanger" in n.links_t.p1.columns:
            hx_heat = np.abs(n.links_t.p1.loc[snapshots, "steam_to_heat_exchanger"])
        else:
            hx_heat = pd.Series(0.0, index=snapshots)
        ax2.plot(snapshots, hx_heat, label="Steam-HX Heat [kW_th]", color="#bcbd22", linewidth=2.0)

    if hasattr(n, "links") and "tes_discharger" in n.links.index:
        if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "tes_discharger" in n.links_t.p1.columns:
            tes_p = np.abs(n.links_t.p1.loc[snapshots, "tes_discharger"])
        else:
            tes_p = pd.Series(0.0, index=snapshots)
        ax2.plot(snapshots, tes_p, label="TES Discharge [kW_th]", color="#a1d99b", linewidth=2.0)

    if hasattr(n, "loads") and "demand_heat" in n.loads.index:
        if hasattr(n, "loads_t") and hasattr(n.loads_t, "p_set") and "demand_heat" in n.loads_t.p_set.columns:
            demand_h = n.loads_t.p_set.loc[snapshots, "demand_heat"]
        elif hasattr(n, "loads_t") and hasattr(n.loads_t, "p") and "demand_heat" in n.loads_t.p.columns:
            demand_h = n.loads_t.p.loc[snapshots, "demand_heat"]
        else:
            demand_h = pd.Series(0.0, index=snapshots)
        ax2.plot(snapshots, demand_h, label="Demand Heat [kW_th]", color="black", linestyle="--", linewidth=2.5)

    ax2.set_title("Low-Temperature Process Heat Supply & Demand Dynamics (b_heat_lt) [kW_th]", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Timestamp", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Thermal Power [kW_th]", fontsize=10, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(bbox_to_anchor=(1.02, 1.0), loc="upper left", frameon=True, fontsize=9)

    plt.tight_layout()
    return fig, axes


def plot_dispatch_stacks_interactive(
    results: Dict[str, Any],
    title: str = "PyPSA 3-Carrier Energy Dispatch Stack (1-Week Window)",
    mode: str = "interactive",
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
):
    """
    Generates an interactive Plotly dynamic stacked area chart or static Matplotlib plot displaying 
    hourly energy dispatch stacks across Electricity (b_elec), High-Temp Steam (b_steam_ht), 
    and Low-Temp Heat (b_heat_lt) buses.
    
    Supports both `mode="interactive"` (returns Plotly Figure) and `mode="static"` (returns Matplotlib Figure).
    """
    if mode == "static":
        fig, _ = plot_dispatch_stacks(results, start_time=start_time, duration_days=duration_days)
        return fig

    if "network" not in results:
        import warnings
        warnings.warn(
            "Legacy results format detected in plot_dispatch_stacks_interactive. "
            "Please update caller to pass full PyPSA solver dictionary `hes.solve()`. "
            "Returning empty Plotly figure.",
            DeprecationWarning,
            stacklevel=2,
        )

    n = results["network"]
    snapshots = n.snapshots

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Electricity Bus (b_elec) [kW]", "HT Steam Bus (b_steam_ht) [kW_th]", "LT Process Heat Bus (b_heat_lt) [kW_th]"),
        vertical_spacing=0.08,
        shared_xaxes=True,
    )

    # 1. Electricity - Positive Supply Stack
    if "grid_electricity" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["grid_electricity"], name="Grid Elec", stackgroup="elec_supply", fillcolor="#3182bd"), row=1, col=1)
    if "solar_pv" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["solar_pv"], name="Solar PV", stackgroup="elec_supply", fillcolor="#fec44f"), row=1, col=1)
    if "pv_ppa" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["pv_ppa"], name="PV PPA", stackgroup="elec_supply", fillcolor="#ffbb78"), row=1, col=1)
    if "wind_ppa" in n.generators_t.p.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=n.generators_t.p["wind_ppa"], name="Wind PPA", stackgroup="elec_supply", fillcolor="#98df8a"), row=1, col=1)
    if "gas_chp" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["gas_chp"]), name="CHP Elec", stackgroup="elec_supply", fillcolor="#e6550d"), row=1, col=1)
    if "bess_discharger" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["bess_discharger"]), name="BESS Discharge", stackgroup="elec_supply", fillcolor="#9ecae1"), row=1, col=1)

    # 1. Electricity - Negative Outgoing Sinks & Export Stack
    if "grid_export" in n.generators_t.p.columns:
        # PyPSA stores p <= 0 for grid_export generator
        p_exp_neg = -np.abs(n.generators_t.p["grid_export"])
        fig.add_trace(go.Scatter(x=snapshots, y=p_exp_neg, name="Grid Export", stackgroup="elec_sink", fillcolor="#006d2c"), row=1, col=1)

    if "bess_charger" in n.links_t.p0.columns:
        bess_chg_neg = -np.abs(n.links_t.p0["bess_charger"])
        fig.add_trace(go.Scatter(x=snapshots, y=bess_chg_neg, name="BESS Charge", stackgroup="elec_sink", fillcolor="#756bb1"), row=1, col=1)

    if "heat_pump" in n.links_t.p0.columns:
        hp_elec_neg = -np.abs(n.links_t.p0["heat_pump"])
        fig.add_trace(go.Scatter(x=snapshots, y=hp_elec_neg, name="HTHP Elec Power", stackgroup="elec_sink", fillcolor="#17becf"), row=1, col=1)

    if "electric_boiler" in n.links_t.p0.columns:
        eb_elec_neg = -np.abs(n.links_t.p0["electric_boiler"])
        fig.add_trace(go.Scatter(x=snapshots, y=eb_elec_neg, name="E-Boiler Elec Power", stackgroup="elec_sink", fillcolor="#8c564b"), row=1, col=1)

    if "solar_pv" in n.generators.index and hasattr(n.generators_t, "p_max_pu") and "solar_pv" in n.generators_t.p_max_pu.columns:
        val = n.generators.loc["solar_pv", "p_nom_opt"] if "p_nom_opt" in n.generators.columns else n.generators.loc["solar_pv", "p_nom"]
        p_opt = float(val) if not pd.isna(val) else float(n.generators.loc["solar_pv", "p_nom"])
        if p_opt > 0:
            p_pot = n.generators_t.p_max_pu["solar_pv"] * p_opt
            p_act = n.generators_t.p["solar_pv"] if "solar_pv" in n.generators_t.p.columns else 0.0
            p_curt_neg = -np.maximum(0.0, p_pot - p_act)
            if float(np.abs(p_curt_neg).sum()) > 0:
                fig.add_trace(go.Scatter(x=snapshots, y=p_curt_neg, name="Solar Curtailed", stackgroup="elec_sink", fillcolor="#7f7f7f"), row=1, col=1)

    if hasattr(n, "loads") and "demand_elec" in n.loads.index:
        if hasattr(n, "loads_t") and hasattr(n.loads_t, "p_set") and "demand_elec" in n.loads_t.p_set.columns:
            fig.add_trace(go.Scatter(x=snapshots, y=n.loads_t.p_set["demand_elec"], name="Demand Elec", line=dict(color="black", dash="dash", width=2.5)), row=1, col=1)
        elif hasattr(n, "loads_t") and hasattr(n.loads_t, "p") and "demand_elec" in n.loads_t.p.columns:
            fig.add_trace(go.Scatter(x=snapshots, y=n.loads_t.p["demand_elec"], name="Demand Elec", line=dict(color="black", dash="dash", width=2.5)), row=1, col=1)

    # 2. HT Steam
    if "gas_chp" in n.links_t.p2.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p2["gas_chp"]), name="CHP Steam", stackgroup="steam", fillcolor="#e6550d"), row=2, col=1)
    if "gas_boiler" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["gas_boiler"]), name="Gas Boiler", stackgroup="steam", fillcolor="#fd8d3c"), row=2, col=1)
    if "electric_boiler" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["electric_boiler"]), name="E-Boiler", stackgroup="steam", fillcolor="#74c476"), row=2, col=1)
    if hasattr(n, "loads") and "demand_steam" in n.loads.index:
        if hasattr(n, "loads_t") and hasattr(n.loads_t, "p_set") and "demand_steam" in n.loads_t.p_set.columns:
            fig.add_trace(go.Scatter(x=snapshots, y=n.loads_t.p_set["demand_steam"], name="Demand Steam", line=dict(color="black", dash="dash", width=2.5)), row=2, col=1)
        elif hasattr(n, "loads_t") and hasattr(n.loads_t, "p") and "demand_steam" in n.loads_t.p.columns:
            fig.add_trace(go.Scatter(x=snapshots, y=n.loads_t.p["demand_steam"], name="Demand Steam", line=dict(color="black", dash="dash", width=2.5)), row=2, col=1)

    # 3. LT Heat
    if "heat_pump" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["heat_pump"]), name="HTHP Heat", stackgroup="heat", fillcolor="#2ca02c"), row=3, col=1)
    if "steam_to_heat_exchanger" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["steam_to_heat_exchanger"]), name="Steam-HX Heat", stackgroup="heat", fillcolor="#bcbd22"), row=3, col=1)
    if "tes_discharger" in n.links_t.p1.columns:
        fig.add_trace(go.Scatter(x=snapshots, y=np.abs(n.links_t.p1["tes_discharger"]), name="TES Discharge", stackgroup="heat", fillcolor="#a1d99b"), row=3, col=1)
    if hasattr(n, "loads") and "demand_heat" in n.loads.index:
        if hasattr(n, "loads_t") and hasattr(n.loads_t, "p_set") and "demand_heat" in n.loads_t.p_set.columns:
            fig.add_trace(go.Scatter(x=snapshots, y=n.loads_t.p_set["demand_heat"], name="Demand Heat", line=dict(color="black", dash="dash", width=2.5)), row=3, col=1)
        elif hasattr(n, "loads_t") and hasattr(n.loads_t, "p") and "demand_heat" in n.loads_t.p.columns:
            fig.add_trace(go.Scatter(x=snapshots, y=n.loads_t.p["demand_heat"], name="Demand Heat", line=dict(color="black", dash="dash", width=2.5)), row=3, col=1)

    fig.update_layout(height=800, title_text=title, template="plotly_white", hovermode="x unified")
    return fig


def plot_market_prices_interactive(
    results: Dict[str, Any],
    title: str = "Grid & PPA Energy Market Price Dynamics",
    mode: str = "interactive",
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
):
    """
    Generates an interactive Plotly line chart or static Matplotlib plot displaying 
    effective Grid Electricity Import, Grid Export, Gas Import, and PPA Strike Price profiles [EUR/MWh].
    Legends explicitly cite the underlying column source from market_data_2025.csv.
    """
    n = results["network"]
    config = results.get("config", None)

    # 1. Determine snapshot window
    if mode.lower() == "static" or not HAS_PLOTLY:
        snapshots = _slice_snapshots_by_window(n, start_time=start_time, duration_days=duration_days, config=config)
    else:
        snapshots = n.snapshots
        if start_time is not None:
            warnings.warn(
                "The 'start_time' and date-window slicing parameters are active for static viewing mode (mode='static'). "
                "Rendering full interactive Plotly timeline. Set mode='static' to render sliced 1-week view.",
                UserWarning,
                stacklevel=2,
            )

    # 2. Extract Grid Electricity Import Price Series & Column Citation
    elec_import_series = None
    is_sec19 = not results.get("sec19_violation", False)
    elec_import_col = "elec_total_sec19_eur_mwh" if is_sec19 else "elec_total_standard_eur_mwh"
    if hasattr(n, "generators_t") and hasattr(n.generators_t, "marginal_cost") and "grid_electricity" in n.generators_t.marginal_cost.columns:
        elec_import_series = n.generators_t.marginal_cost.loc[snapshots, "grid_electricity"] * 1000.0
    elif "grid_electricity" in n.generators.index:
        mc = float(n.generators.loc["grid_electricity", "marginal_cost"]) * 1000.0
        elec_import_series = pd.Series(mc, index=snapshots)

    # 3. Extract Grid Electricity Export Price Series & Column Citation
    export_series = None
    export_col = "elec_spot_eur_mwh"
    if hasattr(n, "generators_t") and hasattr(n.generators_t, "marginal_cost") and "grid_export" in n.generators_t.marginal_cost.columns:
        export_series = n.generators_t.marginal_cost.loc[snapshots, "grid_export"] * 1000.0
    elif "grid_export" in n.generators.index:
        mc = float(n.generators.loc["grid_export", "marginal_cost"]) * 1000.0
        export_series = pd.Series(mc, index=snapshots)

    # 4. Extract Gas Import Price Series & Column Citation
    gas_series = None
    gas_col = "gas_total_eur_mwh"
    if hasattr(n, "generators_t") and hasattr(n.generators_t, "marginal_cost") and "grid_gas" in n.generators_t.marginal_cost.columns:
        gas_series = n.generators_t.marginal_cost.loc[snapshots, "grid_gas"] * 1000.0
    elif "grid_gas" in n.generators.index:
        mc = float(n.generators.loc["grid_gas", "marginal_cost"]) * 1000.0
        gas_series = pd.Series(mc, index=snapshots)

    # 5. Extract PPA Strike Prices
    pv_ppa_strike = None
    if "pv_ppa" in n.generators.index:
        mc_kwh = float(n.generators.loc["pv_ppa", "marginal_cost"])
        pv_ppa_strike = mc_kwh * 1000.0

    wind_ppa_strike = None
    if "wind_ppa" in n.generators.index:
        mc_kwh = float(n.generators.loc["wind_ppa", "marginal_cost"])
        wind_ppa_strike = mc_kwh * 1000.0

    # Render static Matplotlib plot
    if mode.lower() == "static" or not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(12, 6))
        if elec_import_series is not None:
            mean_imp = elec_import_series.mean()
            ax.plot(snapshots, elec_import_series, label=f"Grid Import [{elec_import_col}] (Mean: €{mean_imp:.2f}/MWh)", color="#3182bd", linewidth=1.8)
        if export_series is not None:
            mean_exp = export_series.mean()
            ax.plot(snapshots, export_series, label=f"Grid Export [{export_col}] (Mean: €{mean_exp:.2f}/MWh)", color="#17becf", linewidth=1.5, linestyle=":")
        if gas_series is not None:
            mean_gas = gas_series.mean()
            ax.plot(snapshots, gas_series, label=f"Natural Gas Import [{gas_col}] (Mean: €{mean_gas:.2f}/MWh)", color="#e6550d", linewidth=1.8)
        if pv_ppa_strike is not None:
            ax.axhline(pv_ppa_strike, color="#ffbb78", linestyle="--", linewidth=2.0, label=f"PV PPA Strike [pv_ppa] (Fixed: €{pv_ppa_strike:.2f}/MWh)")
        if wind_ppa_strike is not None:
            ax.axhline(wind_ppa_strike, color="#98df8a", linestyle="--", linewidth=2.0, label=f"Wind PPA Strike [wind_ppa] (Fixed: €{wind_ppa_strike:.2f}/MWh)")

        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylabel("Price [EUR/MWh]", fontsize=10, fontweight="bold")
        ax.set_xlabel("Timestamp", fontsize=10, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(bbox_to_anchor=(1.02, 1.0), loc="upper left", frameon=True, fontsize=9)
        plt.tight_layout()
        return fig

    # Render interactive Plotly chart
    fig = go.Figure()
    if elec_import_series is not None:
        mean_imp = elec_import_series.mean()
        fig.add_trace(go.Scatter(x=snapshots, y=elec_import_series, name=f"Grid Import [{elec_import_col}] (Mean: €{mean_imp:.2f}/MWh)", line=dict(color="#3182bd", width=2)))
    if export_series is not None:
        mean_exp = export_series.mean()
        fig.add_trace(go.Scatter(x=snapshots, y=export_series, name=f"Grid Export [{export_col}] (Mean: €{mean_exp:.2f}/MWh)", line=dict(color="#17becf", width=2, dash="dot")))
    if gas_series is not None:
        mean_gas = gas_series.mean()
        fig.add_trace(go.Scatter(x=snapshots, y=gas_series, name=f"Natural Gas Import [{gas_col}] (Mean: €{mean_gas:.2f}/MWh)", line=dict(color="#e6550d", width=2)))
    if pv_ppa_strike is not None:
        fig.add_trace(go.Scatter(x=[snapshots[0], snapshots[-1]], y=[pv_ppa_strike, pv_ppa_strike], name=f"PV PPA Strike [pv_ppa] (Fixed: €{pv_ppa_strike:.2f}/MWh)", line=dict(color="#ffbb78", width=2.5, dash="dash")))
    if wind_ppa_strike is not None:
        fig.add_trace(go.Scatter(x=[snapshots[0], snapshots[-1]], y=[wind_ppa_strike, wind_ppa_strike], name=f"Wind PPA Strike [wind_ppa] (Fixed: €{wind_ppa_strike:.2f}/MWh)", line=dict(color="#98df8a", width=2.5, dash="dash")))


    fig.update_layout(
        title=title,
        xaxis_title="Timestamp",
        yaxis_title="Market / Contract Price [EUR / MWh]",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="v", yanchor="top", y=0.99, xanchor="left", x=1.02)
    )
    return fig



# Explicit static aliases and backward-compatibility aliases
plot_dispatch_stacks_static = plot_dispatch_stacks

def plot_market_prices_static(
    results: Dict[str, Any],
    title: str = "Grid Spot Market Price Dynamics",
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
) -> plt.Figure:
    """Generates static 1-week Matplotlib line chart for spot market prices."""
    return plot_market_prices_interactive(
        results=results,
        title=title,
        mode="static",
        start_time=start_time,
        duration_days=duration_days,
    )

plot_market_prices = plot_market_prices_interactive
plot_dispatch_with_market_prices_interactive = plot_market_prices_interactive



def plot_storage_dynamics_interactive(
    results: Dict[str, Any],
    title: str = "BESS & TES State-of-Charge (SOC) Dynamics",
    mode: str = "interactive",
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
):
    """Generates interactive SOC plot for Battery and Thermal Energy Storage."""
    n = results["network"]
    config = results.get("config", None)
    
    if mode.lower() == "static" or not HAS_PLOTLY:
        snapshots = _slice_snapshots_by_window(n, start_time=start_time, duration_days=duration_days, config=config)
    else:
        snapshots = n.snapshots

    bess_soc = n.stores_t.e.loc[snapshots, "bess"] if hasattr(n, "stores_t") and hasattr(n.stores_t, "e") and "bess" in n.stores_t.e.columns else None
    tes_soc = n.stores_t.e.loc[snapshots, "tes"] if hasattr(n, "stores_t") and hasattr(n.stores_t, "e") and "tes" in n.stores_t.e.columns else None

    if mode.lower() == "static" or not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(12, 5))
        if bess_soc is not None:
            ax.plot(snapshots, bess_soc, label="BESS SOC [kWh]", color="#3182bd", linewidth=2)
        if tes_soc is not None:
            ax.plot(snapshots, tes_soc, label="TES SOC [kWh_th]", color="#2ca02c", linewidth=2)
        ax.set_title(title)
        ax.set_ylabel("Energy Stored [kWh]")
        ax.grid(True, linestyle="--")
        ax.legend()
        plt.tight_layout()
        return fig

    fig = go.Figure()
    if bess_soc is not None:
        fig.add_trace(go.Scatter(x=snapshots, y=bess_soc, name="BESS SOC [kWh]", line=dict(color="#3182bd", width=2.5)))
    if tes_soc is not None:
        fig.add_trace(go.Scatter(x=snapshots, y=tes_soc, name="TES SOC [kWh_th]", line=dict(color="#2ca02c", width=2.5)))

    fig.update_layout(title=title, xaxis_title="Timestamp", yaxis_title="State of Charge [kWh]", template="plotly_white")
    return fig


def plot_price_duration_curves_interactive(
    results: Dict[str, Any],
    title: str = "Electricity Spot & Marginal Bus Price Duration Curve",
    mode: str = "interactive",
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
):
    """Plots marginal price duration curves for market spot price and solved bus shadow price [EUR/MWh]."""
    n = results["network"]
    config = results.get("config", None)

    if mode.lower() == "static" or not HAS_PLOTLY:
        snapshots = _slice_snapshots_by_window(n, start_time=start_time, duration_days=duration_days, config=config)
    else:
        snapshots = n.snapshots

    grid_mc = n.generators_t.marginal_cost["grid_electricity"] if "grid_electricity" in n.generators_t.marginal_cost.columns else n.generators.loc["grid_electricity", "marginal_cost"]
    price_series = pd.Series(grid_mc, index=snapshots) * 1000.0  # EUR/MWh
    sorted_prices = price_series.sort_values(ascending=False).values
    hours = np.arange(1, len(sorted_prices) + 1)

    bus_mp_series = None
    if hasattr(n, "buses_t") and hasattr(n.buses_t, "marginal_price") and "b_elec" in n.buses_t.marginal_price.columns:
        bus_mp = n.buses_t.marginal_price.loc[snapshots, "b_elec"] * 1000.0  # EUR/MWh
        bus_mp_series = bus_mp.sort_values(ascending=False).values

    if mode.lower() == "static" or not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(hours, sorted_prices, color="#3182bd", linewidth=2, label="Grid Spot Price [EUR/MWh]")
        if bus_mp_series is not None:
            ax.plot(hours, bus_mp_series, color="#d62728", linewidth=2, linestyle="--", label="Electricity Bus LMP (Shadow Price) [EUR/MWh]")
        ax.set_title(title)
        ax.set_xlabel("Hours")
        ax.set_ylabel("Price [EUR/MWh]")
        ax.grid(True, linestyle="--")
        ax.legend()
        plt.tight_layout()
        return fig

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=sorted_prices, name="Grid Spot Price", line=dict(color="#3182bd", width=2.5)))
    if bus_mp_series is not None:
        fig.add_trace(go.Scatter(x=hours, y=bus_mp_series, name="Elec Bus LMP (Shadow Price)", line=dict(color="#d62728", width=2.5, dash="dash")))
    fig.update_layout(title=title, xaxis_title="Hours", yaxis_title="Price [EUR/MWh]", template="plotly_white")
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


def plot_sec19_grid_fee_protection_interactive(
    results: Dict[str, Any],
    threshold_kw: float = 60000.0,
    title: str = "Sec19 StromNEV Peak Grid Demand Profile",
    mode: str = "interactive",
    start_time: Optional[str] = None,
    duration_days: float = 7.0,
):
    """Plots hourly grid electricity import profile against 60 MW continuous baseload threshold."""
    n = results["network"]
    config = results.get("config", None)

    if mode.lower() == "static" or not HAS_PLOTLY:
        snapshots = _slice_snapshots_by_window(n, start_time=start_time, duration_days=duration_days, config=config)
    else:
        snapshots = n.snapshots

    grid_p = n.generators_t.p.loc[snapshots, "grid_electricity"] if "grid_electricity" in n.generators_t.p.columns else pd.Series(0.0, index=snapshots)

    if mode.lower() == "static" or not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(snapshots, grid_p, label="Grid Elec Import [kW]", color="#3182bd", linewidth=1.5)
        ax.axhline(threshold_kw, color="red", linestyle="--", linewidth=2, label=f"Sec19 Threshold ({threshold_kw/1000:.0f} MW)")
        ax.set_title(title)
        ax.set_ylabel("Grid Power [kW]")
        ax.grid(True, linestyle="--")
        ax.legend()
        plt.tight_layout()
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
            if gen in ["grid_electricity", "grid_gas", "grid_export"] or gen.endswith("_dump"):
                continue
            p_actual = float(n.generators_t.p[gen].sum()) if gen in n.generators_t.p.columns else 0.0
            
            # Handle potential NaN in p_nom_opt safely
            val = n.generators.loc[gen, "p_nom_opt"] if "p_nom_opt" in n.generators.columns else n.generators.loc[gen, "p_nom"]
            p_opt = float(val) if not pd.isna(val) else float(n.generators.loc[gen, "p_nom"])

            if hasattr(n.generators_t, "p_max_pu") and gen in n.generators_t.p_max_pu.columns:
                p_potential = float((n.generators_t.p_max_pu[gen] * p_opt).sum())
            else:
                p_potential = p_actual

            tot_elec_generated += p_potential
            curt = max(0.0, p_potential - p_actual)
            tot_elec_curtailed += curt

        if "grid_electricity" in n.generators_t.p.columns:
            tot_elec_generated += float(n.generators_t.p["grid_electricity"].sum())

    if hasattr(n, "links_t") and hasattr(n.links_t, "p1") and "gas_chp" in n.links.index:
        if "gas_chp" in n.links_t.p1.columns:
            tot_elec_generated += float(np.abs(n.links_t.p1["gas_chp"]).sum())

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

    if hasattr(n, "links_t"):
        if "gas_chp" in n.links.index and hasattr(n.links_t, "p2") and "gas_chp" in n.links_t.p2.columns:
            tot_heat_generated += float(np.abs(n.links_t.p2["gas_chp"]).sum())

        if "gas_boiler" in n.links.index and hasattr(n.links_t, "p1") and "gas_boiler" in n.links_t.p1.columns:
            tot_heat_generated += float(np.abs(n.links_t.p1["gas_boiler"]).sum())

        if "electric_boiler" in n.links.index and hasattr(n.links_t, "p1") and "electric_boiler" in n.links_t.p1.columns:
            tot_heat_generated += float(np.abs(n.links_t.p1["electric_boiler"]).sum())

        if "heat_pump" in n.links.index and hasattr(n.links_t, "p1") and "heat_pump" in n.links_t.p1.columns:
            tot_heat_generated += float(np.abs(n.links_t.p1["heat_pump"]).sum())

    tot_heat_potential = tot_heat_generated + tot_heat_curtailed
    heat_curtailment_pct = (tot_heat_curtailed / tot_heat_potential * 100.0) if tot_heat_potential > 0 else 0.0

    return round(elec_curtailment_pct, 2), round(heat_curtailment_pct, 2)


def calculate_renewable_and_export_metrics(res: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculates detailed renewable energy and grid export metrics:
    - Grid Export Volume (MWh)
    - Grid Export Revenue (EUR)
    - Renewable Self-Consumption Rate (%)
    - Renewable Autarky / Green Coverage Rate (%)
    - Onsite PV Inverter Curtailment Rate (%)
    """
    if not isinstance(res, dict) or "network" not in res:
        return {
            "grid_export_mwh": 0.0,
            "grid_export_revenue_eur": 0.0,
            "self_consumption_pct": 0.0,
            "autarky_pct": 0.0,
            "onsite_pv_curtailment_pct": 0.0,
        }

    n = res["network"]
    grid_export_mwh = float(res.get("grid_export_mwh", 0.0))
    grid_export_revenue_eur = float(res.get("grid_export_revenue_eur", 0.0))

    # Calculate total potential renewable generation (Onsite PV + PV PPA + Wind PPA)
    tot_renewable_potential_kwh = 0.0
    tot_renewable_consumed_kwh = 0.0
    onsite_pv_potential_kwh = 0.0
    onsite_pv_curtailed_kwh = 0.0

    if hasattr(n, "generators_t") and hasattr(n.generators_t, "p"):
        for gen in ["solar_pv", "pv_ppa", "wind_ppa"]:
            if gen in n.generators.index:
                val = n.generators.loc[gen, "p_nom_opt"] if "p_nom_opt" in n.generators.columns else n.generators.loc[gen, "p_nom"]
                p_opt = float(val) if not pd.isna(val) else float(n.generators.loc[gen, "p_nom"])
                p_act = float(n.generators_t.p[gen].sum()) if gen in n.generators_t.p.columns else 0.0

                if hasattr(n.generators_t, "p_max_pu") and gen in n.generators_t.p_max_pu.columns:
                    p_pot = float((n.generators_t.p_max_pu[gen] * p_opt).sum())
                else:
                    p_pot = p_act

                tot_renewable_potential_kwh += p_pot

                if gen == "solar_pv":
                    onsite_pv_potential_kwh += p_pot
                    curt = max(0.0, p_pot - p_act)
                    onsite_pv_curtailed_kwh += curt

    # Total grid export in kWh
    export_kwh = grid_export_mwh * 1000.0

    # Self-consumed green energy = Total Renewable Potential - Grid Export - Onsite PV Curtailment
    tot_renewable_consumed_kwh = max(0.0, tot_renewable_potential_kwh - export_kwh - onsite_pv_curtailed_kwh)

    self_consumption_pct = (tot_renewable_consumed_kwh / tot_renewable_potential_kwh * 100.0) if tot_renewable_potential_kwh > 0 else 0.0
    onsite_pv_curtailment_pct = (onsite_pv_curtailed_kwh / onsite_pv_potential_kwh * 100.0) if onsite_pv_potential_kwh > 0 else 0.0

    # Total site electricity demand in kWh (60 MW continuous over snapshots)
    num_snapshots = len(n.snapshots) if hasattr(n, "snapshots") else 8760
    annual_weight = float(n.snapshot_weightings.objective.iloc[0]) if hasattr(n, "snapshot_weightings") and hasattr(n.snapshot_weightings, "objective") and hasattr(n.snapshot_weightings.objective, "iloc") else 1.0
    tot_site_demand_kwh = 60000.0 * num_snapshots * annual_weight
    autarky_pct = (tot_renewable_consumed_kwh / tot_site_demand_kwh * 100.0) if tot_site_demand_kwh > 0 else 0.0

    return {
        "grid_export_mwh": round(grid_export_mwh, 2),
        "grid_export_revenue_eur": round(grid_export_revenue_eur, 2),
        "self_consumption_pct": round(self_consumption_pct, 2),
        "autarky_pct": round(autarky_pct, 2),
        "onsite_pv_curtailment_pct": round(onsite_pv_curtailment_pct, 2),
    }


def calculate_simultaneity_metrics(res: Any, threshold_kw: float = 1.0) -> Dict[str, Any]:
    """
    Calculates simultaneous charging/discharging and grid import/export occurrence across all snapshots.
    
    Returns
    -------
    Dict[str, Any]
        Dictionary containing BESS, TES, Grid, and total simultaneous hours, percentage, and formatted status string.
    """
    empty_res = {
        "bess_simultaneous_hrs": 0,
        "tes_simultaneous_hrs": 0,
        "grid_simultaneous_hrs": 0,
        "total_simultaneous_hrs": 0,
        "simultaneity_pct": 0.0,
        "simultaneity_status": "0 hrs (0.0%)",
        "has_simultaneity": False,
    }

    if isinstance(res, dict):
        n = res.get("network", None)
    elif hasattr(res, "links_t"):
        n = res
    else:
        n = None

    if n is None or not hasattr(n, "snapshots"):
        return empty_res

    num_snapshots = len(n.snapshots) if hasattr(n, "snapshots") else 1
    if num_snapshots == 0:
        return empty_res

    # 1. BESS Simultaneity Check
    bess_sim_mask = pd.Series(False, index=n.snapshots)
    if hasattr(n, "links_t") and hasattr(n.links_t, "p"):
        if "bess_charger" in n.links_t.p.columns and "bess_discharger" in n.links_t.p.columns:
            p_ch = n.links_t.p["bess_charger"]
            p_dis = n.links_t.p["bess_discharger"]
            bess_sim_mask = (p_ch > threshold_kw) & (p_dis > threshold_kw)

    # 2. TES Simultaneity Check
    tes_sim_mask = pd.Series(False, index=n.snapshots)
    if hasattr(n, "links_t") and hasattr(n.links_t, "p"):
        if "tes_charger" in n.links_t.p.columns and "tes_discharger" in n.links_t.p.columns:
            p_ch = n.links_t.p["tes_charger"]
            p_dis = n.links_t.p["tes_discharger"]
            tes_sim_mask = (p_ch > threshold_kw) & (p_dis > threshold_kw)

    # 3. Grid Import/Export Simultaneity Check
    grid_sim_mask = pd.Series(False, index=n.snapshots)
    if hasattr(n, "generators_t") and hasattr(n.generators_t, "p"):
        if "grid_electricity" in n.generators_t.p.columns and "grid_export" in n.generators_t.p.columns:
            p_imp = n.generators_t.p["grid_electricity"]
            p_exp = n.generators_t.p["grid_export"].abs()
            grid_sim_mask = (p_imp > threshold_kw) & (p_exp > threshold_kw)

    # Combined Simultaneity
    any_sim_mask = bess_sim_mask | tes_sim_mask | grid_sim_mask
    tot_sim_hrs = int(any_sim_mask.sum())
    sim_pct = round((tot_sim_hrs / num_snapshots) * 100.0, 2) if num_snapshots > 0 else 0.0

    status_str = f"{tot_sim_hrs} hrs ({sim_pct}%)" if tot_sim_hrs > 0 else "0 hrs (0.0%)"

    return {
        "bess_simultaneous_hrs": int(bess_sim_mask.sum()),
        "tes_simultaneous_hrs": int(tes_sim_mask.sum()),
        "grid_simultaneous_hrs": int(grid_sim_mask.sum()),
        "total_simultaneous_hrs": tot_sim_hrs,
        "simultaneity_pct": sim_pct,
        "simultaneity_status": status_str,
        "has_simultaneity": tot_sim_hrs > 0,
    }


def create_summary_dataframe(results_dict: Dict[str, Dict[str, Any]], annual_tonnage: float = 450000.0) -> pd.DataFrame:
    """Compiles scenario results into a clean financial comparison table (EUR/ton, OPEX, CAPEX, CO2, Export, Curtailment, Simultaneity)."""
    rows = []
    for scenario_name, res in results_dict.items():
        tot_cost = res["total_cost_eur"]
        eff_tonnage = get_period_effective_tonnage(res, annual_tonnage=annual_tonnage)
        cost_per_ton = tot_cost / eff_tonnage if eff_tonnage > 0 else 0.0
        elec_curt_pct, heat_curt_pct = calculate_curtailment_metrics(res)
        ren_metrics = calculate_renewable_and_export_metrics(res)
        sim_metrics = calculate_simultaneity_metrics(res)

        rows.append({
            "Scenario": scenario_name,
            "Total Cost (EUR)": tot_cost,
            "Cost per Ton (EUR/ton)": cost_per_ton,
            "OPEX (EUR)": res["opex_eur"],
            "Annualized CAPEX (EUR)": res["capex_annualized_eur"],
            "Emissions (tCO2)": res["emissions_t_co2"],
            "Peak Grid Demand (MW)": res["peak_grid_demand_kw"] / 1000.0,
            "Grid Export (MWh)": ren_metrics["grid_export_mwh"],
            "Grid Export Rev (EUR)": ren_metrics["grid_export_revenue_eur"],
            "Self-Consumption (%)": ren_metrics["self_consumption_pct"],
            "Autarky (%)": ren_metrics["autarky_pct"],
            "Curtailed Elec (%)": elec_curt_pct,
            "Curtailed Heat (%)": heat_curt_pct,
            "Simultaneous Ops": sim_metrics["simultaneity_status"],
            "Sec19 Compliant": not res["sec19_violation"],
        })

    df_summary = pd.DataFrame(rows).set_index("Scenario")
    return df_summary


def plot_scenario_cost_per_ton_interactive(
    scenarios: Dict[str, Any],
    annual_tonnage: float = 450000.0,
    title: str = "Unit Production Cost Comparison (€/ton)",
    mode: str = "static",
):
    """
    Generates a modular bar chart comparing EUR/ton across arbitrary scenarios (2, 3, or N scenarios).
    Automatically scales production tonnage to match the period duration of each solved scenario.
    Defaults to static Matplotlib output for direct online GitHub notebook rendering.
    
    Parameters
    ----------
    scenarios : Dict[str, Any]
        Mapping of Scenario Name -> (PyPSA results dict OR numeric float/int EUR/ton value).
        Examples:
            # 2 Scenarios:
            plot_scenario_cost_per_ton({"Baseline": 145.20, "Operation Hub": meta_op})
            
            # 3 Scenarios:
            plot_scenario_cost_per_ton({"Baseline": 145.20, "Operation Hub": meta_op, "Decision Hub": meta_inv})
    annual_tonnage : float
        Annual production output in tons (default 450,000 tons/year).
    title : str
        Chart title.
    mode : str
        'static' (Matplotlib, default) or 'interactive' (Plotly).
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

    if mode.lower() == "static" or not HAS_PLOTLY:
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(labels, values, color=bar_colors, width=0.55, edgecolor="black", linewidth=0.8)
        ax.set_ylabel("Unit Cost [EUR / ton]", fontsize=11, fontweight="bold")
        ax.set_xlabel("Scenario Tiers", fontsize=11, fontweight="bold")
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        ax.grid(True, linestyle="--", alpha=0.5, axis="y")

        max_v = max(values) if values else 1.0
        ax.set_ylim(0, max_v * 1.18)

        for bar, v in zip(bars, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + (max_v * 0.02),
                f"€{v:.2f} / t",
                ha="center",
                va="bottom",
                fontweight="bold",
                fontsize=10,
            )

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


# Aliases for plot_scenario_cost_per_ton
plot_scenario_cost_per_ton = plot_scenario_cost_per_ton_interactive
plot_scenario_cost_per_ton_static = plot_scenario_cost_per_ton_interactive


def create_pypsa_asset_sizing_table(results_or_net: Any) -> pd.DataFrame:
    """Extracts optimal asset capacities from a solved PyPSA network or results dict."""
    n = results_or_net.get("network", results_or_net) if isinstance(results_or_net, dict) else getattr(results_or_net, "network", results_or_net)

    asset_rows = []
    if hasattr(n, "generators") and not n.generators.empty:
        for name, row in n.generators.iterrows():
            val = row.get("p_nom_opt", np.nan)
            if pd.isna(val) or val is None:
                val = row.get("p_nom", 0.0)
            p_opt = float(val) if not pd.isna(val) else 0.0
            
            # Exclude grid imports and emergency dump generators
            if p_opt > 0 and name not in ["grid_electricity", "grid_gas"] and not name.endswith("_dump"):
                unit = "kWp" if "pv" in name.lower() else "kW"
                asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{p_opt:,.2f}", "Unit": unit})

    if hasattr(n, "links") and not n.links.empty:
        for name, row in n.links.iterrows():
            val = row.get("p_nom_opt", np.nan)
            if pd.isna(val) or val is None:
                val = row.get("p_nom", 0.0)
            p_opt = float(val) if not pd.isna(val) else 0.0
            
            if p_opt > 0 and name != "steam_to_heat_exchanger":
                # Convert raw input link capacity to output rating
                if name == "gas_chp":
                    eta_el = float(row.get("efficiency", 0.40))
                    cap_el = p_opt * eta_el
                    asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{cap_el:,.2f}", "Unit": "kW_el"})
                elif name == "heat_pump":
                    cop = float(row.get("efficiency", 2.8))
                    cap_th = p_opt * cop
                    asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{cap_th:,.2f}", "Unit": "kW_th"})
                elif name in ["gas_boiler", "electric_boiler"]:
                    eff = float(row.get("efficiency", 0.90))
                    cap_th = p_opt * eff
                    asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{cap_th:,.2f}", "Unit": "kW_th"})
                else:
                    unit = "kW" if "bess" in name.lower() else "kW_th"
                    asset_rows.append({"Asset Component": name.upper(), "Optimal Sizing Capacity": f"{p_opt:,.2f}", "Unit": unit})

    if hasattr(n, "stores") and not n.stores.empty:
        for name, row in n.stores.iterrows():
            val = row.get("e_nom_opt", np.nan)
            if pd.isna(val) or val is None:
                val = row.get("e_nom", 0.0)
            e_opt = float(val) if not pd.isna(val) else 0.0
            
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
            has_ext = "p_nom_extendable" in n_disp.generators.columns
            mask = (n_disp.generators["p_nom_extendable"]) if has_ext else pd.Series(False, index=n_disp.generators.index)
            unbuilt_gens = n_disp.generators[mask & (n_disp.generators.p_nom_opt <= 1e-3)].index
            for g in list(unbuilt_gens):
                n_disp.remove("Generator", g)

        # Remove extendable links with zero capacity built
        if hasattr(n_disp, "links") and "p_nom_opt" in n_disp.links.columns:
            has_ext = "p_nom_extendable" in n_disp.links.columns
            mask = (n_disp.links["p_nom_extendable"]) if has_ext else pd.Series(False, index=n_disp.links.index)
            unbuilt_links = n_disp.links[mask & (n_disp.links.p_nom_opt <= 1e-3)].index
            for l in list(unbuilt_links):
                n_disp.remove("Link", l)

        # Remove extendable stores with zero capacity built
        if hasattr(n_disp, "stores") and "e_nom_opt" in n_disp.stores.columns:
            has_ext = "e_nom_extendable" in n_disp.stores.columns
            mask = (n_disp.stores["e_nom_extendable"]) if has_ext else pd.Series(False, index=n_disp.stores.index)
            unbuilt_stores = n_disp.stores[mask & (n_disp.stores.e_nom_opt <= 1e-3)].index
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
        "grid_gas": {"pos": (1, 8.8), "color": "#6baed6", "label": "Grid Gas\n(Import)"},
        "grid_electricity": {"pos": (1, 6.8), "color": "#3182bd", "label": "Grid Power\n(Import)"},
        "grid_export": {"pos": (1, 5.2), "color": "#17becf", "label": "Grid Export\n(Wholesale Spot)"},
        "pv_ppa": {"pos": (1, 3.8), "color": "#ffbb78", "type": "generators", "prefix": "Solar PPA", "unit": "MW"},
        "solar_pv": {"pos": (1, 2.2), "color": "#fec44f", "type": "generators", "prefix": "Rooftop PV", "unit": "MWp"},
        "wind_ppa": {"pos": (1, 0.6), "color": "#98df8a", "type": "generators", "prefix": "Wind PPA", "unit": "MW"},

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
        "steam_to_heat_exchanger": {"pos": (7, 4.5), "color": "#98df8a", "type": "links", "label": "Steam Exchanger\n(98% Eff)"},

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
        elif name in ["grid_gas", "grid_electricity", "grid_export", "demand_elec", "demand_steam", "demand_heat"]:
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
                elif name == "heat_pump":
                    cop = float(row.get("efficiency", 2.8))
                    hp_th = cap * cop
                    info["label"] = f"HTHP Heat Pump\n({hp_th/1000:.2f} MW_th)"
                elif name == "electric_boiler":
                    eff = float(row.get("efficiency", 0.99))
                    eb_th = cap * eff
                    info["label"] = f"Electric Boiler\n({eb_th/1000:.2f} MW_th)"
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
        ("b_elec", "grid_export"),
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

