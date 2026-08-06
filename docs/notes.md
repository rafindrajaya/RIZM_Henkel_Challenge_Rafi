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
14. Add a aerial photo of Henkel on the README.md

### TODO list:
1. Clean up rafindrajaya repo
2. Push this local repo to public repo in rafindrajaya account (Done)
3. Learn the best practice how to make an MVP using agentic AI that is sustainable and effective
   - I want to be able to still fully understand the code structure
   - I want the most important architecture to be implemented and translated correctly
   - I want the most important functionality to be addressed correctly
4. Do the notes changes in this order below:
- Skills update
- Optimization model opdate
- Jupiter notebook update

### Notes
1. create a utils.py for any printing and plotting visualization abstraction
2. Create a solid outline of how the jupiternotebook should look like step by step, section by section
3. Make sure that the Jupyternotebook already integrates the latest data and components implemented in phase 2 
4. Make sure and confirm that my assumption has a referencing backing: Yearly production qtty, elec and therm consump. qtty.
5. Use mermaid to show how I approach this challenge step by step and attach it in README.md 


What I want for challenge.ipynb:
- I want to create a utils.py in /src for any printing and plotting visualization abstraction so that in the challenge.ipynb, there is no more messy syntaxes for visualization
- I like the first intro executive summary already
- First code section should be just importing all the necessary libraries, APIs, classes as it already is right now. Move the visualization style parameters to utils.py and verify solver installation part to optimization_mode.py
- I like the fermi estimate calculation part. I want the german-energy-market-specialist agent to check if the number makes sense based on the resources online. Is 139 M euro per year for 450,000 ton products logical?
- I want to use pydantic features so that if type of object is fixed with it and any missmatch will be automatically fixed
- With the current system definition, does it make sense to split the heat levels into two? since the component of the Henkel factory is not explicitly modelled, what is the use for splitting the heat levels? I would not be able to do some heat recovery modelling, right?
- I want the user config section code to look like below: 
project_name = current_facility_optimization #with pydantic this will be turned into string right? #the project name will be used as the name of the energy system of oemof.solph
optimization_mode = #operation_hub or decision_hub
start_time = #DD/MM/YYYY format
end_time = #DD/MM/YYYY format

The sizing config below is then saved to a specific energy system definition that is represent by project_name
fixed_components_sizing = #Dictionary
{"pv": XX, #kW
"bess": XX, #kWh
"hthp": XX, #kW_th
"tes": XX #kWh_th}

variable_components_sizing = #Dictionary
{"pv": true or false, min= , max=      #kW
"bess": true or false, min= , max=     #kWh
"hthp": true or false, min= , max=     #kW_th
"tes": true or false, min= , max=      #kWh_t }

This user config will be placed once before the operation hub solution and the optimization hub solution

- In the analysis of operation hub solution, I would like to brainstorm with .agent/skills/solution-architect-career-coach.md and .agent/skills/milp-optimization-engineer.md agent skills, what is best to show in comparison to the estimated baseline of full elec and gas grid reliance. What I have in mind currently is the following:
   - Four subplots of 1 week representative operation in different months or season of how the operation_hub optimizes operation dispatch by ramping up consumption when the price is negative #This should be ones of the function defined in utils.py that can easily be used
   - Bar chart showing the baseline energy cost per ton and the new energy cost per ton #plotting function should also be defined in utils.py

- In the analysis of decision hub solution, I would like to brainstorm with .agent/skills/solution-architect-career-coach.md and .agent/skills/milp-optimization-engineer.md agent skills, what is best to show in comparison to the estimated baseline and operation hub solution:
   - Tables that summarizes the oemof.solph objective translated into meaningful metrics: #table creation should also be abstracted in utils.py
      - Table 1 economics metrics: CAPEX, OPEX, NPV, CO2 emission reduced (based on the reduced grid consumption), IRR, Payback Period, resulting energy cost per ton product
      - Table 2 sizing results : all the component result sizing
   - Bar chart showing the baseline, operation hub, and decision hub energy cost per ton  #plotting function should also be defined in utils.py



### Notes 5 August

- Explain why this approach is chosen and why this extent of abstraction (why not more or less)
- Elaborate the process of tackling this challenge (mermaid diagram w/ extra brief note the importance of each step according to my perspective) ->in README.md
1. Business analysis and data collection
To get a sense of the line of business, energy consumption, & magnitude
2. Idea brainstorming and Goals elaboration 
To land on an impactful solution with clear goal with current estimation
3. Spec engineering and system abstraction creation
Spec engineering for Spec-driven Development was done to set a ground truth when working with agentic AI to set a clear foundation of what tools to be used and to what end. The abstraction creation is system design thinking to ensure clean architechture best practice while avoiding too much abstraction for this specific challenge purpose.
4. Setting up skills, rules, and loops for agentic AI
To add an extra layer of capabilities to the AI to based its reasoning on clear resources specifically for different technical purposes and to validat and correct when I make a mistake: Energy market specialist, MILP specialist, Thernomdynamics specialist, Python best practice, etc
5. Implementation, Review, Iteration
For every details written in the spec sheet, multiple phases each with predefined tasks are generated. It is important to review, fix, and iterate for each of the phase in order to make sure goal is met and codebase remain managable
6. Final Validation
Final testing of logical accuracy, reasoning, and deliveries of the challenge deliverables

Notes challenge.ipynb: 
- For the operation hub, the set fixed_components_sizing CAPEX should not be accounted into the total cost since it is an existing sizing component
- plot_seasonal_dispatch_subplots() got an unexpected keyword argument 'df_op_flows_full' I got this error because I ran the optimization only for 1 week. I guess this function should be modular or flexible such that it plots just for the entirety of the start_time and end_time as an interactive plot where user can zoom in and zoom out, activate or deactivate a plot or legend,
- The optimization ran 23.9 seconds for a 1 week operationhub optimization which is too long condidering the short timestep windonw. Brainstorm with the MILP agent what we can do to improve the computation time? Is there modelling fixed that can make computation time more efficient or is there other computational overhead that is a bottleneck?
- The timestep of the solve should be based on the config start_time and end_time, basically counting how many hours in between the two calendar

Notes 6 August:
- I think PV profile is still bad. Check the profile creation function again. 
- Implement the changes in readme and challenge.ipynb
- Make sure the investment and operation mode point to the same definition of the model
- If the change to oemof convention solph results in a way longer computational time, fallback to the appsihighs approach
- Update the status of SPEC.md at the end to become 'done'
- Baseline calculation should be done in python code with a high level explanation in the markdown cell above it. 


- For each of the config being initialized as an es = solph.EnergySystem(timeindex=timeindex, infer_last_interval=False) (op_config or inv_config), the es object should only build the components listed in the fixed_components_sizing: Any = ...,variable_components_sizing: Any = ..., and also only build buses that are attached to them, the other components or buses that are not mentioned or attached, don't include, except grid!
- Use import oemof_visio as vis in replacement to  import networkx as nx in the existing plot_energy_system_graph
from oemof.solph import Results
Get results from your solved model
results = Results(model)
Extract flows connected to a specific bus (e.g., electricity bus)
electricity_bus_results = results.get((bel, None))
Create I/O balance plots using oemof-visio helpers
my_plot = vis.Plot(electricity_bus_results)
my_plot.draw()
- eta_op = hes_op.solve(timesteps=168), why is the timesteps here still elaborated as integer? I thought it is already the number of hours in between end_time and start_time in the config? 
- What if I want to add another pv on top of an existing pv? is there a way to do this efficiently and best practice? if possible I would want to add a the existing pv as fixed and also simulate adding more pv as the variable component sizing. The same applies to other components. 



Some changes and updates that I want to plan (DONE):
   - ep_cost calculation change from  def _get_annualized_cost(self, capex_per_unit: float, lifetime_years: int) -> float: to the built in oemof.solph one. Make sure to use the config file for the inputs of the function. 
capex = 1000  # investment cost
lifetime = 20  # life expectancy
wacc = 0.05  # weighted average of capital cost
epc = capex * (wacc * (1 + wacc) ** lifetime) / ((1 + wacc) ** lifetime - 1)
from oemof.tools import economics
epc = economics.annuity(1000, 20, 0.05)
   - The minimum should be defined and retrieved from the config, same for other components. I dont see the minimum_capacity being used in the VariableSizingConfig(BaseModel) yet in the challenge.ipynb. I also want to write a clear documentation on how to set up the config in the challenge.ipynb
   - Use the oemof.solph convention to solving an energysystem
   om = solph.Model(my_energysystem)
results = om.solve(solver="cbc", solve_kwargs={"tee": True}) #instead of cbc, use Highs by import highspy at the top of optimization_mode.py
   - Add one cell before the solving part of both operation and investment of plotting the energy system like below in the challenge.ipynb
   # %%[graph_plotting]
plt.figure()
graph = energy_system.to_networkx()
nx.draw(graph, with_labels=True, font_size=8)

   - Can I use this to get the results overview
   tce = results["objective"]? is this a built in oemof.solph tool? can I use it to show the summary of the optimization results in y challenge.ipynb?
   - For all the get functions to retrieve data from either config or result, instead of falling back to default value if problem occurs, raise an error instead with a warning so that user knows what is wrong and don't get a fake result. 

Future update:
1. Make grid also configurable
2. Create different classes in different modules for each component. Make the build function modular