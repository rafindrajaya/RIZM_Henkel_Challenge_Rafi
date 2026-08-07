# PyPSA refactor 

## TODO:
1. Refactor the SPEC.md and uv.lock such that this branch moves from oemof.solph optimization approach to PyPSA-based optimization approach
2. Transform the util.py functions to adapt with the new refactor. Use .agent/skills/pypsa-reporting to identify which method is best to report the result in challenge.ipynb
3. Retain all the OOP structure, config-based ideology, and simply switch the energy system modelling from oemof.solph to PyPSA. For this transfer, based your judgement on pypsa skills that are just transfered to this repo skills 
4. I want to adopt a OOP based class abstraction for all the build components into its individual module on src/components in a python devops best practice way that is then abstracted from the main model module src/optimization_model.py
5. Create a solid plan divided into phases to implement this refactor efficiently and on target while following the spec-driven convention rules of this repo .agents/rules/spec-driven-engineering.md
6. The challenge.ipynb should still have the same structure in a way that it first introduces the challenge with the md cell, then it starts the baseline calculation with fermi estimation and market data in a python cell, and then it starts with the operation_hub solution introduction and decision_hub solution introduction while maintanining the config-based, API first structure and present the solution with plots and visualitaion from utils that is based on intuition of .agent/skills/pypsa-asset-economics. Lastly, it addresses the second challenge question that complements or answers question of how the first challenge with operation and decision hub can be improved by meeting with the stakeholder from Henkel
7. Update the README.md after the refactor 


## DONE
- Move the pvlib pv yield function to pvcomponent class for better visibility and code structure (DONE)
- Validate the data/components with .agent/skills/pypsa-asset-economics (DONE)
- Create PV PPA and Wind PPA classes in grid.py module, profile generators in external_api.py, and integrate with Pydantic configs in optimization_model.py (DONE)
- Is there a way to visualize the topology with PyPSA built in tools?
- The n.explore visualization for investment hub should be after solve because this is when all the final components are instatiated

## TODO 2:

- Remove the fermi baseline calculation and just compare operation hub with existing compoenents and decision hub that includes the option of investing in battery, PPA PV, PPA Wind, TES


## challenge.ipynb structure change (challenge.ipynb)
- Initialize the operation hub with all the components 
- The second challenge question should then answer what we need from stakeholder so that the operation hub and investment hub solution can be even more defensible business case with the actual energy consumption load for different carriers at differet temperature level for the heat


## Questions
- 


### Notes on content

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
- Add the aerial view from google earth of the empty lots on the big building in Dusseldorf site
- Create a UML class diagarm in docs and sequence diagram or other insightful diagram in the readme.md using mermaid

### Not urgent
- - CHP FixedSizingConfig should only just be one value of the the combined heat and power sizing that is then get separated into the COP of elec and heat. For instance, if the fixed sizing is 50 MW, then 
- Is there a way to simulate load flexibility that should always be above 80% demand capacity in PyPSA for all the designed demands?
- Create a CI test that checks whether both the operation hub and decision hub framework can converge optimally under different sizing configuration for a 1 week operation and that the result is not multiple magnitude off from the range of possible results