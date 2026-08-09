# Configurable BESS Cyclic State-of-Charge Feature Report

> **Date:** August 9, 2026  
> **Status:** Completed  
> **Skills Referenced:** `pypsa-physical-realism`

---

## 1. Executive Summary

This update adds a configurable `e_cyclic` parameter to `data/components/bess.toml`, `BESSComponentConfig`, `TESComponentConfig`, and the PyPSA `Store` builder methods in `src/components/storage.py` and `src/optimization_model.py`.

Prior to this update, PyPSA `Store` components for BESS and TES hardcoded `e_cyclic=True`. Adding `e_cyclic` as a configurable attribute allows users to toggle between cyclic state-of-charge constraints ($e_{\text{start}} = e_{\text{end}}$) and fixed initial SOC constraints ($e_{0} = e_{\text{nom}} \times \text{initial\_soc}$).

---

## 2. Technical Implementation Summary

### 2.1 Configuration File (`data/components/bess.toml`)
- Added `e_cyclic = true` under the `# Performance` section.

### 2.2 Schema & Component Builder (`src/components/storage.py`)
- **`BESSComponentConfig` & `TESComponentConfig`**: Added `e_cyclic: bool = Field(default=True, description="Enable cyclic state of charge constraint (e_start == e_end)")`.
- **`BESSComponent` & `TESComponent`**: Replaced hardcoded `e_cyclic=True` with `e_cyclic=self.bess_config.e_cyclic` and `e_cyclic=self.tes_config.e_cyclic` across extendable and non-extendable PyPSA `Store` component initialization.

### 2.3 Optimization Model Integration (`src/optimization_model.py`)
- Updated `HenkelEnergySystem.build_energy_system` to pass `min_soc`, `initial_soc`, and `e_cyclic` from loaded component configurations into `bess_cfg` and `tes_cfg`.

---

## 3. Verification Checklist

- [x] Configured `e_cyclic = true` in `data/components/bess.toml`.
- [x] Added `e_cyclic` parameter to `BESSComponentConfig` and `TESComponentConfig`.
- [x] Connected `e_cyclic` directly to PyPSA `Store` components.
- [x] Rule 8 Compliance: Zero modifications made to `challenge.ipynb` or `challenge_interactive.ipynb`.
