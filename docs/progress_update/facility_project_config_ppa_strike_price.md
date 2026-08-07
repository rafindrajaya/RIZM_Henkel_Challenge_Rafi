# Progress Update: FacilityProjectConfig PPA Strike Price Support

## Summary of Changes
1. **Updated `FacilityProjectConfig` in `src/optimization_model.py`**:
   - Added `pv_ppa_strike_price_eur_per_mwh: Optional[float]` for overriding solar PPA strike price (€/MWh).
   - Added `wind_ppa_strike_price_eur_per_mwh: Optional[float]` for overriding wind PPA strike price (€/MWh).

2. **Updated `EnergySystemOptimizationModel.__init__` in `src/optimization_model.py`**:
   - Automatically propagates top-level `FacilityProjectConfig` PPA strike price overrides to `self.comp_cfg.pv_ppa` and `self.comp_cfg.wind_ppa` during initialization.

3. **Notebook Safety Compliance (Rule 8)**:
   - `challenge.ipynb` was not modified.

## Verification
- Verified schema update and instantiation logic in `src/optimization_model.py`.
