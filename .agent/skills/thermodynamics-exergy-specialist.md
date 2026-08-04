# Thermodynamics & Exergy Specialist Skill

## Purpose

Ground all thermal modeling decisions in physical thermodynamic constraints.
When choosing efficiency values, COP assumptions, or temperature tiers, consult the rules and references below.

## Physical Grounding Rules

1. **Temperature Quality Tiers:**
   - **Steam Grade (16 bar / 180-200 deg C):** Requires gas-fired boilers or Combined Heat & Power (CHP). Standard compression heat pumps cannot reach these temperatures economically. Only specialized multi-stage or cascade systems (e.g. SteamHP by SPH) reach >150 deg C, and these are still pre-commercial at scale.
   - **Process Heat (60-110 deg C):** Ideal for High-Temperature Industrial Heat Pumps (HTHP) recovering waste heat from cooling circuits (30-40 deg C source). Commercially available from suppliers like MAN Energy Solutions, Siemens, Vattenfall.
   - **Why two thermal buses?** Mixing steam and low-grade heat into one bus would overestimate heat pump contribution and underestimate gas consumption. The exergy penalty of serving 200 deg C demand with a COP-2.8 device designed for 80 deg C output makes the physics nonsensical.

2. **Coefficient of Performance (COP) Modeling:**
   - For a linear energy system model, use a fixed COP as a reasonable approximation when the temperature lift is constant. A COP of 2.8 is defensible for an HTHP with:
     - Source temperature: 35 deg C (industrial cooling water)
     - Supply temperature: 80 deg C
     - Carnot COP at these temps: 80+273 / (80-35) = 7.84
     - Second-law efficiency (eta_ex) of 0.35-0.40: practical COP = 7.84 * 0.36 = 2.8
   - If the model is extended to variable temperatures, COP should scale as:
     COP = eta_ex * T_supply / (T_supply - T_source)
   - Document the chosen COP value and its derivation in any notebook cell that uses it.

3. **Storage Losses & Round-Trip Efficiency:**
   - **Thermal Energy Storage (TES):** Loss rate of 0.5% per hour (0.005/h) for well-insulated hot water tanks. This is conservative; stratified tanks can achieve 0.1-0.3%/h.
   - **Battery Storage (BESS):** Round-trip efficiency of ~90% (eta_in=0.95, eta_out=0.95). Self-discharge loss rate of 0.01%/h.
   - Always state the loss rate assumption and whether it represents a best-case or conservative estimate.

4. **Gas Combustion Emission Factor:**
   - Natural gas: 0.201 tCO2/MWh_th (based on LHV). Source: IPCC 2006 Guidelines, Table 2.2.
   - This factor applies to the thermal energy content of the gas input, not the useful heat output. When computing emissions from a boiler with eta=0.92, the gas input per MWh_th of useful heat is 1/0.92 = 1.087 MWh_gas, so emissions = 1.087 * 0.201 = 0.218 tCO2/MWh_th_useful.

## Online References

| Topic | URL | What it provides |
|-------|-----|-----------------|
| IEA Heat Pump Technology Annex | https://heatpumpingtechnologies.org/ | Industrial heat pump technology status, COP benchmarks, case studies |
| DLR StoREN Project | https://www.dlr.de/en/research-and-transfer/projects-and-missions/storen | Public summary of the Henkel/BASF/DLR industrial decarbonization study |
| IPCC Emission Factors (Ch.2) | https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html | Stationary combustion emission factors for natural gas |
| Danish Energy Agency Technology Data | https://ens.dk/en/our-services/projections-and-models/technology-data | Comprehensive cost and performance data for energy technologies (boilers, CHP, heat pumps, storage) |
| oemof-thermal Heat Pump | https://github.com/oemof/oemof-thermal | COP calculation helpers and heat pump modeling for oemof |
| Exergy Analysis Fundamentals | https://web.mit.edu/2.006/www/ | MIT OpenCourseWare on thermodynamics and exergy |
