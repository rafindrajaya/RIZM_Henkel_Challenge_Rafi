# RIZM Agentic Energy OS — Henkel Düsseldorf Holthausen Pilot

Production-grade, modular, reproducible MVP repository and decision framework for **Henkel’s flagship chemical and consumer goods manufacturing site in Düsseldorf-Holthausen**.

---

## 🎯 Executive Summary & Primary Metric

The Henkel Holthausen complex produces over **450,000 tons/year** of laundry detergents, home care products, and industrial adhesives, consuming continuous baseload energy of **60 MW electrical ($MW_{el}$)** and **220 MW thermal ($MW_{th}$)**. Energy costs directly dictate site competitiveness in global chemical markets.

This project delivers a data-driven optimization engine that evaluates energy business use cases strictly measured in **€ / ton of industrial output**:

1. **Operation Hub (PyPSA Dispatch Optimization):** Optimizes real-time dispatch of existing asset infrastructure (40 MW Gas CHP, 180 MW Gas Boiler, 30 MW Electric Boiler, 15 MW HTHP, BESS, TES) against German Day-Ahead & Intraday spot electricity markets while preserving Henkel's **§ 19 Abs. 2 StromNEV** grid fee exemption (~€3.5M/yr value).
2. **Decision Hub (CAPEX Co-Optimization):** Jointly sizes green technology investments—Rooftop Solar PV (25 MWp limit), High-Temperature Industrial Heat Pumps (HTHP), Battery Energy Storage (BESS), and Thermal Energy Storage (TES)—using Equivalent Annual Costs (EAC).
3. **Strategic On-Site Protocol:** Identifies the single most load-bearing 15-minute coincidental time-series data request and 30-minute agenda with the Head of On-Site Energy & Infrastructure (*Leiter Energieversorgung Holthausen*).

---

## 📂 Repository Navigation

```
RIZM_challenge_Rafi/
├── .agent/
│   └── skills/                  # Domain skills grounding AI agentic workflow
│       ├── pypsa-reporting/
│       ├── pypsa-asset-economics/
│       ├── python-best-practices.md
│       ├── german-energy-market-specialist.md
│       └── solution-architect-career-coach.md
├── data/                        # Pre-bundled SMARD spot prices, THE gas, Open-Meteo weather CSVs & TOML configs
│   └── components/              # TOML asset specification files (pv.toml, bess.toml, chp.toml, eboiler.toml, hthp.toml)
├── ref/                         # StoREN DLR study, Henkel annual reports, Bolten et al. 2026 paper
├── src/
│   ├── __init__.py
│   ├── components/              # DevOps OOP modular component class hierarchy
│   │   ├── base.py              # BaseEnergyComponent abstract class interface
│   │   ├── grid.py              # Electricity and Gas grid import components
│   │   ├── pv.py                # Rooftop PV Solar generator
│   │   ├── chp.py               # Combined Heat and Power unit link
│   │   ├── boilers.py           # Gas Boiler, Electric Boiler, Steam-Heat Exchanger
│   │   ├── heat_pump.py         # High-Temperature Heat Pump (HTHP)
│   │   ├── storage.py           # BESS and TES storage units
│   │   └── demand.py            # Industrial demand sinks (Loads)
│   ├── external_api.py          # Market & solar weather pipeline connector
│   ├── optimization_model.py   # PyPSA Network energy system builder & Pydantic config schemas
│   └── utils.py                 # Visual reporting, interactive Plotly dashboard & financial metrics
├── scripts/
│   └── build_notebook.py        # Automated notebook builder script
├── docs/                        # Progress updates, solution notes & checklist
├── challenge.ipynb              # Main executive notebook deliverable
├── pyproject.toml               # Modern Python project configuration
├── uv.lock                      # Universal lockfile for 100% environment reproducibility
└── README.md                    # Project entry point & architectural narrative
```

---

## 🚀 Quick Start & Reproducibility (`uv`)

This repository uses [`uv`](https://github.com/astral-sh/uv) for fast, cross-platform dependency locking.

### 1. Clone & Sync Environment
```bash
git clone https://github.com/mrafiindrajaya/RIZM_challenge_Rafi.git
cd RIZM_challenge_Rafi

# Sync exact lockfile dependencies
uv sync
```

### 2. Run Executive Notebook
```bash
# Launch Jupyter Lab
uv run jupyter lab challenge.ipynb
```

Or execute directly from CLI:
```bash
uv run python -m src.external_api
uv run python -m src.optimization_model
```

---

## 🛠️ Toolchain & Architecture Declaration

- **Optimization Framework:** `PyPSA` (Python for Power System Analysis, >=0.28.0) + `linopy` + `highspy` / `HiGHS` MILP Solver.
- **Component Design:** OOP class hierarchy in `src/components/` enforcing Pydantic validation on TOML configuration models.
- **Solar Simulation & Weather:** `pvlib` + Open-Meteo Historical Weather API.
- **Visualization:** `plotly` (interactive HTML dashboards) & `matplotlib` (publication-ready static exports).
- **Environment Management:** `uv` (v0.11+).
