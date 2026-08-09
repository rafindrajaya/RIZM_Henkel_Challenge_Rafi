# Progress Update: Heat Pump & Converter Sizing Mismatch Fix in `plot_network_schematic`

## Overview
Fixed a capacity unit reporting mismatch in `plot_network_schematic` where the High-Temperature Heat Pump (HTHP) was incorrectly displayed as `21.43 MW_th` instead of its true thermal rating `60.00 MW_th`.

## Key Changes
1. **`src/utils.py` ([src/utils.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py#L1139-L1146))**:
   - PyPSA models `Link` capacities relative to `bus0` (electrical input rating $P_{\text{el, opt}} \approx 21.43 \text{ MW}_{\text{el}}$).
   - Added explicit conversion logic in `plot_network_schematic` for `heat_pump` and `electric_boiler`:
     - **HTHP Heat Pump**: Thermal Output Capacity = $P_{\text{el, opt}} \times \text{COP} = 21.43 \text{ MW}_{\text{el}} \times 2.8 = 60.00 \text{ MW}_{\text{th}}$.
     - **Electric Boiler**: Thermal Output Capacity = $P_{\text{el, opt}} \times \eta$.
   - The schematic diagram now correctly aligns with `create_pypsa_asset_sizing_table` showing `60.00 MW_th` for the optimal heat pump capacity.
