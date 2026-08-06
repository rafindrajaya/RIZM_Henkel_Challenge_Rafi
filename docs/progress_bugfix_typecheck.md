# Repository Status Update: Pyomo Objective Type Safety Fix

## Task Executed
- Fixed type mismatch error: `/` is not supported between `None` and `float` at [src/optimization_model.py](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/RIZM_challenge_Rafi/src/optimization_model.py#L545-L553).

## Root Cause
`pyomo.environ.value(m.objective)` has return type annotations of `float | None` in Pyomo stubs. Static type checkers (Pyright/Mypy) infer `total_cost_eur` as `Optional[float]`, flagging `total_cost_eur / annual_production_tons` as an invalid `None / float` division.

## Resolution
1. Stored the raw Pyomo value in `raw_obj = po.value(m.objective)`.
2. Checked if `raw_obj is None` and raised a `ValueError` if the solver objective failed to compute.
3. Cast `raw_obj` explicitly to `float` (`total_cost_eur = float(raw_obj)`), guaranteeing runtime type safety and satisfying Pyright rules.
