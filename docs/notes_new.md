# PyPSA refactor 

## TODO:
1. Refactor the SPEC.md and uv.lock such that this branch moves from oemof.solph optimization approach to PyPSA-based optimization approach
2. Transform the util.py functions to adapt with the new refactor. Use .agent/skills/pypsa-reporting to identify which method is best to report the result in challenge.ipynb
3. Retain all the OOP structure, config-based ideology, and simply switch the energy system modelling from oemof.solph to PyPSA. For this transfer, based your judgement on pypsa skills that are just transfered to this repo skills 
4. I want to adopt a OOP based class abstraction for all the build components into its individual module on src/components in a python devops best practice way that is then abstracted from the main model module src/optimization_model.py
5. Create a solid plan divided into phases to implement this refactor efficiently and on target while following the spec-driven convention rules of this repo .agents/rules/spec-driven-engineering.md
6. The challenge.ipynb should still have the same structure in a way that it first introduces the challenge with the md cell, then it starts the baseline calculation with fermi estimation and market data in a python cell, and then it starts with the operation_hub solution introduction and decision_hub solution introduction while maintanining the config-based, API first structure and present the solution with plots and visualitaion from utils that is based on intuition of .agent/skills/pypsa-asset-economics. Lastly, it addresses the second challenge question that complements or answers question of how the first challenge with operation and decision hub can be improved by meeting with the stakeholder from Henkel
7. Update the README.md after the refactor 


## Questions
- 
