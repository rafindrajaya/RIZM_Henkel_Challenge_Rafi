# Progress Update: BESS Sizing Table Unit & Energy Schematic Store Nodes Fix

## Summary of Changes
1. **Fixed BESS Link Capacity Unit in `create_pypsa_asset_sizing_table` ([src/utils.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py#L510))**:
   - Replaced hardcoded `kW_th` for PyPSA `Link` components with conditional unit selection: assigns `kW` for electrical battery links (`bess_charger`, `bess_discharger`) and `kW_th` for thermal links.

2. **Fixed BESS and TES Rendering on Energy System Schematic (`plot_network_schematic`) ([src/utils.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py#L695-L810))**:
   - Updated node keys in `nodes` dictionary from `"bess_store"` / `"tes_store"` to `"bess"` / `"tes"` to match PyPSA's store index names.
   - Added automatic alias resolution (`name.replace("_store", "")`) inside `get_component_capacity` so store lookup succeeds regardless of identifier format.
   - Updated flow connections to `("b_elec", "bess")` and `("b_heat_lt", "tes")`.
   - Enhanced dynamic capacity formatting for storage assets (displaying `MWh` / `MWh_th` for capacities >= 1,000 and `kWh` / `kWh_th` for smaller investments).

3. **Notebook Safety Compliance (Rule 8)**:
   - `challenge.ipynb` was not modified.

## Verification
- Verified unit assignment and schematic store node detection.
