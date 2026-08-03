# MILP Optimization Engineer Skill

## Modeling Standards (`oemof.solph` & Pyomo)
1. **Energy Flow Graph Definition:**
   - Define explicit buses for Electricity (`b_elec`), Gas (`b_gas`), High-Temp Steam (`b_steam_ht`), and Mid-Temp Process Heat (`b_heat_lt`).
   - Converters (CHP, Gas Boiler, Electric Boiler, Heat Pump) must specify exact input/output efficiency vectors.
2. **Solvers & Performance:**
   - Use `highspy` (HiGHS MILP solver) for high-performance open-source linear and mixed-integer solving.
   - Set solver options (`mip_rel_gap=0.01`, time limits) to guarantee fast convergence under annual 15-minute resolution datasets (35,040 timesteps).
3. **Operational vs Investment Mode:**
   - **Operational Mode:** Fixed asset capacities (`nominal_value`), minimizing hourly variable operational expenditure (OPEX).
   - **Investment Mode:** Variable capacities with Equivalent Annual Cost (`Investment(ep_costs=...)`), co-optimizing CAPEX + OPEX over asset lifetimes.
4. **Feasibility Safeguards:**
   - Add slack sinks/sources with high penalty costs to avoid unhandled solver infeasibility exceptions during parameter exploration.
