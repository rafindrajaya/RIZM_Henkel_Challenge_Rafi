# Progress Update: PPA Strike Prices, Grid Export, and Column & Mean Price Legend Annotations

## Summary of Changes
1. **Enhanced Market & Contract Price Visualization (`src/utils.py`)**:
   - Updated `plot_market_prices_interactive()` (and `plot_market_prices_static()`) to compute and display the period mean price ($\text{€/MWh}$) alongside the underlying CSV column source tag in the legend labels:
     - `Grid Import [elec_total_sec19_eur_mwh] (Mean: €180.25/MWh)` under §19 protection, or `[elec_total_standard_eur_mwh] (Mean: €230.15/MWh)` under standard tariff.
     - `Grid Export [elec_spot_eur_mwh] (Mean: €75.40/MWh)`.
     - `Natural Gas Import [gas_total_eur_mwh] (Mean: €65.80/MWh)`.
     - `PV PPA Strike [pv_ppa] (Fixed: €55.00/MWh)`.
     - `Wind PPA Strike [wind_ppa] (Fixed: €65.00/MWh)`.

2. **Dual Rendering Compatibility**:
   - Verified that both Plotly (`mode="interactive"`) and Matplotlib (`mode="static"`) render the new mean price annotations cleanly in legends.

## Verification
- Verified function logic and string formatting in `src/utils.py`.
