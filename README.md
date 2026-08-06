# RIZM Agentic Energy OS — Henkel Düsseldorf Holthausen Pilot

Production-grade, modular, reproducible MVP repository and decision framework for **Henkel’s flagship chemical and consumer goods manufacturing site in Düsseldorf-Holthausen**.

---

## 🎯 Executive Summary & Primary Metric

The Henkel Holthausen complex produces over **450,000 tons/year** of laundry detergents, home care products, and industrial adhesives, consuming continuous baseload energy of **60 MW electrical ($MW_{el}$)** and **220 MW thermal ($MW_{th}$)**. Energy costs directly dictate site competitiveness in global chemical markets.

This project delivers a data-driven optimization engine that evaluates energy business use cases strictly measured in **€ / ton of industrial output**:

1. **Operation Hub (MILP Dispatch Optimization):** Optimizes real-time dispatch of existing asset infrastructure (40 MW Gas CHP, 180 MW Gas Boiler, 30 MW Electric Boiler, BESS, TES) against 15-minute German Day-Ahead & Intraday spot electricity markets while preserving Henkel's **§ 19 Abs. 2 StromNEV** grid fee exemption (~€3.5M/yr value).
2. **Decision Hub (CAPEX Co-Optimization):** Jointly sizes green technology investments—Rooftop Solar PV (25 MWp limit), High-Temperature Industrial Heat Pumps (HTHP), Battery Energy Storage (BESS), and Thermal Energy Storage (TES)—using Equivalent Annual Costs (EAC).
3. **Strategic On-Site Protocol:** Identifies the single most load-bearing 15-minute coincidental time-series data request and 30-minute agenda with the Head of On-Site Energy & Infrastructure (*Leiter Energieversorgung Holthausen*).

---

## 📂 Repository Navigation

```
RIZM_challenge_Rafi/
├── .agent/
│   └── skills/                  # Specialized domain skills grounding AI agentic workflow
│       ├── python-best-practices.md
│       ├── german-energy-market-specialist.md
│       ├── milp-optimization-engineer.md
│       ├── thermodynamics-exergy-specialist.md
│       └── solution-architect-career-coach.md
├── data/                        # Pre-bundled 15-min SMARD spot prices, THE gas, Open-Meteo weather CSVs
├── ref/                         # StoREN DLR study, Henkel annual reports, Bolten et al. 2026 paper
├── src/
│   ├── __init__.py
│   ├── external_api.py          # Market & solar weather pipeline connector
│   └── optimization_model.py   # Object-Oriented oemof.solph MILP Energy System builder
├── scripts/
│   └── build_notebook.py        # Automated notebook builder script
├── challenge.ipynb              # Main executive notebook deliverable (executed with plots)
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

## 📊 Summary of Optimization Results (€/ton)

| Phase / Scenario | Total Energy Cost (€/ton) | Annual Cost (450k tons) | Key Driver |
| :--- | :---: | :---: | :--- |
| **Unoptimized Baseline** | **€318.83 / ton** | €143.47 M / yr | Fixed gas boiler operation + unhedged grid electricity |
| **Operation Hub (MILP Dispatch)** | **€372.54 / ton** *(168h sample)* | Benchmark | Spot market price arbitrage + Power-to-Heat (P2H) + §19 StromNEV protection |
| **Decision Hub (Optimal Sizing)** | **€352.36 / ton** *(168h sample)* | **-€9.10 M / yr** | 25 MWp Rooftop PV + 40 MW_th HTHP waste heat recovery + 44.5 MWh_th TES |

---

## 🤝 Strategic On-Site Protocol for Henkel Düsseldorf TODO: This should be moved to the last section in challenge.ipynb I think

### 1. The Single Most Load-Bearing Data Request
> **12 continuous months of coincidental 15-minute resolution time-series data for site electrical import and thermal steam demand broken down by pressure level (16 bar vs 4 bar vs hot water headers).**
> 
> *Rationale:* High-frequency coincidental load shapes reveal peak coincidence, thermal ramp limits, and true waste-heat recovery potential that cannot be inferred from monthly utility bills.

### 2. The Single Most Load-Bearing Stakeholder (30-Minute Agenda)
> **Head of On-Site Energy Utilities & Infrastructure (*Leiter Energieversorgung Holthausen*)**
> 
> *30-Minute Agenda:*
> 1. **Min 0–5:** Baseline €/ton energy cost breakdown and § 19 StromNEV grid fee discount protection protocol.
> 2. **Min 5–15:** Operation Hub real-time dispatch walk-through (CHP & Electric Boiler spot arbitrage).
> 3. **Min 15–25:** Decision Hub investment roadmap (HTHP waste heat recovery & rooftop PV spatial footprint).
> 4. **Min 25–30:** Telemetry integration requirements for Agentic Energy OS telemetry.

---

## 🛠️ Toolchain Transparency Declaration

Per challenge requirement:
- **Optimization Engine:** `oemof.solph` (v0.6.4) + `pyomo` + `highspy` / `HiGHS` MILP Solver.
- **Solar Simulation & Weather:** `pvlib` + Open-Meteo Historical Weather API.
- **Market Datasets:** SMARD (Bundesnetzagentur German Wholesale Electricity) & THE (Trading Hub Europe gas proxy).
- **Environment Management:** `uv` (v0.11.9).

# What I want to add:
## Why I used this approach to tackle the challenge and why abstraction to this extent, not more not less
## Mermaid diagram of the process of tackling this challenge
## 
