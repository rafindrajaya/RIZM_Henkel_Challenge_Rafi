# Progress Update: Investment Hub PPA Schematic Rendering & Asset Sizing Table Sanitization

## Summary of Changes
1. **Added PV PPA and Wind PPA to `plot_network_schematic`**:
   - Updated `nodes` layout template in `src/utils.py` to include `pv_ppa` (Solar PPA) and `wind_ppa` (Wind PPA) generator entries with designated plot positions, distinct colors, and dynamic MW capacity labeling.
   - Added flow connections `("pv_ppa", "b_elec")` and `("wind_ppa", "b_elec")` so active PPA contracts are properly visualized on the Investment Hub block diagram.

2. **Filtered Dummy Dump Generators from `create_pypsa_asset_sizing_table`**:
   - Modified `create_pypsa_asset_sizing_table` in `src/utils.py` to exclude emergency zero-cost heat dump generators (`steam_dump`, `heat_dump`) and grid import placeholders (`grid_electricity`, `grid_gas`) from the asset sizing summary table.
   - Prevented 1,000,000 kW dummy dump bounds from incorrectly showing up as installed asset capacities.

3. **Business Case Defense & Curtailed Energy Analytics**:
   - Provided business defense analysis regarding why PPA candidate capacities max out in linear programming optimization and how to establish defensible PPA upper bounds (`max_capacity`) considering volumetric risk and take-or-pay liabilities.
   - Formulated integrated curtailment metrics for electricity and thermal energy.

## Verification
- Module imports and utility functions verified.
