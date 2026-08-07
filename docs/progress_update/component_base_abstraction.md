# Base Component Financial & Lifecycle Abstraction Progress Report

> **Date:** August 7, 2026  
> **Status:** Completed  
> **Skills Referenced:** `python-best-practices`, `pypsa-asset-economics`

---

## 1. Executive Summary

This report documents the architectural refactoring of [`src/components/base.py`](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/components/base.py) and all derivative PyPSA energy system components in `src/components/`.

Prior to this task, every individual component class (`pv.py`, `boilers.py`, `chp.py`, `heat_pump.py`, `storage.py`) duplicated the exact same mathematical annuity calculation for Equivalent Annualized Capital Cost (EAC). Furthermore, Pydantic configuration classes re-declared common lifecycle fields (`name`, `is_extendable`, `lifetime_years`).

The refactoring abstracts common financial annuity calculation, lifecycle configuration, and capital cost resolution into `src/components/base.py`, establishing a DRY (Don't Repeat Yourself), highly testable, and maintainable OOP architecture across the entire PyPSA framework.

---

## 2. Technical Implementation Summary

### 2.1 Pure Annuity Calculation Helper (`src/components/base.py`)
- Created `calculate_annuity_capex(capex_per_unit, opex_per_unit_year, lifetime_years, wacc)` as a standalone pure function.
- Implements standard Capital Recovery Factor (CRF):
  $$\text{Annuity Factor} = \frac{r \cdot (1 + r)^n}{(1 + r)^n - 1}$$
- Enables isolated unit testing of financial math without instantiating PyPSA components.

### 2.2 Base Configuration Model (`BaseComponentConfig`)
- Defined `BaseComponentConfig(BaseModel)` containing standard asset metadata and bounds:
  - `name: str`
  - `is_extendable: bool = False`
  - `lifetime_years: int = 20`
- All component configuration schemas (`PVComponentConfig`, `GasBoilerConfig`, `EBoilerConfig`, `CHPComponentConfig`, `HTHPComponentConfig`, `BESSComponentConfig`, `TESComponentConfig`, `GridElectricityConfig`, `GridGasConfig`, `PVPPAConfig`, `WindPPAConfig`, `DemandConfig`) now inherit from `BaseComponentConfig`.

### 2.3 Polymorphic Base Class Enhancements (`BaseEnergyComponent`)
- Implemented default `calculate_annualized_capex(wacc)` on `BaseEnergyComponent` that automatically inspects config fields (`capex_eur_per_kw`, `opex_eur_per_kw_year`, `lifetime_years`, `annual_fee_eur_per_kw_year`) and computes EAC.
- Added `is_extendable` property helper: `getattr(self.config, "is_extendable", False)`.
- Added `get_capital_cost(wacc)` helper method returning `self.calculate_annualized_capex(wacc)` if extendable, or `0.0` for fixed capacity assets.

### 2.4 Subclass Code Simplification (`src/components/*.py`)
- Updated `pv.py`, `boilers.py`, `chp.py`, `heat_pump.py`, `storage.py`, `grid.py`, and `demand.py`.
- Removed ~80 lines of duplicate financial annuity calculation boilerplate.
- Replaced repeated capital cost evaluation blocks in `build_component()` with `self.get_capital_cost(wacc)`.
- Exported `BaseComponentConfig` and `calculate_annuity_capex` in [`src/components/__init__.py`](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/components/__init__.py).

---

## 3. Verification & Architecture Benefits

1. **Single Source of Truth:** Updating discount rates, tax treatments, or residual asset value adjustments only requires modifying `calculate_annuity_capex` in `src/components/base.py`.
2. **Polymorphic Compatibility:** Calling code continues to use `component.calculate_annualized_capex(wacc)` or `component.get_capital_cost(wacc)` without breaking any external signatures.
3. **Clean Code & Type Safety:** All components conform to PEP 8 standards, typed Pydantic models, and strict docstring formatting per `python-best-practices`.
