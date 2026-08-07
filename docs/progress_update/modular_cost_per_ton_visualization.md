# Progress Report: Modular Unit Production Cost (€/ton) Visualization & Snapshot Period Tonnage Scaling

**Date:** August 7, 2026  
**Repository:** RIZM_challenge_Rafi  
**Task:** Implement `plot_scenario_cost_per_ton_interactive` and period-adjusted production tonnage scaling (`get_period_effective_tonnage`) in `src/utils.py`.

---

## 1. Summary of Changes

Added snapshot period tonnage scaling to [`src/utils.py`](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py) so that unit production costs (€/ton) are mathematically exact regardless of whether the model was solved for 24 hours, 7 days, 1 month, or a full year (8,760 hours).

### Key Abstractions Added:
1. **`get_period_effective_tonnage(res, annual_tonnage)`**:
   - Inspects PyPSA network snapshot count $N$ and objective weighting.
   - If the solve is for an unscaled $N$-hour operational period, scales effective tonnage to $\text{annual\_tonnage} \times (N / 8760.0)$.
   - If the solve is in investment mode (objective weighted to 8760h), uses full `annual_tonnage`.
2. **Updated `create_summary_dataframe`**: Uses `get_period_effective_tonnage` to compute accurate `Cost per Ton (EUR/ton)`.
3. **Updated `plot_scenario_cost_per_ton_interactive`**: Integrates period effective tonnage for dynamic 2, 3, or N scenario bar charts.

### Files Modified:
- [`src/utils.py`](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/utils.py)
- [`docs/progress_update/modular_cost_per_ton_visualization.md`](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/docs/progress_update/modular_cost_per_ton_visualization.md)

---

## 2. Status

- **Status:** Completed & Documented.
