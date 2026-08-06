# SPEC.md -- Henkel Dusseldorf Agentic Energy OS Challenge

> Single Source of Truth for architecture, directory structure, tech stack, data schemas, feature scope, and task execution order.

---

## 1. Project Objective

Build a production-grade, modular, reproducible MVP repository that answers the RIZM FDE Take-Home Challenge for Henkel's flagship chemical/consumer goods manufacturing site in Dusseldorf-Holthausen.

### 1.1 Challenge Deliverables (from challenge_question.md)

| # | Deliverable | Success Criteria |
|---|-------------|-----------------|
| D1 | Identify data-driven energy business use cases measured in EUR/ton | Grounded in Henkel's current public situation; defensible assumptions |
| D2 | The single most load-bearing data request for the first on-site visit | One request, justified with reasoning |
| D3 | The single most load-bearing stakeholder you need 30 minutes with | One person, justified with reasoning |

### 1.2 Evaluation Philosophy (from challenge_question.md)

- **Method over outcome.** Clean reasoning > correct numbers.
- Every assumption must state *why this one and not another*.
- Toolchain transparency: be explicit about what tools/LLMs/code were used and where.
- A great submission can be short if the reasoning is clean.

---

## 2. Tech Stack (Locked)

| Layer | Tool | Version Constraint | Notes |
|-------|------|--------------------|-------|
| Language | Python | >=3.10 | Via `pyproject.toml` |
| Environment | `uv` | >=0.11 | Cross-platform lockfile via `uv.lock` |
| Optimization | `oemof.solph` | >=0.5.3 | MILP energy system graph definition |
| Solver | HiGHS via `highspy` | >=1.7.0 | Accessed through Pyomo `appsi_highs` SolverFactory |
| Validation | `pydantic` | >=2.0.0 | User configuration schemas and strict data validation |
| Solar Modeling | `pvlib` | >=0.11.0 | Integrated Plane-of-Array irradiance & temperature yield |
| Data | `pandas`, `numpy` | >=2.0.0, >=1.24.0 | DataFrames and numerical computation |
| Visualization | `matplotlib`, `seaborn` | >=3.7.0, >=0.12.0 | Plots in notebook |
| API | `requests` | >=2.31.0 | Open-Meteo & SMARD market API data fetching |
| Spreadsheet IO | `openpyxl` | >=3.1.0 | Excel export if needed |
| Notebook | `jupyter` | >=1.0.0 | Executive deliverable |
| Build | `setuptools` | >=61.0 | Build backend |

> **Rule: No new dependencies may be added without explicit user permission.**

---

## 3. Directory Structure (Canonical)

```
RIZM_challenge_Rafi/
├── .agent/
│   └── skills/                        # Domain skills grounding AI agent behavior
│       ├── python-best-practice.md
│       ├── german-energy-market-specialist.md
│       ├── milp-optimization-engineer.md
│       ├── thermodynamics-exergy-specialist.md
│       └── solution-architect-career-coach.md
├── data/
│   ├── market_data_2025.csv           # Live SMARD API filter 4169 electricity + THE gas prices (hourly 2025, 1yr)
│   ├── solar_data_duesseldorf_2025.csv # Open-Meteo GHI/DNI/DHI + temp (hourly 2025, 1yr)
│   └── components/                    # TOML config files for each asset type
│       ├── pv.toml
│       ├── bess.toml
│       ├── chp.toml
│       ├── eboiler.toml
│       └── hthp.toml
├── ref/                               # Literature references, reports, screenshots
│   ├── StoREN-Phase1_Oeffentlicher_Abschlussbericht.pdf
│   ├── Bolten_et_al_2026_Defossilisation.pdf
│   ├── 2025-annual-report.pdf
│   ├── Screenshot 2026-08-02 at 19.57.06.png
│   └── online_ref.md
├── src/
│   ├── __init__.py
│   ├── external_api.py                # Market & weather data pipeline
│   ├── optimization_model.py          # OOP oemof.solph MILP model & Pydantic config schemas
│   └── utils.py                       # Visualization, plotting & financial summary abstraction
├── scripts/
│   └── build_notebook.py              # Automated notebook generator
├── docs/
│   ├── challenge_question.md          # Original RIZM challenge brief
│   ├── prompt.md                      # Solution planning notes
│   ├── notes.md                       # Working notes and user requirements
│   └── checklist.md                   # Pre-submission checklist
├── challenge.ipynb                    # Main executive notebook deliverable
├── pyproject.toml                     # Project metadata and dependencies
├── uv.lock                            # Universal reproducible lockfile
├── .gitignore
├── README.md                          # Entry point and repo navigation guide
└── SPEC.md                            # THIS FILE -- single source of truth
```

> **Rule: No files or directories may be created outside this structure without proposing a SPEC amendment first.**

---

## 4. Data Schemas

### 4.1 Market Data CSV (`data/market_data_2025.csv`)

| Column | Unit | Description |
|--------|------|-------------|
| index (DatetimeIndex) | UTC+1 hourly | Timestamp |
| `elec_spot_eur_mwh` | EUR/MWh | Day-Ahead electricity spot price |
| `gas_spot_eur_mwh` | EUR/MWh | THE natural gas spot benchmark |
| `co2_tax_eur_mwh_gas` | EUR/MWh | CO2 surcharge on gas combustion |
| `gas_total_eur_mwh` | EUR/MWh | gas_spot + co2_tax |
| `grid_fee_standard_eur_mwh` | EUR/MWh | Standard grid usage fee |
| `grid_fee_sec19_eur_mwh` | EUR/MWh | Reduced fee under sec19 StromNEV |
| `elec_total_standard_eur_mwh` | EUR/MWh | elec_spot + grid_fee_standard |
| `elec_total_sec19_eur_mwh` | EUR/MWh | elec_spot + grid_fee_sec19 |

### 4.2 Solar Data CSV (`data/solar_data_duesseldorf_2025.csv`)

| Column | Unit | Description |
|--------|------|-------------|
| index (DatetimeIndex) | UTC+1 hourly | Timestamp |
| `ghi` | W/m2 | Global Horizontal Irradiance |
| `dni` | W/m2 | Direct Normal Irradiance |
| `dhi` | W/m2 | Diffuse Horizontal Irradiance |
| `temp_air` | deg C | Ambient air temperature |

### 4.3 Component Configuration Files (`data/components/*.toml`) [NEW]

Each asset type gets a TOML config file with real market-sourced specifications that the optimization model will parse. Example schema:

```toml
# data/components/pv.toml
[pv]
model_name = "Generic_Rooftop_Crystalline"
capex_eur_per_kw = 800.0
opex_eur_per_kw_year = 12.0
lifetime_years = 25
degradation_rate_per_year = 0.005
max_capacity_kw = 25000.0  # Rooftop constraint from spatial analysis
```

```toml
# data/components/bess.toml
[bess]
model_name = "Generic_LFP_Container"
capex_eur_per_kwh = 350.0
opex_eur_per_kwh_year = 5.0
lifetime_years = 15
round_trip_efficiency = 0.90
initial_soc = 0.5
max_capacity_kwh = 50000.0
c_rate = 0.5
```

---

## 5. Energy System Architecture

### 5.1 Buses

| Bus Label | Carrier | Unit |
|-----------|---------|------|
| `b_elec` | Electricity | kW |
| `b_gas` | Natural Gas | kW (LHV) |
| `b_steam_ht` | High-Temperature Steam (16 bar, ~200 deg C) | kW_th |
| `b_heat_lt` | Mid/Low-Temperature Process Heat (~80 deg C) | kW_th |

### 5.2 Components (All capacities in kW or kWh)

| Component | Label | Type | Bus In | Bus Out | Key Parameters |
|-----------|-------|------|--------|---------|----------------|
| Grid Electricity | `grid_electricity` | Source | -- | b_elec | variable_costs from market CSV |
| Gas Grid | `grid_gas` | Source | -- | b_gas | variable_costs = gas_spot + CO2_tax |
| Solar PV | `solar_pv` | Source | -- | b_elec | fix=normalized GHI; pvlib integration pending |
| Gas CHP | `gas_chp` | Converter | b_gas | b_elec, b_steam_ht | eta_el=0.40, eta_th=0.45 |
| Gas Boiler | `gas_boiler` | Converter | b_gas | b_steam_ht | eta_th=0.92 |
| Electric Boiler | `electric_boiler` | Converter | b_elec | b_steam_ht | eta_th=0.98 |
| Steam-to-Heat HX | `steam_to_heat_exchanger` | Converter | b_steam_ht | b_heat_lt | eta=0.98 |
| Heat Pump (HTHP) | `heat_pump` | Converter | b_elec | b_heat_lt | COP=2.8 |
| BESS | `bess` | GenericStorage | b_elec | b_elec | eta_in=0.95, eta_out=0.95 |
| TES | `tes` | GenericStorage | b_heat_lt | b_heat_lt | eta_in=0.98, eta_out=0.98, loss_rate=0.005/h |
| Elec Demand | `demand_elec` | Sink | b_elec | -- | 60 MW continuous |
| Steam Demand | `demand_steam` | Sink | b_steam_ht | -- | 160 MW_th continuous |
| Heat Demand | `demand_heat` | Sink | b_heat_lt | -- | 60 MW_th continuous |

### 5.3 Optimization Modes

| Mode | Description | Key Behavior |
|------|-------------|--------------|
| `operation` | Fixed existing asset capacities | Minimize hourly OPEX via dispatch optimization |
| `investment` | Variable capacities for PV, BESS, HTHP, TES | Minimize OPEX + annualized CAPEX (EAC) jointly |

### 5.4 Fermi Estimate Baseline

| Parameter | Value | Source |
|-----------|-------|--------|
| Annual Production | 450,000 tons/year | StoREN DLR / Henkel public data |
| Electrical Baseload | 60 MW_el | StoREN Phase 1 report |
| Thermal Baseload | 220 MW_th (160 HT steam + 60 MT heat) | StoREN Phase 1 report |
| Full-Load Hours | 7,000 h/year (~80% capacity factor) | Industrial chemical site benchmark |
| Gas Tariff (incl. CO2) | 45 EUR/MWh | THE benchmark + EU ETS at 80 EUR/t |
| Electricity Tariff (spot+grid) | 130 EUR/MWh | SMARD 2024 weighted average + grid fees |
| Thermal Energy Intensity | 3.33 MWh_th/ton | Derived: 1,500,000 MWh / 450,000 tons |
| Electrical Energy Intensity | 1.00 MWh_el/ton | Derived: 450,000 MWh / 450,000 tons |
| **Baseline EUR/ton** | **280 EUR/ton** | 150 (thermal) + 130 (electrical) |
| **Annual Energy Cost** | **126,000,000 EUR/year** | 280 * 450,000 |

---

## 6. Execution Phases & Task Breakdown

### Phase 1: Skills Update [STATUS: DONE]

| Task | File(s) | Description |
|------|---------|-------------|
| 1.1 | `.agent/skills/german-energy-market-specialist.md` | Add online reference URLs for validating German energy market assumptions (SMARD, Bundesnetzagentur, sec19 StromNEV legal text) |
| 1.2 | `.agent/skills/milp-optimization-engineer.md` | Add links to oemof.solph docs, example repos, Pyomo best practices |
| 1.3 | `.agent/skills/thermodynamics-exergy-specialist.md` | Add references for COP modeling, heat pump temperature lifts, exergy analysis |
| 1.4 | `.agent/skills/solution-architect-career-coach.md` | Rewrite to focus on first-principles problem decomposition with references to structured thinking frameworks |

### Phase 2: Optimization Model Update [STATUS: TODO]

| Task | File(s) | Description |
|------|---------|-------------|
| 2.1 | `data/components/*.toml` | Create TOML config files with real market specs for PV, BESS, CHP, E-Boiler, HTHP |
| 2.2 | `src/optimization_model.py` | Parse TOML configs instead of hardcoded parameters |
| 2.3 | `src/optimization_model.py` | Accept user-supplied `market_path` and `solar_path` file paths |
| 2.4 | `src/optimization_model.py` | Integrate `pvlib` for PV modeling (replace raw GHI normalization) |
| 2.5 | `src/optimization_model.py` | Add CO2 emission tracking in post-processing (gas grid + electricity grid emission factors; compute tons CO2 avoided) |
| 2.6 | `src/optimization_model.py` | Downgrade sec19 StromNEV from primary feature to one configurable parameter among others (regulation expires ~2028) |
| 2.7 | `src/external_api.py` | Verify `highspy` is properly imported and accessible through `appsi_highs` solver path |

### Phase 2.5: Model Convention Alignment [STATUS: DONE]

| Task | File(s) | Description |
|------|---------|-------------|
| 2.5.1 | `src/optimization_model.py` | Replace `_get_annualized_cost()` with `oemof.tools.economics.annuity()`. WACC stays at 0.07. |
| 2.5.2 | `src/optimization_model.py` | Create Pydantic models for each TOML component config (PVConfig, BESSConfig, CHPConfig, EBoilerConfig, HTHPConfig). Critical fields required; secondary fields keep defaults. Update `load_component_config()` to return validated models. |
| 2.5.3 | `src/optimization_model.py` | Wire `min_capacity` from `ComponentBounds` into oemof `Investment(minimum=...)` for PV, BESS, HTHP, TES. Defaults remain 0.0. |
| 2.5.4 | `src/optimization_model.py` | Switch solve method from `po.SolverFactory('appsi_highs')` to `om.solve(solver='highs', solve_kwargs={'tee': True})`. Remove manual dual/rc hacks. Use `solph.processing.meta_results(om)` for objective. If significantly slower, fall back to `appsi_highs`. |
| 2.5.5 | `src/utils.py` | Add `plot_energy_system_graph(energy_system)` utility using networkx. Add `create_optimization_summary_table(solution_meta)` returning formatted pandas DataFrame. |
| 2.5.6 | `challenge.ipynb` (via `scripts/build_notebook.py`) | Add config schema docs markdown cell, graph visualization cells (both modes), and summary table cells after each solve. |

### Phase 3: Notebook Update [STATUS: TODO]

| Task | File(s) | Description |
|------|---------|-------------|
| 3.1 | `scripts/build_notebook.py` | Remove all emoji characters from notebook markdown cells |
| 3.2 | `scripts/build_notebook.py` | Fix datetime x-axis parsing on all plots (use `matplotlib.dates` formatters) |
| 3.3 | `scripts/build_notebook.py` | Ensure every plot has a visible legend |
| 3.4 | `scripts/build_notebook.py` | Revise Decision Hub narrative (not just sec19-centric; focus on holistic energy cost reduction) |
| 3.5 | `scripts/build_notebook.py` | Regenerate and re-execute `challenge.ipynb` end-to-end |

### Phase 4: Reference Mining [STATUS: TODO]

| Task | File(s) | Description |
|------|---------|-------------|
| 4.1 | `ref/` PDFs | Scan StoREN report and Bolten et al. for existing utility infrastructure data (PV, BESS, CHP, E-Boiler, HTHP capacities) and report findings with page numbers |

### Phase 5: Documentation and Polish [STATUS: TODO]

| Task | File(s) | Description |
|------|---------|-------------|
| 5.1 | `README.md` | Remove emojis; add aerial photo of Henkel site; clean up results table with final verified numbers |
| 5.2 | `README.md` | Ensure repo navigation instructions are accurate to current structure |
| 5.3 | All files | Final review: check data accuracy and intuition per `docs/checklist.md` |
| 5.4 | All files | Verify challenge criteria alignment per `docs/challenge_question.md` |

---

## 7. Coding Standards

1. **Units:** All oemof.solph components use kW (power) and kWh (energy). All market data CSVs use EUR/MWh. Conversion happens at the boundary (divide by 1000 when passing EUR/MWh into model as EUR/kWh).
2. **No Emojis:** No emoji characters anywhere in the repo (code, markdown, notebooks).
3. **Type Hints:** All function signatures must have explicit type annotations.
4. **Function Length:** Individual functions should stay under 40 lines where possible.
5. **Comments:** Inline comments for any non-obvious logic, especially conversion factors, efficiency values, and regulatory references.
6. **Assumptions:** Every hardcoded number (efficiency, cost, capacity) must have a comment or docstring stating its source or reasoning.

---

## 8. Verification Plan

### 8.1 Automated Tests (per-task)

```bash
# Environment reproducibility
uv sync

# Data pipeline
uv run python -m src.external_api

# Operation mode solve (168h sample)
uv run python -c "
import pandas as pd
from src.optimization_model import HenkelEnergySystem
df_m = pd.read_csv('data/market_data_2024.csv', index_col=0, parse_dates=True)
df_s = pd.read_csv('data/solar_data_duesseldorf_2024.csv', index_col=0, parse_dates=True)
hes = HenkelEnergySystem(df_market=df_m, df_solar=df_s, mode='operation')
res = hes.solve(timesteps=168)
print('EUR/ton:', round(res['cost_per_ton_eur'], 2))
"

# Investment mode solve (168h sample)
uv run python -c "
import pandas as pd
from src.optimization_model import HenkelEnergySystem
df_m = pd.read_csv('data/market_data_2024.csv', index_col=0, parse_dates=True)
df_s = pd.read_csv('data/solar_data_duesseldorf_2024.csv', index_col=0, parse_dates=True)
hes = HenkelEnergySystem(df_market=df_m, df_solar=df_s, mode='investment')
res = hes.solve(timesteps=168)
print('EUR/ton:', round(res['cost_per_ton_eur'], 2))
caps = hes.get_investment_capacities()
print('Capacities:', caps)
"

# Notebook end-to-end execution
uv run jupyter nbconvert --to notebook --execute challenge.ipynb --output challenge_executed.ipynb
```

### 8.2 Manual Verification (per docs/checklist.md)

1. Check data accuracy and intuition: do the numbers look right?
2. Check RIZM criteria alignment: does the submission answer D1, D2, D3?
3. Verify no emojis remain in any file.
4. Verify all plots have legends and clean datetime x-axes.

---

## 9. Execution Order

Tasks MUST be executed in this order (matching the TODO list in notes.md):

1. **Phase 1** -- Skills update (Tasks 1.1-1.4)
2. **Phase 2** -- Optimization model update (Tasks 2.1-2.7)
3. **Phase 2.5** -- Model convention alignment (Tasks 2.5.1-2.5.6)
4. **Phase 3** -- Notebook update (Tasks 3.1-3.5)
5. **Phase 4** -- Reference mining (Task 4.1)
6. **Phase 5** -- Documentation and polish (Tasks 5.1-5.4)

> **Rule: Do not start a later phase until all tasks in the current phase pass verification.**
