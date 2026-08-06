# MILP Optimization Engineer Skill

## Purpose

Ground all energy system optimization code in oemof.solph and Pyomo best practices.
When writing or reviewing model code, consult the references below for correct API usage and modeling patterns.

## Modeling Standards (oemof.solph & Pyomo)

1. **Energy Flow Graph Definition:**
   - Define explicit buses for each energy carrier: Electricity (`b_elec`), Gas (`b_gas`), High-Temp Steam (`b_steam_ht`), and Mid-Temp Process Heat (`b_heat_lt`).
   - Converters (CHP, Gas Boiler, Electric Boiler, Heat Pump) must specify exact input/output efficiency vectors via `conversion_factors`.
   - All capacities and flows use kW (power) and kWh (energy). Market prices arrive in EUR/MWh and must be converted to EUR/kWh at the boundary.
2. **Operational vs Investment Mode:**
   - **Operational Mode:** Fixed asset capacities via `nominal_value` parameter on flows. Minimizes hourly variable operational expenditure (OPEX).
   - **Investment Mode:** Variable capacities via `nominal_value=solph.Investment(ep_costs=...)` on flows and `nominal_storage_capacity=solph.Investment(ep_costs=...)` on GenericStorage. Co-optimizes annualized CAPEX + OPEX.
   - Investment `ep_costs` must be the Equivalent Annual Cost (EAC) divided by 8760 to get a per-hour cost that oemof.solph can sum correctly.
3. **Feasibility Safeguards:**
   - Add slack sinks/sources with high penalty costs (e.g. 10x normal price) to avoid unhandled solver infeasibility exceptions during parameter exploration.
   - Always check `po.value(m.objective)` after solving to verify the solver found an optimal solution.
4. **oemof.solph API Notes (v0.5+ / v0.6+):**
   - `nominal_value` on flows triggers a FutureWarning about `nominal_capacity` -- this is safe to ignore in v0.6.x.
   - `nominal_storage_capacity` on GenericStorage triggers a similar warning -- also safe to ignore.
   - The `investment=` keyword argument on Flow was removed in v0.6. Use `nominal_value=solph.Investment(...)` instead.
   - Similarly for GenericStorage: use `nominal_storage_capacity=solph.Investment(...)` instead of `investment=`.
   - EnergySystem requires `infer_last_interval=False` when timeindex already includes the final boundary timestamp.
5. **tool efficiency**
- Whenever I want to develop a tool or feature, check if there is already an existing oemof.solph tool that does basically the same thing as the tool that I want to make. Suggest me this tool instead of creating a new one. 

## Online References

| Topic | URL | What it provides |
|-------|-----|-----------------|
| oemof.solph Documentation | https://oemof-solph.readthedocs.io/en/latest/ | Official API docs, component reference, examples |
| oemof.solph GitHub | https://github.com/oemof/oemof-solph | Source code, issue tracker, example scripts in `examples/` |
| oemof.solph Investment Example | https://github.com/oemof/oemof-solph/tree/dev/examples | Canonical investment optimization example scripts |
| Pyomo Documentation | https://pyomo.readthedocs.io/en/stable/ | Pyomo modeling language reference |
| HiGHS Solver | https://highs.dev/ | HiGHS LP/MIP solver documentation and options |
| oemof Thermal (Heat Pumps) | https://github.com/oemof/oemof-thermal | Heat pump and solar thermal component extensions for oemof |
