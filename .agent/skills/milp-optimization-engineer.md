# MILP Optimization Engineer Skill

## Purpose

Ground all energy system optimization code in oemof.solph and Pyomo best practices.
When writing or reviewing model code, consult the references below for correct API usage and modeling patterns.

## Modeling Standards (oemof.solph & Pyomo)

1. **Energy Flow Graph Definition:**
   - Define explicit buses for each energy carrier: Electricity (`b_elec`), Gas (`b_gas`), High-Temp Steam (`b_steam_ht`), and Mid-Temp Process Heat (`b_heat_lt`).
   - Converters (CHP, Gas Boiler, Electric Boiler, Heat Pump) must specify exact input/output efficiency vectors via `conversion_factors`.
   - All capacities and flows use kW (power) and kWh (energy). Market prices arrive in EUR/MWh and must be converted to EUR/kWh at the boundary.
2. **Solvers & Performance:**
   - Use HiGHS solver through Pyomo's APPSI interface: `po.SolverFactory('appsi_highs')`.
   - The `highspy` package provides the solver binary; it does not need to be imported directly in application code. Pyomo discovers it automatically via `appsi_highs`.
   - When using `appsi_highs` with oemof.solph models, delete the `dual` and `rc` Suffix attributes from the Pyomo model before solving (oemof.solph adds them but APPSI does not support them): `delattr(m, 'dual'); delattr(m, 'rc')`.
   - Set solver options (`mip_rel_gap=0.01`, time limits) to guarantee fast convergence under annual hourly resolution datasets (8,760 timesteps).
3. **Operational vs Investment Mode:**
   - **Operational Mode:** Fixed asset capacities via `nominal_value` parameter on flows. Minimizes hourly variable operational expenditure (OPEX).
   - **Investment Mode:** Variable capacities via `nominal_value=solph.Investment(ep_costs=...)` on flows and `nominal_storage_capacity=solph.Investment(ep_costs=...)` on GenericStorage. Co-optimizes annualized CAPEX + OPEX.
   - Investment `ep_costs` must be the Equivalent Annual Cost (EAC) divided by 8760 to get a per-hour cost that oemof.solph can sum correctly.
4. **Feasibility Safeguards:**
   - Add slack sinks/sources with high penalty costs (e.g. 10x normal price) to avoid unhandled solver infeasibility exceptions during parameter exploration.
   - Always check `po.value(m.objective)` after solving to verify the solver found an optimal solution.
5. **oemof.solph API Notes (v0.5+ / v0.6+):**
   - `nominal_value` on flows triggers a FutureWarning about `nominal_capacity` -- this is safe to ignore in v0.6.x.
   - `nominal_storage_capacity` on GenericStorage triggers a similar warning -- also safe to ignore.
   - The `investment=` keyword argument on Flow was removed in v0.6. Use `nominal_value=solph.Investment(...)` instead.
   - Similarly for GenericStorage: use `nominal_storage_capacity=solph.Investment(...)` instead of `investment=`.
   - EnergySystem requires `infer_last_interval=False` when timeindex already includes the final boundary timestamp.

## Online References

| Topic | URL | What it provides |
|-------|-----|-----------------|
| oemof.solph Documentation | https://oemof-solph.readthedocs.io/en/latest/ | Official API docs, component reference, examples |
| oemof.solph GitHub | https://github.com/oemof/oemof-solph | Source code, issue tracker, example scripts in `examples/` |
| oemof.solph Investment Example | https://github.com/oemof/oemof-solph/tree/dev/examples | Canonical investment optimization example scripts |
| Pyomo Documentation | https://pyomo.readthedocs.io/en/stable/ | Pyomo modeling language reference |
| Pyomo APPSI HiGHS | https://pyomo.readthedocs.io/en/stable/contributed_packages/appsi/appsi.solvers.highs.html | APPSI interface for HiGHS solver |
| HiGHS Solver | https://highs.dev/ | HiGHS LP/MIP solver documentation and options |
| oemof Thermal (Heat Pumps) | https://github.com/oemof/oemof-thermal | Heat pump and solar thermal component extensions for oemof |
