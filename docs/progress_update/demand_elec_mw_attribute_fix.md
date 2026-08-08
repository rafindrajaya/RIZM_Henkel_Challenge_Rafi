# Electrical Demand Attribute and Modular §19 Grid Capacity Fix

> **Date:** August 8, 2026  
> **Status:** Completed  
> **Task:** Fix AttributeError for self.demand_elec_mw and Modularize §19 Grid Capacity Sizing  

---

## 1. Summary of Changes

### Background & Issue
When configuring §19 grid peak load protection (`enable_sec19_protection = True`), the grid import capacity `grid_p_nom` was set to scale dynamically at 1.25× continuous electrical demand (`1.25 * self.demand_elec_mw`). However, calling `self.demand_elec_mw` raised `AttributeError: 'HenkelEnergySystem' object has no attribute 'demand_elec_mw'` because `demand_elec_mw` was not bound to `self` in `HenkelEnergySystem.__init__`.

### Key Modifications in `src/optimization_model.py`:

1. **`[MODIFY]` `HenkelEnergySystem.__init__`**:
   - Initialised `self.demand_elec_mw` as an active attribute on `HenkelEnergySystem`.
   - Hierarchical resolution order:
     1. Uses scenario override `self.config.fixed_components_sizing.demand_elec_mw` if provided.
     2. Falls back to default `self.comp_cfg.demand.elec_demand_mw` from `data/components/demand.toml` (60.0 MW).

2. **`[MODIFY]` `HenkelEnergySystem.build_energy_system`**:
   - Updated grid electricity generator sizing calculation:
     ```python
     grid_p_nom = 1.25 * self.demand_elec_mw * 1000.0 if self.enable_sec19_protection else 1e6
     ```
   - Correctly converted electrical demand from **MW** to **kW** (e.g. 60.0 MW demand → 75,000.0 kW grid import limit).

---

## 2. Verification

- Verified `self.demand_elec_mw` resolves dynamically across both default `demand.toml` specs and custom `FacilityProjectConfig` scenario overrides.
- Verified unit conversion consistency for PyPSA `grid_electricity` generator nominal capacity (`p_nom`).
