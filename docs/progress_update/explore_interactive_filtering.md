# Progress Report: Post-Solve Candidate Asset Filtering in `explore_network_interactive`

**Date:** August 7, 2026  
**Repository:** RIZM_challenge_Rafi  
**Task:** Update `explore_network_interactive` in `src/utils.py` to support automatic post-solve exclusion of unbuilt candidate assets (`p_nom_opt <= 1e-3` / `e_nom_opt <= 1e-3`).

---

## 1. Executive Summary

Updated `explore_network_interactive(results_or_net, active_only=True)` in `src/utils.py`. When called post-solve with `active_only=True` (default), the function now creates a temporary network copy and filters out extendable candidate generators, links, and stores that received zero investment (`p_nom_opt <= 1e-3` / `e_nom_opt <= 1e-3`). This ensures interactive map visualizations (`n.explore()`) reflect only actively built assets without clutter from unbuilt candidate components.

---

## 2. Updated Architecture & Function Signature

### `src/utils.py`
- **`explore_network_interactive(results_or_net: Any, active_only: bool = True)`**:
  - `active_only=True` (default): If the network is solved, extendable components (`generators`, `links`, `stores`) with `p_nom_opt <= 1e-3` or `e_nom_opt <= 1e-3` are removed from a copied network before rendering `n.explore()`.
  - `active_only=False`: Renders all instantiated network components (useful for pre-solve structural inspection).
  - Preserves default GPS spatial coordinates injection for Henkel site buses (`b_elec`, `b_gas`, `b_steam_ht`, `b_heat_lt`, `bess_bus`, `tes_bus`).

---

## 3. Files Modified

1. **`src/utils.py`**: Updated `explore_network_interactive()` with `active_only` candidate filtering logic.
2. **`docs/progress_update/explore_interactive_filtering.md`**: Created progress report.

---

## 4. Usage Example in Notebooks (`challenge.ipynb`)

```python
from src.utils import explore_network_interactive

# Post-solve map showing built assets only (active_only=True by default)
map_invested = explore_network_interactive(results)

# Post-solve or pre-solve map showing all candidate assets
map_all_candidates = explore_network_interactive(results, active_only=False)
```

**Status:** Completed and verified.
