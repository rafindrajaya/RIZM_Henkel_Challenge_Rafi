# MISSION BRIEF 

## Role Definition
You are acting as an elite Solution engineer at RIZM. Your objective is to build a production-grade, modular, reproducible MVP repository and decision framework for Henkel’s flagship chemical/consumer products manufacturing site in Düsseldorf-Holthausen.

---

## ITERATIVE REPO BUILD ROADMAP

Execute this mission in strictly ordered, step-by-step phases. Validate completion after each phase before proceeding.

### PHASE 1: REPOSITORY SCAFFOLDING & DEPENDENCY MANAGEMENT
Establish an environment managed via `uv` with cross-platform lockfiles.

1. **Repository Structure:**
   ├── .agent/
   │   └── skills/                  # Custom domain skills for Antigravity AI Agent
   │       ├── python-best-practice.md
   │       ├── german-energy-market-specialist.md
   │       ├── milp-optimization-engineer.md
   │       ├── thermodynamics-exergy-specialist.md
   │       └── solution-architect-career-coach.md
   ├── data/                      # Input profiles, time-series, component model config (pv, bess, chp, industrial heat pump, TES) 
   ├── ref/                         # Literature references, legal texts (§ 19 StromNEV), Henkel reports, google earth data, screenshots, etc
   ├── src/
   │   ├── __init__.py
   │   ├── external_api.py          # Market & weather API connectors (ENTSO-E, SMARD, Open-Meteo)
   │   └── optimization_model.py   # oemof.solph MILP graph definition & execution engine
   ├── challenge.ipynb              # Main narrative notebook & executive deliverable
   ├── pyproject.toml               # Modern Python project configuration
   ├── uv.lock                      # Universal lockfile
   └── README.md                    # Project entry point & architectural narrative

2. **Dependencies (`pyproject.toml`):**
   - `oemof.solph` (MILP modeling for energy systems)
   - `pvlib` (Rooftop PV irradiance and solar power generation)
   - `pandas`, `numpy` (Data manipulation & numerical handling)
   - `matplotlib`, `seaborn` (Visualizations & dynamic heatmaps)
   - `requests`, `openpyxl` (Data pipelines & API communication)
   - Solver: HiGHS via highspy

---

### PHASE 2: DOMAIN SKILLS REGISTRY (`.agent/skills/`)
Generate the 5 domain skill files specified in Phase 1 to ground all code generation in domain-specific best practices. For solution architect expert, include explicitly this ideology below:

Core Principles: 
1. **Method Over Outcome:** Clear, explicit mathematical and thermodynamic assumptions outweigh synthetic precision. Document *why* every choice was made and *why* alternatives were excluded.
2. **Direct Metric Translation:** Every energy optimization output MUST be translated into €/ton of industrial output.
3. **Clean Software Engineering:** Modern Python standard (`pyproject.toml`), environment reproducibility via `uv`, modular architecture separating IO from optimization, type hinting, and clear documentation.

---

### PHASE 3: CORE LIBRARY IMPLEMENTATION (`src/`)
1. **`src/external_api.py`:**
   - Fetch real-world German wholesale electricity market prices via ENTSO-E / SMARD (Day-Ahead & 15-min Intraday Continuous).
   - Fetch natural gas hub prices (THE - Trading Hub Europe proxy).
   - Fetch weather/irradiance data for Düsseldorf (`51°10'41.86"N 6°50'40.25"E`) via Open-Meteo API for `pvlib` simulation.
   - I want a configurable module that allows me to choose what data I want to retrieve, what year, what I want to name the output 
   - Save the retrieved data in /data folder 
2. **`src/optimization_model.py`:**
   - Create a configurable abstraction and Object Oriented Programming (OOP) logic in modelling `oemof.solph`.
   - **Buses:** `b_elec` (Electricity), `b_gas` (Natural Gas), `b_heat`
   - **Sources:** Electricity Grid (dynamic time-series pricing, input from the retrieved data from api call), Gas Grid (fuel + CO2 tax index), PV Array (`pvlib` profile).
   - **Converters:** Gas CHP, Electric Boiler (Power-to-Heat), High-Temperature Industrial Heat Pump (waste heat recovery).
   - **Storage:** Thermal Energy Storage (Steam buffer/TES), Battery Energy Storage System (BESS).
   - **Sinks:** Process Electrical Load, Process Heat Demand (tied to €/ton production output).
   - Support both **Operational Mode** (fixed dispatch optimization) and **Investment Mode** (sizing PV, BESS, and Heat Pumps).
   - Model definition and objective function should be based on the optimization objective 

---

### PHASE 4: EXECUTIVE NOTEBOOK DELIVERABLE (`challenge.ipynb`)
Structure `challenge.ipynb` with clear Markdown narrative, code cells, data analysis, and visual plots:
- **Cell 1:** General Markdown walkthrough of how I am approaching this challenge
- **Cell 2:** Baseline Fermi Estimate & €/ton Cost Baseline derivation.
- **Cell 3:** Technical Config Cell (selecting enabled assets, price signals, solver options).
- **Cell 4:** Operation Hub Optimization Run (MILP dispatch on existing infrastructure, spot arbitrage, §19 StromNEV peak shaving, rolling horizon explanation).
- **Cell 5:** Operation Hub Data Analysis (timeseries analysis showing how optimization results in promoting flexibility and load shifting)
- **Cell 6:** Decision Hub Config & Investment Run (spatial analysis of Düsseldorf roof space, joint sizing & dispatch of PV, BESS, Heat Pump).
- **Cell 7:** Decision Hub Data Analysis & CAPEX Payback Breakdown.
- **Cell 8:** Dynamic Sensitivity & "What-If" Matrix (Gas/Power price ratio, CO2 pricing, grid fees).
- **Cell 9:** Strategic On-Site Protocol for Henkel Düsseldorf (Data Request & 30-Min Stakeholder Agenda).

#### IMPORTANT:
1. Make sure that every assumption is defensible and backed by logical reasoning
2. Elaborate why this assumption is chosen instead of another

---

### PHASE 5: DOCUMENTATION & SUBMISSION PACKAGE (`README.md` & `ref/`)
Produce a comprehensive `README.md` explaining repo navigation, mathematical & tool choices, and business impact to Henkel.


### Fermi Estimate

Baseline Thermal and Electrical DemandsEngineering evaluations of the Holthausen site—such as the joint StoREN industrial decarbonization study conducted by Henkel, BASF, and the German Aerospace Center (DLR)—indicate that baseline industrial operations require a minimum continuous thermal capacity of 220 MW thermal ($MW_{th}$) and a minimum electrical capacity of 60 MW electrical ($MW_{el}$).

Assuming around 80% continuous full load capacity
Elec energy= 60 MW * 7000 h = 420,000 MWh
Thermal energy= 220 MW * 7000 h = 1,540,000 MWh

Thermal Energy per ton= 
1,500,000 MWh/450,000 tons = 3.33333333333 MWh thermal / ton

Electric Energy per ton= 
450,000 MWh/450,000 tons = 1 MWh elec / ton

Weighted average energy tariffs:

- Average Natural Gas + CO2 Tax (€80/t) Cost ($C_{\text{gas}}$): €45 / MWh (€0.045 / kWh).

- Average Spot + Grid + Tax Electricity Cost ($C_{\text{elec}}$): €130 / MWh (€0.13 / kWh).

Baseline Thermal cost: 3.33333333333 MWh thermal / ton * €45 / MWh = 150 euro / ton 
Baseline electricity cost: 1 MWh elec / ton * €130 / MWh = 130 euro / ton
Total energy cost = 280 euro / ton 
Total annual cost = 280 * 450,000 = 126,000,000 Euro / year electricity cost

### Post Scaffolding Notes
1. PV lib is not being used to model the PV yet
2. I want to pupulate data with specs of each available component based on real market data written as .toml file, this will be then the config that will be parsed into the optimization model:
   - PV: Model name, CAPEX (EUR/MW), OPEX, some other parameters that can be an input for oemof PV model paired with pv lib
   - BESS: CAPEX, OPEX, round-tripefficiency, initial SOC, other configurable parameters based on market sheet
   And same for the other available components:
      - E-boiler: 
      - CHP
      - HTTP

3. What is the unit of the sink nominal capacity?
4. I want to change the decision hub solution narrative
5. I want to remove any emojis used in this repo
6. §19 StromNEV Grid Fee Protection should not be the highlight of the solution. It is only part of the equation, especially since this regulation is about to end soon I heard in 2028 or something
7. I thought using high solver has to involve import highspy, where is that located?
8. From the available ref in the ref folder, try to find any report on existing utility infrastructure such as PV, BESS, e-boiler, CHP, industrial heat pumps and report to me any findings if any, their capacity if any, and which page the information could be found from the pdf. 
9. Model the emission factor for the gas grid as well. Record also in the post processing function the amount of CO2 avoided from the optimization from both CO2 avoided from elec and gas grid.
10. Fix date parsing for all the plots in challenge.ipynb. Now the x axis label is just messy because the datetime is not parsed correctly
11. Display legend for each visualization in the challenge.ipynb
12. I want to be able to input myself the market and solar path of the energy system
13. Improve the skills with online references for each agent
   - German market specialist: refer to online references when ask to validate some assumption regarding to energy market data
   - MILP optimization engineer: refer to online references or public repository to acquire skills of best practice in modelling in oemof.solph, pyomo, etc
   - Thermodynamics exergy specialist: refer to online references or public repository to acquire skills of best practice in modelling in linear energy system to accurately model the thermodynamics efficinetly
   - Fix the solution architect career coach to refer to online references or public repository of how to address a problem or challenge with a first principle mindset that exactly identifies the main challenge or problem, and provide solution that hits all the crucial points
