# Progress Update -- Phase 6: Selective Component/Bus Building, Automatic Timesteps, Full Dual Asset Sizing & oemof_visio Balance Plotting

> **Status:** COMPLETED
> **Date:** August 6, 2026

---

## 1. Summary of Accomplishments

### 1.1 Selective Active Component & Bus Building (`src/optimization_model.py`)
- Refactored `HenkelEnergySystem.build_energy_system()` to build ONLY components configured with `fixed_components_sizing` capacity > 0 or `variable_components_sizing` enabled in investment mode.
- Dynamically identifies connected buses (`b_elec`, `b_gas`, `b_steam_ht`, `b_heat_lt`) from active components and grid sources, only registering attached active buses into the `solph.EnergySystem`.

### 1.2 Full Dual Asset Sizing Consistency (All 7 Asset Types)
- Standardized fixed baseline capacity + candidate investment expansion across ALL components:
  - **Sources/Renewables**: `solar_pv_fixed` & `solar_pv_expansion`
  - **Storage**: `bess_fixed` & `bess_expansion`, `tes_fixed` & `tes_expansion`
  - **Converters**: `heat_pump_fixed` & `heat_pump_expansion`, `gas_chp_fixed` & `gas_chp_expansion`, `gas_boiler_fixed` & `gas_boiler_expansion`, `electric_boiler_fixed` & `electric_boiler_expansion`
- Fixed baseline capacities operate at zero investment cost while candidate expansion capacities optimize investment bounds (`solph.Investment`) when enabled in investment mode.

### 1.3 Automatic Timestep Derivation
- Removed legacy integer `timesteps` parameter overrides from `build_energy_system()` and `solve()`.
- Timesteps are calculated strictly from the date range bounds (`start_time` to `end_time`) in `FacilityProjectConfig`.

### 1.4 `oemof_visio` I/O Balance Plotting (`src/utils.py`)
- Updated `plot_energy_system_graph()` in `src/utils.py` to extract bus results using `solph.views.node()` and draw input/output flow balance plots using `oemof_visio.Plot` (with graceful Matplotlib fallback).

---

## 2. Modified Files

- [src/optimization_model.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/optimization_model.py): Dynamic active component and bus filtering, 7-asset fixed + expansion dual asset sizing, automatic timestep derivation, Pyomo import.
- [src/utils.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py): Replaced networkx graph visualizer with `oemof_visio` bus I/O balance plotting routine.
- [docs/progress_phase6.md](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/docs/progress_phase6.md): Progress documentation for Phase 6 changes.

---

## 3. Repository State

- All 7 asset types now strictly adhere to uniform fixed existing capacity + candidate expansion investment modeling logic.
- `HenkelEnergySystem` graph building is fully standardized and clean.
