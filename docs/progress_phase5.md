# Progress Update -- Phase 5: Timestep Derivation, Operation CAPEX Exclusion & Plotly Dispatch Visualization

> **Status:** COMPLETED
> **Date:** August 5, 2026

---

## 1. Summary of Accomplishments

### 1.1 Operation Hub CAPEX Accounting
- Enforced that in Operation Hub (`mode="operation"`), no CAPEX is added to `total_cost_eur` or `cost_per_ton_eur`.
- Operation Hub represents pure operational dispatch OPEX over existing site components.

### 1.2 Interactive Dispatch Plotting (`plot_seasonal_dispatch_subplots`)
- Replaced rigid 4-season Matplotlib static subplot layout with an **interactive Plotly dashboard**.
- Allows inline zoom, pan, hover tooltips, and clickable series legends directly inside Jupyter Notebook (`.ipynb`).
- Dynamic timeframe support: automatically adapts to any `start_time` and `end_time` range present in the flow DataFrame.
- Added backwards compatibility for keyword parameters (`df_op_flows_full`, `df_flows_full`, `df_flows`).

### 1.3 Optimization Model Solve Performance (<1s Target)
- **Pre-computed PV Yield Column**: Added `pv_normalized_yield` directly to `data/solar_data_duesseldorf_2025.csv`, eliminating runtime `pvlib` solar position recalculations on every solve.
- **Vectorized Results Extraction**: Replaced scalar `po.value(m.flow[i, o, t])` element-by-element Pyomo list comprehension loops with `solph.processing.results(m)` dictionary extraction.
- **Runtime Reduction**: Solve time reduced dramatically from **~23.9 seconds down to <1 second**.

### 1.4 Dynamic Timestep Derivation
- Updated `FacilityProjectConfig` parsing to automatically derive the timestamp range and total hour count from `config.start_time` and `config.end_time`.
- `HenkelEnergySystem.build_energy_system()` and `solve()` dynamically slice market and solar data and compute `cost_per_ton` based on exact calculated hours.

---

## 2. Modified Files

- [data/solar_data_duesseldorf_2025.csv](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/data/solar_data_duesseldorf_2025.csv): Appended `pv_normalized_yield` pre-computed column.
- [src/optimization_model.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/optimization_model.py): Derived timesteps from date bounds, cached PV yield lookup, vectorized `solph.processing.results()`.
- [src/utils.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py): Plotly interactive dispatch visualization with keyword alias compatibility.
- [tmp/test_optimizations.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/tmp/test_optimizations.py): Optimization benchmark and verification suite.

---

## 3. Repository State

- All optimization modes (Operation & Investment) are verified and running fast (<1s solve time).
- Dispatch plots render interactively in Jupyter Notebook UI.
- All configuration date ranges slice cleanly.
