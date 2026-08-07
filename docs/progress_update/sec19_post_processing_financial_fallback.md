# Progress Update: Upfront §19 Grid Capacity Constraint & Compliance Enforcement

## Summary of Changes
1. **Pre-Optimization §19 Capacity Constraint (`p_nom = 60,000 kW`)**:
   - Updated `build_energy_system()` in `src/optimization_model.py`.
   - When `enable_sec19_protection=True` is configured, `GridElectricityComponent` is built with a hard capacity bound `p_nom = 60000.0` kW (60 MW).
   - When `enable_sec19_protection=False`, `grid_electricity` remains unconstrained (`p_nom = 1,000,000 kW`).

2. **Co-Optimization of Flexibility Assets**:
   - Capping maximum grid draw at 60 MW upfront forces PyPSA to co-optimize flexibility assets (BESS storage, HTHP, TES, and PPAs) to peak-shave site electrical load below the statutory limit.
   - Guarantees 100% §19 StromNEV compliance by design, avoiding post-solve penalties or illegal peak draws.

3. **Audit Verification**:
   - Maintained post-solve check `sec19_violation = peak_grid_kw > 60000.0` for auditing consistency.

## Verification
- Grid capacity constraint logic verified in `src/optimization_model.py`.
