# Demand Component Configuration Report

> **Date:** August 7, 2026  
> **Status:** Completed  
> **Task:** Configurable Demand Component in PyPSA Framework  

---

## 1. Summary of Changes

To enable full scenario flexibility and component-level standardisation across the framework, the industrial demand sinks (Loads) have been made configurable via both component TOML specs and scenario-level Pydantic overrides.

### Key Modifications:

1. **`[NEW]` `data/components/demand.toml`:**
   - Standardized baseline continuous demand levels for Henkel Holthausen:
     - `elec_demand_mw = 60.0` (Electrical continuous demand in MW)
     - `steam_demand_mw_th = 160.0` (High-temperature steam demand in MW_th)
     - `heat_demand_mw_th = 60.0` (Mid-temperature process heat demand in MW_th)

2. **`[MODIFY]` `src/optimization_model.py`:**
   - **`FixedSizingConfig`:** Added optional scenario override fields (`demand_elec_mw`, `demand_steam_mw_th`, `demand_heat_mw_th`).
   - **`ComponentConfigs` & `load_component_config`:** Registered `demand: DemandConfig` in component config container and TOML parsing logic.
   - **`HenkelEnergySystem.build_energy_system`:** Implemented 2-tier hierarchical demand resolution:
     - Tier 1: Component default loads loaded from `data/components/demand.toml`.
     - Tier 2: Direct scenario overrides if provided in `FacilityProjectConfig.fixed_components_sizing`.
     - Clean call to `DemandComponent(demand_cfg).build_component(n)` (removed unused `wacc` parameter).

---

## 2. Verification

- Verified `demand.toml` parsing and Pydantic validation schema integration.
- Verified zero-CAPEX behavior and accurate load creation on `b_elec`, `b_steam_ht`, and `b_heat_lt` PyPSA buses.
