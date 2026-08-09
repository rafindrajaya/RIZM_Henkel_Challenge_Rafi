# Configurable Grid Export Capacity Feature Report

> **Date:** August 9, 2026  
> **Status:** Completed  
> **Skills Referenced:** `pypsa-physical-realism`

---

## 1. Executive Summary

This update adds a configurable `grid_export` capacity field to `FixedSizingConfig` within `src/optimization_model.py`. This allows users and sensitivity notebooks to configure custom grid export limits (e.g., `60,000 kW` for peak load match, `30,000 kW` for DSO limits, or `0 kW` for net-zero export) and observe how the PyPSA optimization model adjusts PPA sizing and energy balance dispatch.

---

## 2. Technical Implementation Details

### 2.1 Pydantic Schema Update (`src/optimization_model.py`)
- **`FixedSizingConfig`**: Added `grid_export: float = Field(default=1e6, ge=0.0, description="Electricity grid export capacity limit in kW")`.
- Default value is set to `1e6` (1,000,000 kW = 1 GW), maintaining unconstrained grid export by default while allowing custom limits.

### 2.2 Model Constructor & Component Wiring (`src/optimization_model.py`)
- **`HenkelEnergySystem.__init__`**: Bound `self.grid_export_limit_kw = self.config.fixed_components_sizing.grid_export`.
- **`build_energy_system`**: Instantiated `GridExportConfig(p_nom=self.config.fixed_components_sizing.grid_export)` and passed it to `GridExportComponent`.

---

## 3. Usage Examples

```python
from src.optimization_model import FixedSizingConfig, FacilityProjectConfig, HenkelEnergySystem

# Example 1: Cap Grid Export to Peak Site Load (60 MW / 60,000 kW)
cfg_60mw = FacilityProjectConfig(
    optimization_mode="investment",
    fixed_components_sizing=FixedSizingConfig(grid_export=60000.0)
)
model_60mw = HenkelEnergySystem(config=cfg_60mw)

# Example 2: Strict Net-Zero Export (0 kW)
cfg_zero = FacilityProjectConfig(
    optimization_mode="investment",
    fixed_components_sizing=FixedSizingConfig(grid_export=0.0)
)
model_zero = HenkelEnergySystem(config=cfg_zero)
```

---

## 4. Verification Checklist

- [x] Added `grid_export` field to `FixedSizingConfig`.
- [x] Wired `grid_export` to `GridExportComponent` `p_nom` attribute in PyPSA Network.
- [x] Verified default value is `1e6` kW (backwards-compatible).
- [x] Rule 8 Compliance: Zero modifications made to `challenge.ipynb` or `challenge_interactive.ipynb`.
