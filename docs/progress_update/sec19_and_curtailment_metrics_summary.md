# Progress Update: §19 StromNEV Compliance Mechanics & Summary Dataframe Curtailment Metrics

## Summary of Changes
1. **Clarified §19 StromNEV Compliance Architecture**:
   - `enable_sec19_protection=True` in `FacilityProjectConfig` configures the grid electricity price series to `elec_total_sec19_eur_mwh` (incorporating discounted grid fees) when constructing the PyPSA network.
   - Post-solve verification checks whether peak grid demand (`peak_grid_demand_kw > 60000.0` or full load hours < 7000h) violates statutory limits.
   - Clarified that `Sec19 Compliant = False` in the summary table is an ex-post audit metric warning that peak grid draw exceeded the 60 MW threshold.

2. **Added Curtailment Percentage Columns to `create_summary_dataframe`**:
   - Implemented `calculate_curtailment_metrics()` in `src/utils.py`.
   - Added `Curtailed Elec (%)` (`curtailed electricity / total electricity generated across all sources`) and `Curtailed Heat (%)` (`curtailed heat & steam dumped / total heat & steam produced`) to `create_summary_dataframe()`.
   - Supported both Operation Hub and Decision Hub scenarios.

## Verification
- Function signatures and dataframe outputs verified.
