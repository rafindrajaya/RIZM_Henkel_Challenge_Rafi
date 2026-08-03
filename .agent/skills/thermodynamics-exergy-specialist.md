# Thermodynamics & Exergy Specialist Skill

## Physical Grounding Rules
1. **Temperature Quality Tiers:**
   - Steam Grade (16 bar / 180–200°C): Requires Gas Boiler or Combined Heat & Power (CHP). Cannot be served by standard heat pumps without specialized multi-stage high-temperature refrigeration.
   - Process Heat (60–110°C): Ideal for High-Temperature Industrial Heat Pumps (HTHP) with COP ~2.8–3.2 recovering industrial waste heat (e.g. cooling water at 30–40°C).
2. **Coefficient of Performance (COP) Scaling:**
   - Model Heat Pump COP dynamically or with realistic Carnot exergy efficiency $\eta_{ex} \approx 0.45–0.50$:
     $$\text{COP} = \eta_{ex} \times \frac{T_{supply}}{T_{supply} - T_{source}}$$
3. **Storage Losses & Thermal Energy Storage (TES):**
   - Thermal storage loses energy over time ($\text{loss\_rate} \approx 0.005 / \text{hour}$).
   - Battery Storage (BESS) round-trip efficiency (RTE) set to ~90–92% ($\eta_{in}=0.95, \eta_{out}=0.95$).
