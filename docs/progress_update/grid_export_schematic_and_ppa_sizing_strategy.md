# Grid Export Schematic Representation & PPA Sizing Strategy Report

> **Date:** August 9, 2026  
> **Status:** Completed  
> **Skills Referenced:** `pypsa-reporting`, `pypsa-physical-realism`

---

## 1. Executive Summary

This update resolves the missing **Grid Export** node in `plot_network_schematic()` and establishes an engineering framework for realistic PPA capacity bounds (`PV PPA` and `Wind PPA`) in PyPSA investment optimization.

Prior to this update, `plot_network_schematic()` rendered all supply and conversion assets but omitted `grid_export` because the schematic layout nodes were configured before `GridExportComponent` was integrated. Additionally, linear programming solvers expanded extendable PPAs to their upper bound (`50,000 kW`) due to positive wholesale spot market spreads. This report documents the schematic visualization fix in `src/utils.py` and outlines practical PPA capacity bounding strategies.

---

## 2. Technical Implementation Summary

### 2.1 Schematic Diagram Refactoring (`src/utils.py`)
- **Node Topology Update**: Added `"grid_export"` node template at position `(1, 5.2)` with color `#17becf` and label `"Grid Export\n(Wholesale Spot)"`.
- **Generator Inclusion Filter**: Included `"grid_export"` in the generator index filter check inside `plot_network_schematic()`.
- **Flow Arrow Connection**: Added edge connection `("b_elec", "grid_export")` to display outbound power flow arrows from the electricity bus (`b_elec`) to wholesale grid export.

### 2.2 PPA Sizing Realism & Capping Strategy Framework
- **Root Cause Analysis**: PPA levelized costs (€55–€66.6/MWh) are frequently lower than wholesale EPEX spot prices (€70–€100+/MWh), creating a positive arbitrage spread. In linear optimization without export limits, the LP solver maximizes PPA investment up to `max_capacity`.
- **Capping Strategy Guidelines**:
  1. **Peak Site Load Cap (60 MW / 60,000 kW)**: Caps PPA total capacity to match peak site grid connection capacity, respecting physical grid transformer bounds.
  2. **Baseload Hedge Cap (25 MW / 25,000 kW) [Recommended]**: Models conservative industrial procurement by hedging 40–70% of electrical baseload, preventing speculative power trading while providing green power coverage.
  3. **Grid Export Capacity Cap (`GridExportConfig.p_nom`)**: Limits maximum export flow (e.g. 10 MW or 0 MW for net-zero export) to simulate real-world grid injection constraints.

---

## 3. Verification & Compliance

- [x] Updated `plot_network_schematic()` in `src/utils.py` to render `grid_export`.
- [x] Preserved existing block diagram styling and layout hierarchy.
- [x] Rule 8 Compliance: Zero changes made to `challenge.ipynb` or `challenge_interactive.ipynb`.
