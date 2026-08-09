# Progress Update: Static Dispatch Stack Outgoing Streams Integration

## Overview
Updated the static dispatch stack plotting function `plot_dispatch_stacks` (and its wrapper `plot_dispatch_stacks_interactive(..., mode="static")`) in `src/utils.py` to include all negative outgoing electrical streams on the Electricity Bus panel (`b_elec`). This matches the outgoing stream dynamics of the interactive Plotly visualization mode.

## Key Changes
1. **Added Outgoing Electricity Sinks to Panel 1 (`ax0`) in `plot_dispatch_stacks()`**:
   - **HTHP Elec Power (`heat_pump` electrical consumption):** Plotted as `-np.abs(n.links_t.p0["heat_pump"])` with color `#17becf` and dotted line `linestyle=":"`.
   - **E-Boiler Elec Power (`electric_boiler` electrical consumption):** Plotted as `-np.abs(n.links_t.p0["electric_boiler"])` with color `#8c564b` and dotted line `linestyle=":"`.
   - **Solar Curtailed (PV curtailment):** Plotted as `-np.maximum(0.0, p_pot - p_act)` with color `#7f7f7f` and dotted line `linestyle=":"` whenever non-zero.

2. **Parity with Interactive Plotly Mode**:
   - Both `mode="interactive"` (Plotly stacked area) and `mode="static"` (Matplotlib line chart) now display complete 2-way power flow on the electricity bus (positive generation sources vs. negative outgoing sinks/exports and black dashed load demand).

## Rule 8 Compliance
- Zero edits were made to `challenge.ipynb`.
