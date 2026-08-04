"""
OEMOF.SOLPH Mixed-Integer Linear Programming (MILP) Energy System Model
for Henkel Dusseldorf Holthausen Flagship Manufacturing Site.

Models dual-temperature thermal quality (High-Temp Steam vs Mid-Temp Process Heat),
configurable grid fee scenarios, CHP, Electric Boilers,
Industrial Heat Pumps, PV, BESS, and Thermal Energy Storage (TES).

Component specifications are loaded from TOML config files in data/components/.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import tomllib

import pandas as pd
import numpy as np
import pyomo.environ as po
import oemof.solph as solph
from oemof.solph import buses, components, flows

# Default path to component configuration directory
DEFAULT_COMPONENTS_DIR = Path(__file__).parent.parent / "data" / "components"

# Emission factors (tCO2 per MWh)
# Gas: IPCC 2006 Guidelines Table 2.2, natural gas LHV basis
GAS_EMISSION_FACTOR_T_PER_MWH = 0.201
# Electricity grid (Germany avg): Umweltbundesamt 2024 publication
GRID_ELEC_EMISSION_FACTOR_T_PER_MWH = 0.38


def compute_pv_normalized_yield(
    df_solar: pd.DataFrame,
    lat: float = 51.1783,
    lon: float = 6.8445,
    tilt: float = 30.0,
    azimuth: float = 180.0,
) -> np.ndarray:
    """
    Computes normalized PV generation profile (0..1+ AC kW per kWp installed)
    using pvlib Plane-of-Array (POA) irradiance and cell temperature modeling.
    """
    try:
        import pvlib

        times = df_solar.index
        solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
        total_irrad = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azimuth,
            solar_zenith=solpos["apparent_zenith"],
            solar_azimuth=solpos["azimuth"],
            dni=df_solar["dni"],
            ghi=df_solar["ghi"],
            dhi=df_solar["dhi"],
        )
        poa_global = total_irrad["poa_global"].fillna(0.0)
        temp_air = df_solar.get("temp_air", 15.0)
        cell_temp = pvlib.temperature.faiman(poa_global, temp_air)
        dc_power = pvlib.pvsystem.pvwatts_dc(poa_global, cell_temp, pdc0=1.0, gamma_pdc=-0.004)
        pv_yield = np.clip(dc_power.values, 0.0, 1.2)
        return pv_yield
    except Exception:
        # Fallback to simple GHI / 1000 if pvlib calculation fails or data missing
        ghi = df_solar["ghi"].values / 1000.0
        return np.clip(ghi, 0.0, 1.0)


def load_component_config(components_dir: Path = DEFAULT_COMPONENTS_DIR) -> Dict[str, Dict]:
    """
    Loads all TOML config files from the components directory.
    Returns a dict keyed by component name (e.g. 'pv', 'bess', 'chp').
    """
    configs: Dict[str, Dict] = {}
    for toml_path in sorted(components_dir.glob("*.toml")):
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        # Each TOML file has a single top-level section matching its filename
        section_name = list(data.keys())[0]
        configs[section_name] = data[section_name]
    return configs


class HenkelEnergySystem:
    """
    Object-Oriented Wrapper for Henkel Holthausen Energy System Optimization.
    Supports both Operational Dispatch Mode and Investment Sizing Mode.

    All component specs are sourced from TOML configs (data/components/*.toml)
    instead of hardcoded values.
    """

    def __init__(
        self,
        df_market: Optional[pd.DataFrame] = None,
        df_solar: Optional[pd.DataFrame] = None,
        market_path: Optional[str | Path] = None,
        solar_path: Optional[str | Path] = None,
        mode: str = "operation",  # "operation" or "investment"
        pv_capacity_kwp: float = 0.0,
        bess_capacity_kwh: float = 0.0,
        hthp_capacity_kw_th: float = 15000.0,
        tes_capacity_kwh_th: float = 20000.0,
        enable_sec19_protection: bool = True,
        co2_tax_eur_per_ton: float = 85.0,
        wacc: float = 0.07,
        components_dir: Optional[Path] = None,
    ):
        base_data_dir = Path(__file__).parent.parent / "data"

        if df_market is not None:
            self.df_market = df_market.copy()
        else:
            m_path = Path(market_path) if market_path else base_data_dir / "market_data_2025.csv"
            self.df_market = pd.read_csv(m_path, index_col=0, parse_dates=True)

        if df_solar is not None:
            self.df_solar = df_solar.copy()
        else:
            s_path = Path(solar_path) if solar_path else base_data_dir / "solar_data_duesseldorf_2025.csv"
            self.df_solar = pd.read_csv(s_path, index_col=0, parse_dates=True)

        self.mode = mode
        self.enable_sec19_protection = enable_sec19_protection
        self.co2_tax_eur_per_ton = co2_tax_eur_per_ton
        self.wacc = wacc

        # Load component specifications from TOML configs
        comp_dir = components_dir or DEFAULT_COMPONENTS_DIR
        self.comp_cfg = load_component_config(comp_dir)

        # Extract existing plant capacities from configs (kW)
        chp_cfg = self.comp_cfg.get("chp", {})
        self.cap_chp_el = chp_cfg.get("capacity_el_kw", 40000.0)
        self.cap_chp_th = chp_cfg.get("capacity_th_kw", 45000.0)
        self.cap_gas_boiler = 180000.0  # 180 MW_th Gas Boiler (not in TOML -- existing baseline)

        eboiler_cfg = self.comp_cfg.get("eboiler", {})
        self.cap_eboiler = eboiler_cfg.get("capacity_th_kw", 30000.0)

        # Configurable / Investment capacities (overrides for operation mode)
        self.pv_capacity_kwp = pv_capacity_kwp
        self.bess_capacity_kwh = bess_capacity_kwh
        self.hthp_capacity_kw_th = hthp_capacity_kw_th
        self.tes_capacity_kwh_th = tes_capacity_kwh_th

        # Model state
        self.solph_es: Optional[solph.EnergySystem] = None
        self.model = None
        self.df_flows: Optional[pd.DataFrame] = None
        self.solution_meta: Optional[Dict[str, Any]] = None

    def _get_annualized_cost(self, capex_per_unit: float, lifetime_years: int) -> float:
        """Calculates Equivalent Annual Cost (EAC) per unit for Investment Mode."""
        r = self.wacc
        n = lifetime_years
        # Annuity factor: CRF = r(1+r)^n / ((1+r)^n - 1)
        annuity_factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        return capex_per_unit * annuity_factor

    def build_energy_system(self, timesteps: int = 168) -> solph.EnergySystem:
        """
        Constructs the oemof.solph EnergySystem graph for the specified timesteps.
        Component parameters are sourced from TOML configs loaded in __init__.
        """
        df_m = self.df_market.iloc[:timesteps]
        df_s = self.df_solar.iloc[:timesteps]
        timeindex = pd.date_range(
            start=df_m.index[0], periods=len(df_m) + 1, freq="h"
        )

        es = solph.EnergySystem(timeindex=timeindex, infer_last_interval=False)

        # -------------------------------------------------------
        # 1. BUSES
        # -------------------------------------------------------
        b_elec = buses.Bus(label="b_elec")
        b_gas = buses.Bus(label="b_gas")
        b_steam_ht = buses.Bus(label="b_steam_ht")  # High-Temp Steam (16 bar)
        b_heat_lt = buses.Bus(label="b_heat_lt")     # Mid-Temp Process Heat (80 deg C)

        es.add(b_elec, b_gas, b_steam_ht, b_heat_lt)

        # -------------------------------------------------------
        # 2. SOURCES (Grids & Renewables)
        # -------------------------------------------------------
        # Electricity grid cost: sec19 is one configurable option, not the default
        if self.enable_sec19_protection:
            grid_elec_cost = df_m["elec_total_sec19_eur_mwh"].values / 1000.0
        else:
            grid_elec_cost = df_m["elec_total_standard_eur_mwh"].values / 1000.0

        grid_elec = components.Source(
            label="grid_electricity",
            outputs={b_elec: flows.Flow(variable_costs=grid_elec_cost)}
        )

        # Gas grid cost: spot price + CO2 tax applied to emission factor
        gas_cost_eur_mwh = (
            df_m["gas_spot_eur_mwh"].values
            + (self.co2_tax_eur_per_ton * GAS_EMISSION_FACTOR_T_PER_MWH)
        )
        gas_cost_eur_kwh = gas_cost_eur_mwh / 1000.0  # EUR/MWh -> EUR/kWh for oemof

        grid_gas = components.Source(
            label="grid_gas",
            outputs={b_gas: flows.Flow(variable_costs=gas_cost_eur_kwh)}
        )

        # Solar PV -- modeled via pvlib POA irradiance and temperature yield
        pv_normalized = compute_pv_normalized_yield(df_s)

        pv_cfg = self.comp_cfg.get("pv", {})
        if self.mode == "investment":
            eac_pv = self._get_annualized_cost(
                capex_per_unit=pv_cfg.get("capex_eur_per_kw", 800.0),
                lifetime_years=pv_cfg.get("lifetime_years", 25),
            ) / 8760.0  # EUR/kWp-h
            pv_array = components.Source(
                label="solar_pv",
                outputs={
                    b_elec: flows.Flow(
                        fix=pv_normalized,
                        nominal_value=solph.Investment(
                            ep_costs=eac_pv,
                            maximum=pv_cfg.get("max_capacity_kw", 25000.0),
                        ),
                    )
                },
            )
        else:
            pv_array = components.Source(
                label="solar_pv",
                outputs={
                    b_elec: flows.Flow(
                        fix=pv_normalized,
                        nominal_value=self.pv_capacity_kwp,
                    )
                },
            )

        es.add(grid_elec, grid_gas, pv_array)

        # -------------------------------------------------------
        # 3. CONVERTERS (CHP, Boilers, Heat Pumps, Heat Exchangers)
        # -------------------------------------------------------
        chp_cfg = self.comp_cfg.get("chp", {})
        chp = components.Converter(
            label="gas_chp",
            inputs={b_gas: flows.Flow()},
            outputs={
                b_elec: flows.Flow(nominal_value=self.cap_chp_el),
                b_steam_ht: flows.Flow(nominal_value=self.cap_chp_th),
            },
            conversion_factors={
                b_elec: chp_cfg.get("electrical_efficiency", 0.40),
                b_steam_ht: chp_cfg.get("thermal_efficiency", 0.45),
            },
        )

        gas_boiler = components.Converter(
            label="gas_boiler",
            inputs={b_gas: flows.Flow()},
            outputs={b_steam_ht: flows.Flow(nominal_value=self.cap_gas_boiler)},
            conversion_factors={b_steam_ht: 0.92},  # Standard gas boiler efficiency
        )

        eboiler_cfg = self.comp_cfg.get("eboiler", {})
        eboiler = components.Converter(
            label="electric_boiler",
            inputs={b_elec: flows.Flow()},
            outputs={
                b_steam_ht: flows.Flow(
                    nominal_value=self.cap_eboiler,
                )
            },
            conversion_factors={
                b_steam_ht: eboiler_cfg.get("thermal_efficiency", 0.98),
            },
        )

        # Steam-to-heat exchanger: downgrades HT steam to LT process heat
        steam_to_heat = components.Converter(
            label="steam_to_heat_exchanger",
            inputs={b_steam_ht: flows.Flow()},
            outputs={b_heat_lt: flows.Flow(nominal_value=100000.0)},
            conversion_factors={b_heat_lt: 0.98},
        )

        hthp_cfg = self.comp_cfg.get("hthp", {})
        hthp_cop = hthp_cfg.get("cop", 2.8)

        if self.mode == "investment":
            eac_hthp = self._get_annualized_cost(
                capex_per_unit=hthp_cfg.get("capex_eur_per_kw_th", 600.0),
                lifetime_years=hthp_cfg.get("lifetime_years", 20),
            ) / 8760.0
            hthp = components.Converter(
                label="heat_pump",
                inputs={b_elec: flows.Flow()},
                outputs={
                    b_heat_lt: flows.Flow(
                        nominal_value=solph.Investment(
                            ep_costs=eac_hthp,
                            maximum=hthp_cfg.get("max_capacity_kw_th", 40000.0),
                        )
                    )
                },
                conversion_factors={b_heat_lt: hthp_cop},
            )
        else:
            hthp = components.Converter(
                label="heat_pump",
                inputs={b_elec: flows.Flow()},
                outputs={
                    b_heat_lt: flows.Flow(nominal_value=self.hthp_capacity_kw_th)
                },
                conversion_factors={b_heat_lt: hthp_cop},
            )

        es.add(chp, gas_boiler, eboiler, steam_to_heat, hthp)

        # -------------------------------------------------------
        # 4. STORAGE (BESS & Thermal Energy Storage)
        # -------------------------------------------------------
        bess_cfg = self.comp_cfg.get("bess", {})

        if self.mode == "investment":
            eac_bess = self._get_annualized_cost(
                capex_per_unit=bess_cfg.get("capex_eur_per_kwh", 350.0),
                lifetime_years=bess_cfg.get("lifetime_years", 15),
            ) / 8760.0
            bess = components.GenericStorage(
                label="bess",
                nominal_storage_capacity=solph.Investment(
                    ep_costs=eac_bess,
                    maximum=bess_cfg.get("max_capacity_kwh", 50000.0),
                ),
                inputs={b_elec: flows.Flow()},
                outputs={b_elec: flows.Flow()},
                loss_rate=bess_cfg.get("self_discharge_rate_per_hour", 0.0001),
                inflow_conversion_factor=bess_cfg.get("charge_efficiency", 0.95),
                outflow_conversion_factor=bess_cfg.get("discharge_efficiency", 0.95),
            )
        else:
            c_rate = bess_cfg.get("c_rate", 0.5)
            bess_power = self.bess_capacity_kwh * c_rate if self.bess_capacity_kwh > 0 else 0.0
            bess = components.GenericStorage(
                label="bess",
                nominal_storage_capacity=self.bess_capacity_kwh,
                inputs={b_elec: flows.Flow(nominal_value=bess_power)},
                outputs={b_elec: flows.Flow(nominal_value=bess_power)},
                loss_rate=bess_cfg.get("self_discharge_rate_per_hour", 0.0001),
                inflow_conversion_factor=bess_cfg.get("charge_efficiency", 0.95),
                outflow_conversion_factor=bess_cfg.get("discharge_efficiency", 0.95),
            )

        # TES -- no TOML config yet; using inline defaults
        if self.mode == "investment":
            eac_tes = self._get_annualized_cost(
                capex_per_unit=120.0,  # EUR/kWh_th (Danish Energy Agency reference)
                lifetime_years=25,
            ) / 8760.0
            tes = components.GenericStorage(
                label="tes",
                nominal_storage_capacity=solph.Investment(
                    ep_costs=eac_tes, maximum=100000.0
                ),
                inputs={b_heat_lt: flows.Flow()},
                outputs={b_heat_lt: flows.Flow()},
                loss_rate=0.005,
                inflow_conversion_factor=0.98,
                outflow_conversion_factor=0.98,
            )
        else:
            tes_power = self.tes_capacity_kwh_th / 4.0 if self.tes_capacity_kwh_th > 0 else 0.0
            tes = components.GenericStorage(
                label="tes",
                nominal_storage_capacity=self.tes_capacity_kwh_th,
                inputs={b_heat_lt: flows.Flow(nominal_value=tes_power)},
                outputs={b_heat_lt: flows.Flow(nominal_value=tes_power)},
                loss_rate=0.005,
                inflow_conversion_factor=0.98,
                outflow_conversion_factor=0.98,
            )

        es.add(bess, tes)

        # -------------------------------------------------------
        # 5. SINKS (Demands)
        # -------------------------------------------------------
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
        Returns optimization results dictionary including CO2 tracking.
        """
        if self.solph_es is None:
            self.build_energy_system(timesteps=timesteps)

        self.model = solph.Model(self.solph_es)
        m = self.model

        # Clean Pyomo APPSI attributes that oemof adds but appsi_highs rejects
        if hasattr(m, "dual"):
            delattr(m, "dual")
        if hasattr(m, "rc"):
            delattr(m, "rc")

        opt = po.SolverFactory(solver_name)
        opt.solve(m)

        total_cost_eur = po.value(m.objective)
        hours = timesteps
        # 450,000 tons/year at 8760 hours -> tons per hour * hours simulated
        annual_production_tons = (450000.0 / 8760.0) * hours
        cost_per_ton = total_cost_eur / annual_production_tons

        # Extract flow time-series DataFrame
        df_m = self.df_market.iloc[:timesteps]
        flow_data: Dict[str, list] = {}
        for (i, o) in m.FLOWS:
            flow_key = f"{i.label} -> {o.label}"
            flow_data[flow_key] = [
                po.value(m.flow[i, o, t]) for t in range(timesteps)
            ]

        self.df_flows = pd.DataFrame(flow_data, index=df_m.index)

        # Post-processing: CO2 emission tracking
        co2_results = self._compute_co2_emissions(timesteps)

        self.solution_meta = {
            "total_cost_eur": total_cost_eur,
            "cost_per_ton_eur": cost_per_ton,
            "timesteps": timesteps,
            "mode": self.mode,
            **co2_results,
        }

        return self.solution_meta

    def _compute_co2_emissions(self, timesteps: int) -> Dict[str, float]:
        """
        Computes CO2 emissions from gas and electricity grid consumption,
        and estimates CO2 avoided relative to a gas-only baseline.

        Gas emissions: gas consumed (kWh) * GAS_EMISSION_FACTOR (tCO2/MWh) / 1000
        Grid elec emissions: grid elec consumed (kWh) * GRID_ELEC_EMISSION_FACTOR / 1000
        CO2 avoided: baseline emissions - optimized emissions
        """
        df = self.df_flows
        if df is None:
            return {}

        # Gas consumption from grid (kWh per timestep)
        gas_col = "grid_gas -> b_gas"
        gas_consumed_kwh = df[gas_col].sum() if gas_col in df.columns else 0.0
        # Convert kWh to MWh for emission factor multiplication
        co2_from_gas_tons = gas_consumed_kwh * GAS_EMISSION_FACTOR_T_PER_MWH / 1000.0

        # Grid electricity consumption (kWh per timestep)
        elec_col = "grid_electricity -> b_elec"
        grid_elec_consumed_kwh = df[elec_col].sum() if elec_col in df.columns else 0.0
        co2_from_elec_tons = grid_elec_consumed_kwh * GRID_ELEC_EMISSION_FACTOR_T_PER_MWH / 1000.0

        co2_total_tons = co2_from_gas_tons + co2_from_elec_tons

        # Baseline: all heat from gas boilers (eta=0.92), all elec from grid
        # Demand: 60 MW_el + 160 MW_th steam + 60 MW_th heat = 280 MW total thermal
        baseline_elec_kwh = 60000.0 * timesteps
        baseline_steam_kwh = 160000.0 * timesteps
        baseline_heat_kwh = 60000.0 * timesteps
        # Gas needed for all thermal via boiler at 92% efficiency
        baseline_gas_kwh = (baseline_steam_kwh + baseline_heat_kwh) / 0.92
        baseline_co2_gas = baseline_gas_kwh * GAS_EMISSION_FACTOR_T_PER_MWH / 1000.0
        baseline_co2_elec = baseline_elec_kwh * GRID_ELEC_EMISSION_FACTOR_T_PER_MWH / 1000.0
        baseline_co2_total = baseline_co2_gas + baseline_co2_elec

        co2_avoided_tons = baseline_co2_total - co2_total_tons

        return {
            "co2_from_gas_tons": round(co2_from_gas_tons, 2),
            "co2_from_elec_tons": round(co2_from_elec_tons, 2),
            "co2_total_tons": round(co2_total_tons, 2),
            "co2_baseline_tons": round(baseline_co2_total, 2),
            "co2_avoided_tons": round(co2_avoided_tons, 2),
        }

    def get_dispatch_dataframe(self) -> pd.DataFrame:
        """Returns the full hourly dispatch flow DataFrame."""
        if self.df_flows is None:
            raise ValueError("Model has not been solved yet. Call solve() first.")
        return self.df_flows

    def get_investment_capacities(self) -> Dict[str, float]:
        """Extracts optimal investment capacities if solved in Investment mode."""
        if self.mode != "investment":
            return {"status": "Not in investment mode"}

        m = self.model
        investments: Dict[str, float] = {}
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
