# Must-Run PPA & Grid Export Integration Report

> **Date:** August 8, 2026  
> **Status:** Completed  
> **Skills Referenced:** `pypsa-asset-economics`, `pypsa-market-design`, `pypsa-data-pipelines`

---

## 1. Executive Summary

This report documents the architectural upgrade of **Pay-as-Produced PPA Contracts**, the implementation of a **Wholesale Grid Export Interface**, and the refactoring of **Renewable Energy & Curtailment Metrics** within the Henkel Holthausen PyPSA optimization framework.

Prior to this update, PPA generators had an unconstrained lower bound ($p_{\text{min,pu}} = 0.0$), allowing the linear programming solver to curtail contracted PPA power on-site for free without paying for unused potential. The new architecture enforces **Must-Run Pay-as-Produced contracts** ($p_{\text{min,pu}} = p_{\text{max,pu}}$), forcing the model to take 100% of generated PPA power and monetizing surplus electricity via a **Grid Export Generator** at EPEX wholesale spot market prices (`elec_spot_eur_mwh`).

---

## 2. Technical Implementation Summary

### 2.1 Must-Run PPA & Grid Export Abstractions (`src/components/grid.py`)
- **Must-Run Formulation**: Updated `PVPPAComponent` and `WindPPAComponent` to set `p_min_pu = self.pv_profile.values` and `p_min_pu = self.wind_profile.values` respectively across both fixed and extendable capacity modes.
- **`GridExportConfig` & `GridExportComponent`**: Implemented a dedicated grid export generator on `b_elec` with:
  - `p_nom = 1e6` (kW capacity upper bound)
  - `p_min_pu = -1.0` (allows power flow OUT of `b_elec`, $p \le 0$), `p_max_pu = 0.0` (strictly prevents free generation INTO `b_elec`)
  - `marginal_cost = + (spot_price_series / 1000.0)` (€/kWh), ensuring positive spot prices yield export revenue (reducing cost objective) and negative spot prices yield export penalties.
- Exported `GridExportComponent` and `GridExportConfig` in `src/components/__init__.py`.

### 2.2 Core Optimization Model Integration (`src/optimization_model.py`)
- **System Assembly (`build_system`)**: Instantiated `GridExportComponent(spot_price_series=df_m["elec_spot_eur_mwh"])` and bound it to `b_elec`.
- **Financial Post-Processing (`solve`)**:
  - Extracted positive export power flow $P_{\text{export}}(t) = - n.generators\_t.p[\text{"grid\_export"}]$.
  - Computed `grid_export_revenue_eur = sum(p_export * spot_price_mwh / 1000) * annual_weight` and `grid_export_mwh` using `self.df_market.loc[n.snapshots, "elec_spot_eur_mwh"]`.
  - Updated total OPEX calculation: `opex_total = elec_import_cost + gas_cost + pv_ppa_cost + wind_ppa_cost - grid_export_revenue_eur`.
  - Included `grid_export_revenue_eur` and `grid_export_mwh` in the returned results dictionary.

### 2.3 Analytics & 2-Sided Dispatch Refactoring (`src/utils.py`)
- Refactored `plot_dispatch_stacks()` (Matplotlib) and `plot_dispatch_stacks_interactive()` (Plotly) to render a **true 2-sided energy balance stack** for `b_elec`:
  - **Positive Supply Stack ($y \ge 0$)**: `Grid Elec`, `Solar PV`, `PV PPA`, `Wind PPA`, `CHP Elec`, `BESS Discharge`.
  - **Negative Outgoing Sinks Stack ($y \le 0$)**: `Grid Export`, `BESS Charge`, `HTHP Elec Power`, `E-Boiler Elec Power`, `Solar Curtailed`.
- Updated `calculate_curtailment_metrics()` to exclude `grid_export` generator from the energy producer loop.

### 2.4 Integrated Summary Table & Renewable Metrics (`src/utils.py`)
- Implemented `calculate_renewable_and_export_metrics(res)` extracting:
  - `Grid Export (MWh)` & `Grid Export Rev (EUR)`
  - `Self-Consumption (%)` & `Autarky (%)`
- Integrated all metrics directly into `create_summary_dataframe(results_dict)`, allowing callers to display full scenario comparisons via `df_summary = create_summary_dataframe(...)`.

---

## 3. Verification & Code Audit Checklist

- [x] Must-Run PPA generators enforce $p(t) = p_{\text{max,pu}}(t) \times p_{\text{nom}}$.
- [x] Grid Export generator operates on `b_elec` at wholesale spot price (`elec_spot_eur_mwh`).
- [x] Negative spot prices penalize export while positive spot prices earn revenue.
- [x] § 19 StromNEV import peak protection remains uninfluenced by grid exports (separate RLM registers).
- [x] Created verification script `tmp/test_mustrun_ppa_grid_export.py`.
- [x] Rule 8 Compliance: Zero modifications made to `challenge.ipynb` or `challenge_static.ipynb`.
