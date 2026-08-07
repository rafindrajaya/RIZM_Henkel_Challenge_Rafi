# Component Configuration & PyPSA Model Audit Report

> **Date:** August 7, 2026  
> **Status:** Completed  
> **Skills Referenced:** `pypsa-asset-economics`, `pypsa-market-design`

---

## 1. Executive Summary

This report documents the systematic audit and validation of the component configurations in `data/components/*.toml` and their corresponding OOP PyPSA model implementations in `src/components/` and `src/optimization_model.py`.

The evaluation covers two core PyPSA modeling frameworks:
1. **PyPSA Asset Economics:** Verification of capital expenditure (CAPEX), annualized annuity factors (EAC), fixed/variable O&M, degradation/cycling wear costs, wholesale price vs. tariff/tax/levy additions, and potential foresight/merchant biases.
2. **PyPSA Market Design:** Verification of bus topology, sector-coupled thermal quality levels (High-Temp Steam vs. Mid-Temp Heat), marginal price/dual formation, and wholesale/grid import price mechanics.

---

## 2. Component-by-Component Validation Summary

| Component | TOML Spec File | Key Technical & Economic Parameters | Asset Economics Assessment | Market Design Assessment |
|---|---|---|---|---|
| **Rooftop Solar PV** | `data/components/pv.toml` | • CAPEX: 800 €/kWp<br>• OPEX: 12 €/kWp/yr (1.5%)<br>• Lifetime: 25 yrs<br>• Max Cap: 25 MWp<br>• Degradation: 0.5%/yr | Standard 2024 DE rooftop benchmark (Fraunhofer ISE / DEA). Annuity factor calculated with site WACC (7%). | Connects to `b_elec` with normalized yield profile ($p_{\max,pu}$) computed via `pvlib` Hay-Davies POA model. |
| **Battery Storage (BESS)** | `data/components/bess.toml` | • CAPEX: 350 €/kWh<br>• OPEX: 5 €/kWh/yr<br>• Lifetime: 15 yrs<br>• RTE: 90% ($\eta_{ch}=95\%, \eta_{dis}=95\%$)<br>• Self-discharge: 0.01%/h | 2024 containerized LFP battery benchmark (BNEF). Perfect foresight bias caveat (~10-30% revenue overstatement) noted. | Decoupled PyPSA `Store` + 2 `Link` objects (charger & discharger) connected to `b_elec`. |
| **Combined Heat & Power (CHP)** | `data/components/chp.toml` | • Ref CAPEX: 1,200 €/kW_el<br>• Fixed OPEX: 25 €/kW_el/yr<br>• $\eta_{el}=40\%$, $\eta_{th}=45\%$<br>• Capacity: 40 MW_el, 45 MW_th | Represents existing legacy CHP unit at Holthausen site (sunk CAPEX in operation mode). Fuel utilization = 85%. | 2-output PyPSA `Link` (`b_gas` $\rightarrow$ `b_elec` + `b_steam_ht`). Correct energy balance dual participation. |
| **Electric Boiler** | `data/components/eboiler.toml` | • CAPEX: 100 €/kW_th<br>• OPEX: 2 €/kW_th/yr<br>• Lifetime: 20 yrs<br>• $\eta_{th}=98\%$<br>• Capacity: 30 MW_th | Industrial high-voltage electrode boiler specs (DEA 2024). Low CAPEX Power-to-Heat driver. | PyPSA `Link` (`b_elec` $\rightarrow$ `b_steam_ht`). Converts surplus renewable/low-spot electricity to high-temp steam. |
| **High-Temp Heat Pump (HTHP)** | `data/components/hthp.toml` | • CAPEX: 600 €/kW_th<br>• OPEX: 10 €/kW_th/yr<br>• Lifetime: 20 yrs<br>• COP: 2.8<br>• Source: 35°C, Supply: 80°C | Derivation based on Carnot COP (7.84) and second-law exergy efficiency ($\eta_{ex}=0.36$). | PyPSA `Link` (`b_elec` $\rightarrow$ `b_heat_lt`). Directly supplies mid-temperature process heat bus. |

---

## 3. Deep-Dive Audit Against `pypsa-asset-economics`

### 3.1 Bias Analysis
1. **Bias 1 — Perfect Foresight:**
   - **Observation:** Optimization is executed deterministically over full horizon (168h to 8760h) with complete price & solar availability visibility.
   - **Impact:** Storage dispatch (BESS and TES) represents an upper bound on economic value (~10–30% higher arbitrage revenue than real-time rolling-horizon dispatch).
   - **Action:** Clearly state perfect foresight assumption in notebook deliverables and executive summaries.

2. **Bias 2 — System vs. Merchant Optimization:**
   - **Observation:** The model optimizes total site operating cost for Henkel Holthausen as a price-taking industrial consumer.
   - **Impact:** Aligns directly with behind-the-meter industrial reality; no market price feedback distortion since site load (<100 MW) is small relative to the German BZN (DE-LU).

3. **Bias 3 — Wholesale Price vs. Delivered Asset Cost:**
   - **Observation:** Electricity import cost incorporates spot price + grid fees + levies + S19 StromNEV peak-shaving mechanics. Gas import cost incorporates spot price + CO2 tax ($85\text{ \euro{}/t}$, $0.201\text{ tCO}_2/\text{MWh}$).
   - **Impact:** Avoids underestimating delivered energy costs; accurately captures power-to-heat switching thresholds.

### 3.2 Annuity & Financial Valuation
- **Capital Cost Calculation:** All extendable components use explicit Equivalent Annualized Cost (EAC):
  $$\text{EAC} = \text{CAPEX} \times \frac{r(1+r)^n}{(1+r)^n - 1} + \text{OPEX}_{\text{fixed}}$$
- Default discount rate $r = 7.0\%$ (WACC) matches Henkel industrial project benchmarks.

---

## 4. Deep-Dive Audit Against `pypsa-market-design`

### 4.1 Bus Architecture & Exergy Separation
The network topology enforces strict energy quality levels across four buses:
- `b_elec`: Electricity bus (130 €/MWh avg baseline).
- `b_gas`: Gas bus (45 €/MWh avg baseline incl. CO2).
- `b_steam_ht`: High-temperature steam (180–200°C, 16 bar) for process reactions.
- `b_heat_lt`: Mid-temperature process heat (80°C) for washing & facility heating.

A Steam-to-Heat Exchanger (`Link` with 98% efficiency) allows steam to cascade down to mid-temp heat, but mid-temp heat cannot heat high-temp steam, respecting Second Law thermodynamics.

### 4.2 Shadow Prices & Linear Pricing
- Model is solved as a continuous LP using HiGHS solver (`pypsa.Network.optimize(solver_name="highs")`).
- Dual values are preserved in `n.buses_t.marginal_price`, enabling detailed marginal cost decomposition across electricity, steam, and heat buses.

---

## 5. Verification & Key Findings

1. **TOML Configuration Completeness:** All 5 TOML files (`pv.toml`, `bess.toml`, `chp.toml`, `eboiler.toml`, `hthp.toml`) load cleanly and validate against Pydantic schema standards (`ComponentConfigs`).
2. **Economic Soundness:** Unit costs, efficiencies, and lifetime parameters align with Danish Energy Agency (2024) and Fraunhofer ISE benchmarks.
3. **PyPSA Modeling Alignment:** Component classes in `src/components/` accurately instantiate native PyPSA elements (`Generator`, `Link`, `Store`, `Bus`, `Load`) without unit conversion errors.
