# German Energy Market Specialist Skill

## Purpose

Ground all energy market assumptions in verifiable German regulatory and market data.
When asked to validate a price, tariff, or regulatory claim, consult the references below before answering.

## Market Rules & Tariff Structure

1. **Wholesale Power Markets (SMARD / ENTSO-E):**
   - Day-Ahead Spot Auction (hourly / 15-min price signals).
   - Intraday Continuous Market (15-min resolution, key for short-term renewable balancing).
   - 2024 German Day-Ahead base price averaged ~75-95 EUR/MWh depending on season.
2. **Natural Gas & Carbon Taxes:**
   - Trading Hub Europe (THE) gas benchmark (~35-45 EUR/MWh in 2024).
   - EU ETS Carbon Price (80-120 EUR/ton CO2) added to natural gas combustion emission factors (0.201 tCO2/MWh_gas).
   - German national CO2 surcharge (BEHG) at 45 EUR/ton CO2 for heating fuels (separate from EU ETS for industrial sites).
3. **Grid Fee Regulations (sec 19 Abs. 2 StromNEV):**
   - **Individuelle Netzentgelte:** >7,000 full-load operating hours/year AND >10 GWh annual consumption unlocks an 80-90% discount on grid usage fees (Netzentgelte).
   - **Atypische Netznutzung:** Load shifting away from distribution system operator (DSO) peak load windows.
   - **Important context:** This regulation is under political review and may be reformed or phased out around 2028. It should be modeled as one configurable parameter among others, not the centerpiece of the solution.
4. **Electricity Grid Emission Factor (Germany):**
   - Average grid emission factor for Germany: ~0.35-0.40 tCO2/MWh_el (declining yearly with renewables expansion).
   - Source: Umweltbundesamt annual publication.

## Online References

Use these to validate assumptions when uncertain:

| Topic | URL | What it provides |
|-------|-----|-----------------|
| SMARD Electricity Market Data | https://www.smard.de/home | Real-time and historical German wholesale electricity prices (Day-Ahead, Intraday) |
| Bundesnetzagentur Monitoring Report | https://www.bundesnetzagentur.de/monitoringberichte | Annual report on German energy market conditions, grid fees, and network tariffs |
| sec 19 StromNEV Legal Text | https://www.gesetze-im-internet.de/stromnev/__19.html | Full legal text of the individual grid fee reduction regulation |
| Trading Hub Europe (THE) | https://www.tradinghub.eu/ | German gas market hub -- reference prices and market reports |
| EU ETS Carbon Price | https://www.eex.com/en/market-data/environmental-markets | European Energy Exchange -- live and historical EU Allowance (EUA) prices |
| BEHG CO2 Surcharge | https://www.dehst.de/EN/national-emissions-trading | German national CO2 pricing under BEHG for heating fuels |
| Umweltbundesamt Emission Factors | https://www.umweltbundesamt.de/en/topics/climate-energy/renewable-energies | Grid electricity emission factors for Germany |
| ENTSO-E Transparency Platform | https://transparency.entsoe.eu/ | Pan-European power system data (generation, cross-border flows, prices) |
