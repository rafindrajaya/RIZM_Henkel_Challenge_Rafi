# Progress Update: Static 1-Week Plotting Mode & Date Slicing Integration

## Overview
Added static 1-week datetime window slicing and `mode` selection (`"interactive"` | `"static"`) to PyPSA dispatch stack and market price plotting functions in `src/utils.py`. This enables dynamic online rendering on GitHub web notebook previews without needing interactive Plotly JavaScript execution.

## Key Changes
1. **Helper Function `_slice_snapshots_by_window`**:
   - Parses datetime strings with flexible formats using `pd.to_datetime(..., dayfirst=True)`.
   - Defaults to `start_time` from `FacilityProjectConfig` (or first network snapshot).
   - Handles out-of-bounds start dates gracefully by emitting a `UserWarning` without crashing and falling back to default start time.
   - Slices snapshots for `duration_days` (default `7.0` days = 168 hours).

2. **Updated Functions in `src/utils.py`**:
   - `plot_dispatch_stacks(results, title=..., start_time=None, duration_days=7.0)` (Refactored to 2D line curves per carrier, adding continuous black dashed load demand curves (`demand_elec`, `demand_steam`, `demand_heat`), complete legend coverage for all activated network components, and side legend placement `bbox_to_anchor=(1.02, 1)`).
   - `plot_dispatch_stacks_interactive(results, title=..., mode="interactive", start_time=None, duration_days=7.0)`
   - `plot_market_prices_interactive(results, title=..., mode="interactive", start_time=None, duration_days=7.0)`
   - `plot_scenario_cost_per_ton(scenarios, title=..., mode="static")` (Defaults to static Matplotlib figure with value labels and custom colors).
   - Added explicit static aliases `plot_dispatch_stacks_static`, `plot_market_prices_static`, and `plot_scenario_cost_per_ton_static`.
   - Issued warnings if `start_time` is specified in `mode="interactive"`.

3. **Automated Testing**:
   - Added unit test suite in `tests/test_static_1week_plotting.py` covering default window slicing, custom date strings, out-of-bound warning fallback, static/interactive function calls, and scenario cost per ton bar chart.

## Rule 8 Compliance
- Zero edits were made to `challenge.ipynb`.
