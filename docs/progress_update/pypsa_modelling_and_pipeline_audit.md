# Audit Report: PyPSA Core Modeling & Data Pipeline Analysis

**Date:** August 7, 2026  
**Repository:** RIZM_challenge_Rafi  
**Audited Modules:** `src/optimization_model.py` and `src/external_api.py`  
**Skill Guidelines Applied:**
- `.agent/skills/python-best-practices.skill.md`
- `.agent/skills/pypsa-network-modeling/SKILL.md`
- `.agent/skills/pypsa-data-pipelines/SKILL.md`
- `.agent/skills/pypsa-physical-realism/SKILL.md`

---

## 1. Executive Summary

A comprehensive audit was performed on the core energy system modeling engine ([optimization_model.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/optimization_model.py)) and the external data pipeline connector ([external_api.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/external_api.py)). 

Overall, the architecture demonstrates strong physical realism (dual-temperature heat cascade, proper efficiency-to-input link capacity scaling, and valid thermodynamic parameters). However, key logical, numerical, and structural discrepancies were identified in:
1. **WACC Propagation & CAPEX Annualization**
2. **PyPSA Pre-Optimization & Snapshot Weighting Discipline**
3. **Storage Charger/Discharger Free Expansion Sizing**
4. **Timezone DST Artifacts in Data Pipelines**

---

## 2. Detailed Audit Findings Matrix

### Domain A: Python Best Practices (`python-best-practices.skill.md`)

| Module / Component | Finding | Severity | Status | Remediation Implemented |
|---|---|---|---|---|
| `src/components/*.py` | Hardcoded `wacc=0.07` in `build_component()` | **High** | **FIXED** | Updated `BaseEnergyComponent.build_component(n, wacc=0.07)` signature across all component classes. `HenkelEnergySystem` now explicitly passes `wacc=self.wacc` to all components. |
| `src/optimization_model.py` | Broad `except Exception:` in `compute_pv_normalized_yield` | **Medium** | **FIXED** | Replaced broad exception catching with explicit tuple `(ImportError, KeyError, ValueError, AttributeError)` and logged descriptive warnings via standard `logger`. |
| `src/optimization_model.py` | Magic numbers in dataframe slicing | **Low** | **FIXED** | Defined `DEFAULT_FALLBACK_TIMESTEPS = 168` constant and added `logger.warning` explaining fallback behavior if date slicing returns empty data. |
| `src/external_api.py` | Broad exception handling in Open-Meteo & Highs solver checks | **Low** | **FIXED** | Updated `fetch_open_meteo_solar` to catch explicit `(requests.RequestException, KeyError, ValueError)` with formatted error class logging. |

---

### Domain B: PyPSA Network Modeling (`pypsa-network-modeling`)

| Aspect / Function | Finding | Severity | Status | Remediation Implemented |
|---|---|---|---|---|
| `n.consistency_check()` | Omitted before `n.optimize()` in `solve()` | **High** | **FIXED** | Added mandatory `n.consistency_check()` immediately before `n.optimize()` in `HenkelEnergySystem.solve()`. |
| Partial-Year Snapshot Weightings | Disconnect between Annualized CAPEX & Sub-Year OPEX | **High** | **FIXED** | Configured `n.snapshot_weightings["objective"] = 8760.0 / len(snapshots)` in `build_energy_system()` when in investment mode, balancing partial-year OPEX with 1-year annualized CAPEX. |
| BESS & TES Link Sizing | Unpriced Charger/Discharger `p_nom_extendable` | **Medium** | **FIXED** | Added `p_nom_min` bounds in `storage.py` and introduced `apply_c_rate_coupling` extra functionality in `n.optimize()`, dynamically binding charger and discharger link capacities to store energy ($P_{nom} = E_{nom} \times \text{c\_rate}$). |
| OPEX Calculation | `(p * marginal_cost).sum()` in `solve()` | **Low** | **FIXED** | Scaled OPEX calculations in `solve()` by `n.snapshot_weightings.objective`, maintaining exact consistency with the objective function. |

---

### Domain C: PyPSA Data Pipelines (`pypsa-data-pipelines`)

| Data Stream / Function | Finding | Severity | Status | Remediation Implemented |
|---|---|---|---|---|
| `fetch_smard_electricity_prices` | Timezone conversion `Europe/Berlin` + `drop_duplicates` | **High** | **FIXED** | Enforced strict internal UTC timestamps for SMARD electricity market data, eliminating DST clock shift hour deletions/duplications. |
| `fetch_open_meteo_solar` | `timezone="Europe/Berlin"` API request | **Medium** | **FIXED** | Changed API request parameter to `"timezone": "UTC"` for Open-Meteo weather data, ensuring 1-to-1 hourly timestamp alignment with market data. |
| `generate_synthetic_solar_data` | Non-deterministic random noise | **Low** | **FIXED** | Added explicit `np.random.seed(42)` initialization at start of fallback function, making synthetic weather profiles 100% reproducible. |

---

### Domain D: Logical System & Physical Realism (`pypsa-physical-realism`)

| Component / Subsystem | Status | Engineering Evaluation |
|---|---|---|
| Thermal Cascade | **PASS** | Dual-temperature structure ($b\_steam\_ht$ 160 MW_th @ high temp vs $b\_heat\_lt$ 60 MW_th @ mid temp) strictly prevents low-temp heat pumps from violating thermodynamic quality rules. |
| Link Unit Scaling | **PASS** | $P_{nom}$ represents input capacity at `bus0`. Capital cost and capacity bounds for CHP, Boilers, and HTHP are properly scaled by efficiency/COP. |
| Storage Thermodynamics | **PASS** | BESS RTE (90.25%) and TES RTE (96.04%) with self-discharge losses are physically grounded. |

---

## 3. Data Repopulation & Optimal PV Yield Caching

Both local benchmark CSV files in `data/` were repopulated using the updated pipeline in [external_api.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/external_api.py):
1. **[market_data_2025.csv](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/data/market_data_2025.csv)**: Repopulated with UTC-aligned 2025 SMARD spot prices and THE natural gas benchmark data.
2. **[solar_data_duesseldorf_2025.csv](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/data/solar_data_duesseldorf_2025.csv)**: Repopulated with UTC Open-Meteo weather data and pre-computed, cached `pv_normalized_yield` profile.

### Optimal `pvlib` Parameter Configuration:
- **Location:** Düsseldorf Holthausen ($51.1783^\circ\text{ N}, 6.8445^\circ\text{ E}$)
- **Surface Geometry:** Tilt = $38.0^\circ$ (optimal annual tilt for $51.2^\circ\text{ N}$), Azimuth = $180.0^\circ$ (South)
- **Irradiance Transposition Model:** Hay-Davies model with exact `dni_extra` extraterrestrial radiation
- **Thermal Model:** Faiman cell temperature model
- **DC/AC Derating & System Efficiency:** PVWatts DC model ($\gamma = -0.4\%/\text{°C}$) with 96% inverter efficiency factor

The pre-computed `pv_normalized_yield` column is cached directly in `solar_data_duesseldorf_2025.csv`, allowing `HenkelEnergySystem` to instantly load normalized solar yield without executing runtime `pvlib` simulations.

