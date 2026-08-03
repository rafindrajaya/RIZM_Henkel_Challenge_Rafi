"""
OEMOF.SOLPH Mixed-Integer Linear Programming (MILP) Energy System Model
for Henkel Düsseldorf Holthausen Flagship Manufacturing Site.

Models dual-temperature thermal quality (High-Temp Steam vs Mid-Temp Process Heat),
electricity grid fees (§19 StromNEV protection), CHP, Electric Boilers,
Industrial Heat Pumps, PV, BESS, and Thermal Energy Storage (TES).
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import pyomo.environ as po
import oemof.solph as solph
from oemof.solph import buses, components, flows


class HenkelEnergySystem:
    """
    Object-Oriented Wrapper for Henkel Holthausen Energy System Optimization.
    Supports both Operational Dispatch Mode and Investment Sizing Mode.
    """

    def __init__(
        self,
        df_market: pd.DataFrame,
        df_solar: pd.DataFrame,
        mode: str = "operation",  # "operation" or "investment"
        pv_capacity_kwp: float = 0.0,
        bess_capacity_kwh: float = 0.0,
        hthp_capacity_kw_th: float = 15000.0,  # Baseline 15 MW_th Heat Pump
        tes_capacity_kwh_th: float = 20000.0,  # Baseline 20 MWh TES
        enable_sec19_protection: bool = True,
        co2_tax_eur_per_ton: float = 85.0,
        wacc: float = 0.07,
    ):
        self.df_market = df_market.copy()
        self.df_solar = df_solar.copy()
        self.mode = mode
        self.enable_sec19_protection = enable_sec19_protection
        self.co2_tax_eur_per_ton = co2_tax_eur_per_ton
        self.wacc = wacc

        # Existing plant capacities (baseline kW)
        self.cap_chp_el = 40000.0        # 40 MW_el Gas CHP
        self.cap_chp_th = 45000.0        # 45 MW_th High-Temp Steam CHP
        self.cap_gas_boiler = 180000.0   # 180 MW_th Gas Boiler
        self.cap_eboiler = 30000.0       # 30 MW_th Electric Boiler (P2H)

        # Configurable / Investment capacities
        self.pv_capacity_kwp = pv_capacity_kwp
        self.bess_capacity_kwh = bess_capacity_kwh
        self.hthp_capacity_kw_th = hthp_capacity_kw_th
        self.tes_capacity_kwh_th = tes_capacity_kwh_th

        self.solph_es = None
        self.model = None
        self.df_flows = None
        self.solution_meta = None

    def _get_annualized_cost(self, capex_per_unit: float, lifetime_years: int) -> float:
        """Calculates Equivalent Annual Cost (EAC) per unit for Investment Mode."""
        r = self.wacc
        n = lifetime_years
        annuity_factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        return capex_per_unit * annuity_factor

    def build_energy_system(self, timesteps: int = 168) -> solph.EnergySystem:
        """
        Constructs the oemof.solph EnergySystem graph for the specified timesteps.
        """
        df_m = self.df_market.iloc[:timesteps]
        df_s = self.df_solar.iloc[:timesteps]
        timeindex = pd.date_range(start=df_m.index[0], periods=len(df_m) + 1, freq="h")

        es = solph.EnergySystem(timeindex=timeindex, infer_last_interval=False)

        # ----------------------------------------------------
        # 1. BUSES
        # ----------------------------------------------------
        b_elec = buses.Bus(label="b_elec")
        b_gas = buses.Bus(label="b_gas")
        b_steam_ht = buses.Bus(label="b_steam_ht")  # High-Temp Steam (16 bar)
        b_heat_lt = buses.Bus(label="b_heat_lt")    # Mid-Temp Process Heat (80°C)

        es.add(b_elec, b_gas, b_steam_ht, b_heat_lt)

        # ----------------------------------------------------
        # 2. SOURCES (Grids & Renewables)
        # ----------------------------------------------------
        if self.enable_sec19_protection:
            grid_elec_cost = df_m["elec_total_sec19_eur_mwh"].values / 1000.0  # €/kWh
        else:
            grid_elec_cost = df_m["elec_total_standard_eur_mwh"].values / 1000.0

        grid_elec = components.Source(
            label="grid_electricity",
            outputs={b_elec: flows.Flow(variable_costs=grid_elec_cost)}
        )

        gas_emission_factor_t_per_mwh = 0.201
        gas_cost_eur_mwh = df_m["gas_spot_eur_mwh"].values + (self.co2_tax_eur_per_ton * gas_emission_factor_t_per_mwh)
        gas_cost_eur_kwh = gas_cost_eur_mwh / 1000.0

        grid_gas = components.Source(
            label="grid_gas",
            outputs={b_gas: flows.Flow(variable_costs=gas_cost_eur_kwh)}
        )

        pv_normalized = df_s["ghi"].values / 1000.0
        pv_normalized = np.clip(pv_normalized, 0, 1)

        if self.mode == "investment":
            eac_pv = self._get_annualized_cost(capex_per_unit=800.0, lifetime_years=25) / 8760.0  # €/kWp-h
            pv_array = components.Source(
                label="solar_pv",
                outputs={
                    b_elec: flows.Flow(
                        fix=pv_normalized,
                        nominal_value=solph.Investment(ep_costs=eac_pv, maximum=25000.0)  # Max 25 MWp rooftop
                    )
                }
            )
        else:
            pv_array = components.Source(
                label="solar_pv",
                outputs={
                    b_elec: flows.Flow(
                        fix=pv_normalized,
                        nominal_value=self.pv_capacity_kwp
                    )
                }
            )

        es.add(grid_elec, grid_gas, pv_array)

        # ----------------------------------------------------
        # 3. CONVERTERS (CHP, Boilers, Heat Pumps, Heat Exchangers)
        # ----------------------------------------------------
        chp = components.Converter(
            label="gas_chp",
            inputs={b_gas: flows.Flow()},
            outputs={
                b_elec: flows.Flow(nominal_value=self.cap_chp_el),
                b_steam_ht: flows.Flow(nominal_value=self.cap_chp_th)
            },
            conversion_factors={b_elec: 0.40, b_steam_ht: 0.45}
        )

        gas_boiler = components.Converter(
            label="gas_boiler",
            inputs={b_gas: flows.Flow()},
            outputs={b_steam_ht: flows.Flow(nominal_value=self.cap_gas_boiler)},
            conversion_factors={b_steam_ht: 0.92}
        )

        eboiler = components.Converter(
            label="electric_boiler",
            inputs={b_elec: flows.Flow()},
            outputs={b_steam_ht: flows.Flow(nominal_value=self.cap_eboiler)},
            conversion_factors={b_steam_ht: 0.98}
        )

        steam_to_heat = components.Converter(
            label="steam_to_heat_exchanger",
            inputs={b_steam_ht: flows.Flow()},
            outputs={b_heat_lt: flows.Flow(nominal_value=100000.0)},
            conversion_factors={b_heat_lt: 0.98}
        )

        if self.mode == "investment":
            eac_hthp = self._get_annualized_cost(capex_per_unit=600.0, lifetime_years=20) / 8760.0
            hthp = components.Converter(
                label="heat_pump",
                inputs={b_elec: flows.Flow()},
                outputs={
                    b_heat_lt: flows.Flow(
                        nominal_value=solph.Investment(ep_costs=eac_hthp, maximum=40000.0)
                    )
                },
                conversion_factors={b_heat_lt: 2.8}
            )
        else:
            hthp = components.Converter(
                label="heat_pump",
                inputs={b_elec: flows.Flow()},
                outputs={b_heat_lt: flows.Flow(nominal_value=self.hthp_capacity_kw_th)},
                conversion_factors={b_heat_lt: 2.8}
            )

        es.add(chp, gas_boiler, eboiler, steam_to_heat, hthp)

        # ----------------------------------------------------
        # 4. STORAGE (BESS & Thermal Energy Storage)
        # ----------------------------------------------------
        if self.mode == "investment":
            eac_bess = self._get_annualized_cost(capex_per_unit=350.0, lifetime_years=15) / 8760.0
            bess = components.GenericStorage(
                label="bess",
                nominal_storage_capacity=solph.Investment(ep_costs=eac_bess, maximum=50000.0),
                inputs={b_elec: flows.Flow()},
                outputs={b_elec: flows.Flow()},
                loss_rate=0.0001,
                inflow_conversion_factor=0.95,
                outflow_conversion_factor=0.95,
            )

            eac_tes = self._get_annualized_cost(capex_per_unit=120.0, lifetime_years=25) / 8760.0
            tes = components.GenericStorage(
                label="tes",
                nominal_storage_capacity=solph.Investment(ep_costs=eac_tes, maximum=100000.0),
                inputs={b_heat_lt: flows.Flow()},
                outputs={b_heat_lt: flows.Flow()},
                loss_rate=0.005,
                inflow_conversion_factor=0.98,
                outflow_conversion_factor=0.98,
            )
        else:
            bess = components.GenericStorage(
                label="bess",
                nominal_storage_capacity=self.bess_capacity_kwh,
                inputs={b_elec: flows.Flow(nominal_value=self.bess_capacity_kwh / 2.0 if self.bess_capacity_kwh > 0 else 0.0)},
                outputs={b_elec: flows.Flow(nominal_value=self.bess_capacity_kwh / 2.0 if self.bess_capacity_kwh > 0 else 0.0)},
                loss_rate=0.0001,
                inflow_conversion_factor=0.95,
                outflow_conversion_factor=0.95,
            )

            tes = components.GenericStorage(
                label="tes",
                nominal_storage_capacity=self.tes_capacity_kwh_th,
                inputs={b_heat_lt: flows.Flow(nominal_value=self.tes_capacity_kwh_th / 4.0 if self.tes_capacity_kwh_th > 0 else 0.0)},
                outputs={b_heat_lt: flows.Flow(nominal_value=self.tes_capacity_kwh_th / 4.0 if self.tes_capacity_kwh_th > 0 else 0.0)},
                loss_rate=0.005,
                inflow_conversion_factor=0.98,
                outflow_conversion_factor=0.98,
            )

        es.add(bess, tes)

        # ----------------------------------------------------
        # 5. SINKS (Demands)
        # ----------------------------------------------------
        demand_elec = components.Sink(
            label="demand_elec",
            inputs={b_elec: flows.Flow(nominal_value=60000.0, fix=1.0)} 
        )

        demand_steam = components.Sink(
            label="demand_steam",
            inputs={b_steam_ht: flows.Flow(nominal_value=160000.0, fix=1.0)}
        )

        demand_heat = components.Sink(
            label="demand_heat",
            inputs={b_heat_lt: flows.Flow(nominal_value=60000.0, fix=1.0)}
        )

        es.add(demand_elec, demand_steam, demand_heat)

        self.solph_es = es
        return es

    def solve(self, solver_name: str = "appsi_highs", timesteps: int = 168) -> Dict[str, Any]:
        """
        Builds the model and invokes the solver (HiGHS via appsi_highs).
        Returns optimization results dictionary.
        """
        if self.solph_es is None:
            self.build_energy_system(timesteps=timesteps)

        self.model = solph.Model(self.solph_es)
        m = self.model

        # Clean Pyomo APPSI attributes
        if hasattr(m, 'dual'): delattr(m, 'dual')
        if hasattr(m, 'rc'): delattr(m, 'rc')

        opt = po.SolverFactory(solver_name)
        opt.solve(m)

        total_cost_eur = po.value(m.objective)
        hours = timesteps
        annual_production_tons = (450000.0 / 8760.0) * hours
        cost_per_ton = total_cost_eur / annual_production_tons

        # Extract flow time-series DataFrame
        df_m = self.df_market.iloc[:timesteps]
        flow_data = {}
        for (i, o) in m.FLOWS:
            flow_key = f"{i.label} -> {o.label}"
            flow_data[flow_key] = [po.value(m.flow[i, o, t]) for t in range(timesteps)]

        self.df_flows = pd.DataFrame(flow_data, index=df_m.index)

        self.solution_meta = {
            "total_cost_eur": total_cost_eur,
            "cost_per_ton_eur": cost_per_ton,
            "timesteps": timesteps,
            "mode": self.mode
        }

        return self.solution_meta

    def get_dispatch_dataframe(self) -> pd.DataFrame:
        """Returns the full 15-min / hourly dispatch flow DataFrame."""
        if self.df_flows is None:
            raise ValueError("Model has not been solved yet. Call solve() first.")
        return self.df_flows

    def get_investment_capacities(self) -> Dict[str, float]:
        """Extracts optimal investment capacities if solved in Investment mode."""
        if self.mode != "investment":
            return {"status": "Not in investment mode"}
        
        m = self.model
        investments = {}
        if hasattr(m, "InvestmentFlowBlock"):
            for k, val in m.InvestmentFlowBlock.invest.items():
                src_label = str(k[0]).split("'")[1] if "'" in str(k[0]) else str(k[0])
                target_label = str(k[1]).split("'")[1] if "'" in str(k[1]) else str(k[1])
                investments[f"Invest: {src_label} -> {target_label}"] = po.value(val)
            
        if hasattr(m, "GenericInvestmentStorageBlock"):
            for k, val in m.GenericInvestmentStorageBlock.invest.items():
                node_label = str(k[0]).split("'")[1] if "'" in str(k[0]) else str(k[0])
                investments[f"Invest Storage: {node_label}"] = po.value(val)
            
        return investments
