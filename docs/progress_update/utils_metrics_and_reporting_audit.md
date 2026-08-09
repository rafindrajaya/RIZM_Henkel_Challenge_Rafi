# Progress Update: Audit & Refactoring of `src/utils.py` Visual Reporting & Financial Metrics

## Summary of Changes

1. **Fixed Asset Sizing Summary Table Extraction (`create_pypsa_asset_sizing_table`)**:
   - Replaced unsafe `getattr(row, "p_nom_opt")` calls with `row.get("p_nom_opt", np.nan)` falling back to `p_nom` when `p_nom_opt` is `NaN`. This fixes a critical bug where non-extendable fixed assets (such as the 180 MW Gas Boiler or 30 MW CHP) were omitted from the asset sizing table.
   - Converted raw fuel input link capacities to true output ratings ($\text{kW}_{\text{el}}$ or $\text{kW}_{\text{th}}$) for CHP (gas input $\rightarrow$ electrical output rating), Gas Boiler (gas input $\rightarrow$ thermal output rating), and HTHP (electrical input $\rightarrow$ thermal output rating via COP).

2. **Refined Curtailment & Thermal Energy Calculations (`calculate_curtailment_metrics`)**:
   - Wrapped link output energy flows (`p1`, `p2`) with `np.abs()` to protect against negative sign conventions across PyPSA link outputs.
   - Added `NaN` safety handling for generator capacity values during potential generation calculations.

3. **Enhanced Interactive & Static Visual Reporting**:
   - Added dashed black load demand profiles (`demand_elec`, `demand_steam`, `demand_heat`) to Plotly interactive multi-carrier dispatch stack figures (`plot_dispatch_stacks_interactive`).
   - Updated `plot_price_duration_curves_interactive` to plot the solved Electricity Bus Locational Marginal Price / Shadow Price (`n.buses_t.marginal_price["b_elec"]` in EUR/MWh) alongside market spot prices per `@[# PyPSA Reporting]` guidelines.
   - Standardized optional interface parameters (`mode`, `start_time`, `duration_days`) across `plot_storage_dynamics_interactive`, `plot_price_duration_curves_interactive`, and `plot_sec19_grid_fee_protection_interactive`.

4. **Sanitized Interactive Network Map Filtering (`explore_network_interactive`)**:
   - Guarded column boolean mask indexing for `p_nom_extendable` and `e_nom_extendable` to prevent `TypeError` when filtering zero-capacity extendable assets with `active_only=True`.

## Verification & Status
- Refactored functions in `src/utils.py` ([utils.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py)) verified.
