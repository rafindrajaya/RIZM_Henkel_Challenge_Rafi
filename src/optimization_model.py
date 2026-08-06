"""
OEMOF.SOLPH Mixed-Integer Linear Programming (MILP) Energy System Model
for Henkel Dusseldorf Holthausen Flagship Manufacturing Site.

Models dual-temperature thermal quality (High-Temp Steam vs Mid-Temp Process Heat),
configurable grid fee scenarios, CHP, Electric Boilers,
Industrial Heat Pumps, PV, BESS, and Thermal Energy Storage (TES).

Component specifications are loaded from TOML config files in data/components/.
"""

import sys
from typing import Dict, Any, Optional, Literal
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import toml as tomllib  # type: ignore

import pandas as pd
import numpy as np
import pyomo.environ as po
import oemof.solph as solph
from oemof.solph import buses, components, flows
from oemof.tools import economics
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# CONFIGURATION SCHEMAS (Pydantic Models)
# -----------------------------------------------------------------------------
class FixedSizingConfig(BaseModel):
    """Configuration for fixed existing/installed asset capacities (kW or kWh)."""
    pv: float = Field(default=0.0, ge=0.0, description="Rooftop PV installed capacity in kWp")
    bess: float = Field(default=0.0, ge=0.0, description="Battery Storage capacity in kWh")
    hthp: float = Field(default=15000.0, ge=0.0, description="High-Temp Heat Pump thermal capacity in kW_th")
    tes: float = Field(default=20000.0, ge=0.0, description="Thermal Energy Storage capacity in kWh_th")
    chp_el: float = Field(default=30000.0, ge=0.0, description="Existing CHP electrical capacity in kW")
    chp_th: float = Field(default=30000.0, ge=0.0, description="Existing CHP thermal capacity in kW")
    gas_boiler: float = Field(default=180000.0, ge=0.0, description="Existing Gas Boiler thermal capacity in kW")
    eboiler: float = Field(default=25000.0, ge=0.0, description="Existing Electric Boiler thermal capacity in kW")


class ComponentBounds(BaseModel):
    """Investment optimization bounds for a single asset."""
    enabled: bool = Field(default=True, description="Whether asset is eligible for investment sizing")
    min_capacity: float = Field(default=0.0, ge=0.0, description="Minimum capacity bound")
    max_capacity: float = Field(default=50000.0, ge=0.0, description="Maximum capacity bound")


class VariableSizingConfig(BaseModel):
    """Configuration for variable investment candidate assets."""
    pv: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=True, min_capacity=0.0, max_capacity=25000.0))
    bess: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=True, min_capacity=0.0, max_capacity=50000.0))
    hthp: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=True, min_capacity=0.0, max_capacity=40000.0))
    tes: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=True, min_capacity=0.0, max_capacity=100000.0))
    chp: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=False, min_capacity=0.0, max_capacity=50000.0))
    gas_boiler: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=False, min_capacity=0.0, max_capacity=100000.0))
    eboiler: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=False, min_capacity=0.0, max_capacity=50000.0))


class FacilityProjectConfig(BaseModel):
    """Master Pydantic configuration schema for Henkel Holthausen Energy System."""
    project_name: str = Field(default="current_facility_optimization", description="Name of project / energy system")
    optimization_mode: Literal["operation", "investment"] = Field(default="operation", description="Optimization mode")
    start_time: str = Field(default="01/01/2025", description="Start date in DD/MM/YYYY format")
    end_time: str = Field(default="08/01/2025", description="End date in DD/MM/YYYY format")
    fixed_components_sizing: FixedSizingConfig = Field(default_factory=FixedSizingConfig)
    variable_components_sizing: VariableSizingConfig = Field(default_factory=VariableSizingConfig)
    co2_tax_eur_per_ton: float = Field(default=85.0, ge=0.0)
    enable_sec19_protection: bool = Field(default=True)
    wacc: float = Field(default=0.07, ge=0.0, le=0.30)
    market_path: Optional[Path] = None
    solar_path: Optional[Path] = None


# Default path to component configuration directory
DEFAULT_COMPONENTS_DIR = Path(__file__).parent.parent / "data" / "components"

# Emission factors (tCO2 per MWh)
GAS_EMISSION_FACTOR_T_PER_MWH = 0.201
GRID_ELEC_EMISSION_FACTOR_T_PER_MWH = 0.38


# -----------------------------------------------------------------------------
# COMPONENT CONFIGURATION SCHEMAS (Pydantic Models for TOML files)
# Critical fields are REQUIRED (no default) -- missing them triggers a
# ValidationError at load time, preventing silent fallback to wrong values.
# Secondary fields have sensible defaults and are optional.
# -----------------------------------------------------------------------------
class PVComponentConfig(BaseModel):
    """Rooftop PV system configuration loaded from data/components/pv.toml."""
    # Required: cost-critical fields that directly affect optimization objective
    capex_eur_per_kw: float = Field(ge=0.0, description="EUR/kWp installed, large-scale rooftop")
    lifetime_years: int = Field(ge=1, description="Expected operational lifetime in years")
    max_capacity_kw: float = Field(ge=0.0, description="Maximum rooftop area constraint in kWp")
    # Optional: secondary performance parameters
    model_name: str = Field(default="Generic_Rooftop_Crystalline_Si")
    opex_eur_per_kw_year: float = Field(default=12.0, ge=0.0, description="Fixed O&M per year")
    degradation_rate_per_year: float = Field(default=0.005, ge=0.0, le=0.1, description="Linear degradation rate")
    tilt_deg: float = Field(default=30.0, ge=0.0, le=90.0, description="Panel tilt angle in degrees")
    azimuth_deg: float = Field(default=180.0, ge=0.0, le=360.0, description="Panel azimuth (180=South)")
    albedo: float = Field(default=0.2, ge=0.0, le=1.0, description="Ground reflectance")


class BESSComponentConfig(BaseModel):
    """Battery Energy Storage System configuration loaded from data/components/bess.toml."""
    # Required: cost-critical fields
    capex_eur_per_kwh: float = Field(ge=0.0, description="EUR/kWh usable capacity")
    lifetime_years: int = Field(ge=1, description="Expected operational lifetime in years")
    max_capacity_kwh: float = Field(ge=0.0, description="Maximum BESS capacity in kWh")
    charge_efficiency: float = Field(ge=0.0, le=1.0, description="DC charging efficiency")
    discharge_efficiency: float = Field(ge=0.0, le=1.0, description="DC discharging efficiency")
    # Optional: secondary parameters
    model_name: str = Field(default="Generic_LFP_Container_4h")
    opex_eur_per_kwh_year: float = Field(default=5.0, ge=0.0, description="Fixed O&M per year")
    round_trip_efficiency: float = Field(default=0.90, ge=0.0, le=1.0, description="AC-AC RTE")
    self_discharge_rate_per_hour: float = Field(default=0.0001, ge=0.0, description="Calendar degradation proxy")
    initial_soc: float = Field(default=0.5, ge=0.0, le=1.0, description="Initial state of charge")
    c_rate: float = Field(default=0.5, ge=0.0, description="Max power = C_rate * capacity")


class CHPComponentConfig(BaseModel):
    """Combined Heat and Power (CHP) configuration loaded from data/components/chp.toml."""
    # Required: critical performance and sizing fields
    electrical_efficiency: float = Field(ge=0.0, le=1.0, description="Electrical output / gas input (LHV)")
    thermal_efficiency: float = Field(ge=0.0, le=1.0, description="HT steam output / gas input (LHV)")
    capacity_el_kw: float = Field(ge=0.0, description="Electrical capacity in kW")
    capacity_th_kw: float = Field(ge=0.0, description="Thermal capacity in kW")
    # Optional: secondary parameters
    model_name: str = Field(default="Existing_Gas_CHP_Holthausen")
    capex_eur_per_kw_el: float = Field(default=1200.0, ge=0.0, description="Reference greenfield CAPEX")
    opex_eur_per_kw_el_year: float = Field(default=25.0, ge=0.0, description="Fixed O&M per year")
    lifetime_years: int = Field(default=25, ge=1, description="Expected operational lifetime in years")


class EBoilerComponentConfig(BaseModel):
    """Electric Boiler (Power-to-Heat) configuration loaded from data/components/eboiler.toml."""
    # Required: critical fields
    thermal_efficiency: float = Field(ge=0.0, le=1.0, description="Electricity to steam conversion")
    capacity_th_kw: float = Field(ge=0.0, description="Thermal capacity in kW")
    # Optional: secondary parameters
    model_name: str = Field(default="Electrode_Boiler_HT_Steam")
    capex_eur_per_kw_th: float = Field(default=100.0, ge=0.0, description="EUR/kW_th installed")
    opex_eur_per_kw_th_year: float = Field(default=2.0, ge=0.0, description="Fixed O&M per year")
    lifetime_years: int = Field(default=20, ge=1, description="Expected operational lifetime in years")


class HTHPComponentConfig(BaseModel):
    """High-Temperature Industrial Heat Pump configuration loaded from data/components/hthp.toml."""
    # Required: cost-critical fields
    capex_eur_per_kw_th: float = Field(ge=0.0, description="EUR/kW_th installed")
    lifetime_years: int = Field(ge=1, description="Expected operational lifetime in years")
    cop: float = Field(ge=1.0, description="Coefficient of Performance")
    max_capacity_kw_th: float = Field(ge=0.0, description="Maximum thermal capacity in kW_th")
    # Optional: secondary parameters
    model_name: str = Field(default="Industrial_HTHP_Compression")
    opex_eur_per_kw_th_year: float = Field(default=10.0, ge=0.0, description="Fixed O&M per year")
    source_temp_c: float = Field(default=35.0, description="Waste heat source temperature")
    supply_temp_c: float = Field(default=80.0, description="Process heat supply temperature")


class TESComponentConfig(BaseModel):
    """Thermal Energy Storage configuration (currently hardcoded, will source from TOML)."""
    # Required: cost-critical fields
    capex_eur_per_kwh_th: float = Field(default=120.0, ge=0.0, description="EUR/kWh_th installed")
    lifetime_years: int = Field(default=25, ge=1, description="Expected operational lifetime")
    max_capacity_kwh_th: float = Field(default=100000.0, ge=0.0, description="Maximum TES capacity")
    # Optional: performance parameters
    model_name: str = Field(default="Generic_Sensible_TES")
    loss_rate_per_hour: float = Field(default=0.005, ge=0.0, description="Thermal loss rate per hour")
    charge_efficiency: float = Field(default=0.98, ge=0.0, le=1.0, description="Charging efficiency")
    discharge_efficiency: float = Field(default=0.98, ge=0.0, le=1.0, description="Discharging efficiency")


class ComponentConfigs(BaseModel):
    """Container holding all validated component configurations."""
    pv: PVComponentConfig
    bess: BESSComponentConfig
    chp: CHPComponentConfig
    eboiler: EBoilerComponentConfig
    hthp: HTHPComponentConfig
    tes: TESComponentConfig = Field(default_factory=TESComponentConfig)


def compute_pv_normalized_yield(
    df_solar: pd.DataFrame,
    lat: float = 51.1783,
    lon: float = 6.8445,
    tilt: float = 38.0,
    azimuth: float = 180.0,
) -> np.ndarray:
    """
    Computes or retrieves normalized PV generation profile (0..1+ AC kW per kWp installed)
    using pre-computed DataFrame column or pvlib Plane-of-Array (POA) irradiance modeling.
    """
    if "pv_normalized_yield" in df_solar.columns:
        return np.clip(np.asarray(df_solar["pv_normalized_yield"], dtype=float), 0.0, 1.2)

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
        temp_air = df_solar["temp_air"] if "temp_air" in df_solar.columns else 15.0
        cell_temp = pvlib.temperature.faiman(poa_global, temp_air)
        dc_power = pvlib.pvsystem.pvwatts_dc(poa_global, cell_temp, pdc0=1.0, gamma_pdc=-0.004)
        pv_yield = np.clip(np.asarray(dc_power, dtype=float), 0.0, 1.2)
        return pv_yield
    except Exception:
        ghi = np.asarray(df_solar["ghi"], dtype=float) / 1000.0
        return np.clip(ghi, 0.0, 1.0)


def parse_config_date(date_str: str) -> pd.Timestamp:
    """Parses date string supporting DD/MM/YYYY, YYYY-MM-DD, and ISO datetime strings."""
    try:
        return pd.to_datetime(date_str, dayfirst=True)
    except Exception:
        return pd.to_datetime(date_str)


def load_component_config(components_dir: Path = DEFAULT_COMPONENTS_DIR) -> ComponentConfigs:
    """
    Loads all TOML config files from the components directory and validates
    each against its Pydantic model. Raises ValidationError if required fields
    are missing, preventing silent fallback to incorrect default values.

    Returns a typed ComponentConfigs container with validated component configs.
    """
    raw_configs: Dict[str, Dict] = {}
    for toml_path in sorted(components_dir.glob("*.toml")):
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        section_name = list(data.keys())[0]
        raw_configs[section_name] = data[section_name]

    # Map TOML section names to their Pydantic model classes
    model_map = {
        "pv": PVComponentConfig,
        "bess": BESSComponentConfig,
        "chp": CHPComponentConfig,
        "eboiler": EBoilerComponentConfig,
        "hthp": HTHPComponentConfig,
    }

    validated: Dict[str, Any] = {}
    for name, model_cls in model_map.items():
        raw_data = raw_configs.get(name)
        if raw_data is None:
            raise FileNotFoundError(
                f"Missing TOML config for component '{name}'. "
                f"Expected file: {components_dir / f'{name}.toml'}"
            )
        # Pydantic validates and raises ValidationError if required fields missing
        validated[name] = model_cls(**raw_data)

    # TES has all-default fields, so it's optional in the TOML directory
    if "tes" in raw_configs:
        validated["tes"] = TESComponentConfig(**raw_configs["tes"])
    else:
        validated["tes"] = TESComponentConfig()

    return ComponentConfigs(**validated)


class HenkelEnergySystem:
    """
    Object-Oriented Wrapper for Henkel Holthausen Energy System Optimization.
    Supports both Operational Dispatch Mode and Investment Sizing Mode.
    Validated via Pydantic configuration schemas.
    """

    def __init__(
        self,
        config: Optional[FacilityProjectConfig] = None,
        df_market: Optional[pd.DataFrame] = None,
        df_solar: Optional[pd.DataFrame] = None,
        market_path: Optional[str | Path] = None,
        solar_path: Optional[str | Path] = None,
        mode: str = "operation",
        pv_capacity_kwp: float = 0.0,
        bess_capacity_kwh: float = 0.0,
        hthp_capacity_kw_th: float = 15000.0,
        tes_capacity_kwh_th: float = 20000.0,
        enable_sec19_protection: bool = True,
        co2_tax_eur_per_ton: float = 85.0,
        wacc: float = 0.07,
        components_dir: Optional[Path] = None,
    ):
        # Build or use provided Pydantic config
        if config is not None:
            self.config = config
        else:
            fixed_cfg = FixedSizingConfig(
                pv=pv_capacity_kwp,
                bess=bess_capacity_kwh,
                hthp=hthp_capacity_kw_th,
                tes=tes_capacity_kwh_th,
            )
            self.config = FacilityProjectConfig(
                optimization_mode=mode,
                fixed_components_sizing=fixed_cfg,
                co2_tax_eur_per_ton=co2_tax_eur_per_ton,
                enable_sec19_protection=enable_sec19_protection,
                wacc=wacc,
                market_path=Path(market_path) if market_path else None,
                solar_path=Path(solar_path) if solar_path else None,
            )

        self.project_name = self.config.project_name
        self.mode = self.config.optimization_mode
        self.enable_sec19_protection = self.config.enable_sec19_protection
        self.co2_tax_eur_per_ton = self.config.co2_tax_eur_per_ton
        self.wacc = self.config.wacc

        # Extract fixed sizing capacities
        self.pv_capacity_kwp = self.config.fixed_components_sizing.pv
        self.bess_capacity_kwh = self.config.fixed_components_sizing.bess
        self.hthp_capacity_kw_th = self.config.fixed_components_sizing.hthp
        self.tes_capacity_kwh_th = self.config.fixed_components_sizing.tes
        self.cap_chp_el = self.config.fixed_components_sizing.chp_el
        self.cap_chp_th = self.config.fixed_components_sizing.chp_th
        self.cap_gas_boiler = self.config.fixed_components_sizing.gas_boiler
        self.cap_eboiler = self.config.fixed_components_sizing.eboiler

        base_data_dir = Path(__file__).parent.parent / "data"

        if df_market is not None:
            self.df_market = df_market.copy()
        else:
            m_path = self.config.market_path or (Path(market_path) if market_path else base_data_dir / "market_data_2025.csv")
            self.df_market = pd.read_csv(m_path, index_col=0, parse_dates=True)

        # Sanitize market index to clean timezone-naive DatetimeIndex
        self.df_market.index = pd.to_datetime(self.df_market.index, utc=True).tz_localize(None)

        if df_solar is not None:
            self.df_solar = df_solar.copy()
        else:
            s_path = self.config.solar_path or (Path(solar_path) if solar_path else base_data_dir / "solar_data_duesseldorf_2025.csv")
            self.df_solar = pd.read_csv(s_path, index_col=0, parse_dates=True)

        # Sanitize solar index to clean timezone-naive DatetimeIndex
        self.df_solar.index = pd.to_datetime(self.df_solar.index, utc=True).tz_localize(None)

        # Load component specifications from TOML configs
        comp_dir = components_dir or DEFAULT_COMPONENTS_DIR
        self.comp_cfg = load_component_config(comp_dir)

        # Allow direct kwarg overrides if config was not explicitly provided
        if config is None:
            self.pv_capacity_kwp = pv_capacity_kwp
            self.bess_capacity_kwh = bess_capacity_kwh
            self.hthp_capacity_kw_th = hthp_capacity_kw_th
            self.tes_capacity_kwh_th = tes_capacity_kwh_th

        # Model state
        self.solph_es: Optional[solph.EnergySystem] = None
        self.model = None
        self.df_flows: Optional[pd.DataFrame] = None
        self.solution_meta: Optional[Dict[str, Any]] = None


    def build_energy_system(self, timesteps: Optional[int] = None, **kwargs) -> solph.EnergySystem:
        """
        Constructs the oemof.solph EnergySystem graph derived from config start_time and end_time.
        Dynamically filters and adds ONLY active components specified in fixed_components_sizing
        and variable_components_sizing, and ONLY the buses attached to active components.
        """
        start_dt = parse_config_date(self.config.start_time)
        end_dt = parse_config_date(self.config.end_time)

        df_m = self.df_market.loc[start_dt:end_dt]
        df_s = self.df_solar.loc[start_dt:end_dt]

        if df_m.empty:
            df_m = self.df_market.iloc[: (timesteps if timesteps else 168)]
            df_s = self.df_solar.iloc[: (timesteps if timesteps else 168)]
        elif timesteps is not None and timesteps < len(df_m):
            df_m = df_m.iloc[:timesteps]
            df_s = df_s.iloc[:timesteps]

        self._active_df_m = df_m
        self._active_df_s = df_s

        timeindex = pd.date_range(
            start=df_m.index[0], periods=len(df_m) + 1, freq="h"
        )

        es = solph.EnergySystem(timeindex=timeindex, infer_last_interval=False)

        # -------------------------------------------------------
        # 1. BUSES DEFINITION
        # -------------------------------------------------------
        b_elec = buses.Bus(label="b_elec")
        b_gas = buses.Bus(label="b_gas")
        b_steam_ht = buses.Bus(label="b_steam_ht")  # High-Temp Steam (16 bar)
        b_heat_lt = buses.Bus(label="b_heat_lt")     # Mid-Temp Process Heat (80 deg C)

        active_components = []
        active_buses = set()

        # -------------------------------------------------------
        # 2. BASELINE GRID SOURCES (Always Included)
        # -------------------------------------------------------
        if self.enable_sec19_protection:
            grid_elec_cost = np.asarray(df_m["elec_total_sec19_eur_mwh"], dtype=float) / 1000.0
        else:
            grid_elec_cost = np.asarray(df_m["elec_total_standard_eur_mwh"], dtype=float) / 1000.0

        grid_elec = components.Source(
            label="grid_electricity",
            outputs={b_elec: flows.Flow(variable_costs=grid_elec_cost)}
        )

        gas_cost_eur_mwh = (
            np.asarray(df_m["gas_spot_eur_mwh"], dtype=float)
            + (self.co2_tax_eur_per_ton * GAS_EMISSION_FACTOR_T_PER_MWH)
        )
        gas_cost_eur_kwh = gas_cost_eur_mwh / 1000.0

        grid_gas = components.Source(
            label="grid_gas",
            outputs={b_gas: flows.Flow(variable_costs=gas_cost_eur_kwh)}
        )

        active_components.extend([grid_elec, grid_gas])
        active_buses.update([b_elec, b_gas])

        # -------------------------------------------------------
        # 3. SOLAR PV (Fixed Existing & Candidate Expansion)
        # -------------------------------------------------------
        pv_normalized = compute_pv_normalized_yield(df_s)
        pv_cfg = self.comp_cfg.pv

        # Fixed PV Asset
        if self.pv_capacity_kwp > 0:
            pv_fixed = components.Source(
                label="solar_pv_fixed",
                outputs={
                    b_elec: flows.Flow(
                        fix=pv_normalized,
                        nominal_capacity=self.pv_capacity_kwp,
                    )
                },
            )
            active_components.append(pv_fixed)
            active_buses.add(b_elec)

        # Variable PV Investment Expansion Asset
        if self.mode == "investment" and self.config.variable_components_sizing.pv.enabled and self.config.variable_components_sizing.pv.max_capacity > 0:
            eac_pv = economics.annuity(
                capex=pv_cfg.capex_eur_per_kw,
                n=pv_cfg.lifetime_years,
                wacc=self.wacc,
            ) / 8760.0
            pv_expansion = components.Source(
                label="solar_pv_expansion",
                outputs={
                    b_elec: flows.Flow(
                        fix=pv_normalized,
                        nominal_capacity=solph.Investment(
                            ep_costs=eac_pv,
                            maximum=pv_cfg.max_capacity_kw,
                            minimum=self.config.variable_components_sizing.pv.min_capacity,
                        ),
                    )
                },
            )
            active_components.append(pv_expansion)
            active_buses.add(b_elec)

        # -------------------------------------------------------
        # 4. CONVERTERS (CHP, Boilers, Heat Pumps, Heat Exchangers)
        # -------------------------------------------------------
        chp_cfg = self.comp_cfg.chp
        # Fixed Existing CHP
        if self.cap_chp_el > 0 or self.cap_chp_th > 0:
            chp_fixed = components.Converter(
                label="gas_chp_fixed",
                inputs={b_gas: flows.Flow()},
                outputs={
                    b_elec: flows.Flow(nominal_capacity=self.cap_chp_el),
                    b_steam_ht: flows.Flow(nominal_capacity=self.cap_chp_th),
                },
                conversion_factors={
                    b_elec: chp_cfg.electrical_efficiency,
                    b_steam_ht: chp_cfg.thermal_efficiency,
                },
            )
            active_components.append(chp_fixed)
            active_buses.update([b_gas, b_elec, b_steam_ht])

        # Variable CHP Investment Expansion
        if self.mode == "investment" and self.config.variable_components_sizing.chp.enabled and self.config.variable_components_sizing.chp.max_capacity > 0:
            eac_chp = economics.annuity(
                capex=chp_cfg.capex_eur_per_kw_el,
                n=chp_cfg.lifetime_years,
                wacc=self.wacc,
            ) / 8760.0
            chp_expansion = components.Converter(
                label="gas_chp_expansion",
                inputs={b_gas: flows.Flow()},
                outputs={
                    b_elec: flows.Flow(
                        nominal_capacity=solph.Investment(
                            ep_costs=eac_chp,
                            maximum=self.config.variable_components_sizing.chp.max_capacity,
                            minimum=self.config.variable_components_sizing.chp.min_capacity,
                        )
                    ),
                    b_steam_ht: flows.Flow(),
                },
                conversion_factors={
                    b_elec: chp_cfg.electrical_efficiency,
                    b_steam_ht: chp_cfg.thermal_efficiency,
                },
            )
            active_components.append(chp_expansion)
            active_buses.update([b_gas, b_elec, b_steam_ht])

        # Fixed Existing Gas Boiler
        if self.cap_gas_boiler > 0:
            gas_boiler_fixed = components.Converter(
                label="gas_boiler_fixed",
                inputs={b_gas: flows.Flow()},
                outputs={b_steam_ht: flows.Flow(nominal_capacity=self.cap_gas_boiler)},
                conversion_factors={b_steam_ht: 0.92},
            )
            active_components.append(gas_boiler_fixed)
            active_buses.update([b_gas, b_steam_ht])

        # Variable Gas Boiler Investment Expansion
        if self.mode == "investment" and self.config.variable_components_sizing.gas_boiler.enabled and self.config.variable_components_sizing.gas_boiler.max_capacity > 0:
            eac_gb = economics.annuity(
                capex=100.0,  # EUR/kW_th reference capex
                n=25,
                wacc=self.wacc,
            ) / 8760.0
            gas_boiler_expansion = components.Converter(
                label="gas_boiler_expansion",
                inputs={b_gas: flows.Flow()},
                outputs={
                    b_steam_ht: flows.Flow(
                        nominal_capacity=solph.Investment(
                            ep_costs=eac_gb,
                            maximum=self.config.variable_components_sizing.gas_boiler.max_capacity,
                            minimum=self.config.variable_components_sizing.gas_boiler.min_capacity,
                        )
                    )
                },
                conversion_factors={b_steam_ht: 0.92},
            )
            active_components.append(gas_boiler_expansion)
            active_buses.update([b_gas, b_steam_ht])

        eboiler_cfg = self.comp_cfg.eboiler
        # Fixed Existing Electric Boiler
        if self.cap_eboiler > 0:
            eboiler_fixed = components.Converter(
                label="electric_boiler_fixed",
                inputs={b_elec: flows.Flow()},
                outputs={
                    b_steam_ht: flows.Flow(
                        nominal_capacity=self.cap_eboiler,
                    )
                },
                conversion_factors={
                    b_steam_ht: eboiler_cfg.thermal_efficiency,
                },
            )
            active_components.append(eboiler_fixed)
            active_buses.update([b_elec, b_steam_ht])

        # Variable Electric Boiler Investment Expansion
        if self.mode == "investment" and self.config.variable_components_sizing.eboiler.enabled and self.config.variable_components_sizing.eboiler.max_capacity > 0:
            eac_eb = economics.annuity(
                capex=eboiler_cfg.capex_eur_per_kw_th,
                n=eboiler_cfg.lifetime_years,
                wacc=self.wacc,
            ) / 8760.0
            eboiler_expansion = components.Converter(
                label="electric_boiler_expansion",
                inputs={b_elec: flows.Flow()},
                outputs={
                    b_steam_ht: flows.Flow(
                        nominal_capacity=solph.Investment(
                            ep_costs=eac_eb,
                            maximum=self.config.variable_components_sizing.eboiler.max_capacity,
                            minimum=self.config.variable_components_sizing.eboiler.min_capacity,
                        )
                    )
                },
                conversion_factors={
                    b_steam_ht: eboiler_cfg.thermal_efficiency,
                },
            )
            active_components.append(eboiler_expansion)
            active_buses.update([b_elec, b_steam_ht])

        steam_to_heat = components.Converter(
            label="steam_to_heat_exchanger",
            inputs={b_steam_ht: flows.Flow()},
            outputs={b_heat_lt: flows.Flow(nominal_capacity=100000.0)},
            conversion_factors={b_heat_lt: 0.98},
        )
        active_components.append(steam_to_heat)
        active_buses.update([b_steam_ht, b_heat_lt])

        hthp_cfg = self.comp_cfg.hthp
        hthp_cop = hthp_cfg.cop

        # Fixed HTHP Asset
        if self.hthp_capacity_kw_th > 0:
            hthp_fixed = components.Converter(
                label="heat_pump_fixed",
                inputs={b_elec: flows.Flow()},
                outputs={
                    b_heat_lt: flows.Flow(nominal_capacity=self.hthp_capacity_kw_th)
                },
                conversion_factors={b_heat_lt: hthp_cop},
            )
            active_components.append(hthp_fixed)
            active_buses.update([b_elec, b_heat_lt])

        # Variable HTHP Expansion Asset
        if self.mode == "investment" and self.config.variable_components_sizing.hthp.enabled and self.config.variable_components_sizing.hthp.max_capacity > 0:
            eac_hthp = economics.annuity(
                capex=hthp_cfg.capex_eur_per_kw_th,
                n=hthp_cfg.lifetime_years,
                wacc=self.wacc,
            ) / 8760.0
            hthp_expansion = components.Converter(
                label="heat_pump_expansion",
                inputs={b_elec: flows.Flow()},
                outputs={
                    b_heat_lt: flows.Flow(
                        nominal_capacity=solph.Investment(
                            ep_costs=eac_hthp,
                            maximum=hthp_cfg.max_capacity_kw_th,
                            minimum=self.config.variable_components_sizing.hthp.min_capacity,
                        )
                    )
                },
                conversion_factors={b_heat_lt: hthp_cop},
            )
            active_components.append(hthp_expansion)
            active_buses.update([b_elec, b_heat_lt])

        # -------------------------------------------------------
        # 5. STORAGE (BESS & Thermal Energy Storage)
        # -------------------------------------------------------
        bess_cfg = self.comp_cfg.bess
        c_rate = bess_cfg.c_rate

        # Fixed BESS Asset
        if self.bess_capacity_kwh > 0:
            bess_power = self.bess_capacity_kwh * c_rate
            bess_fixed = components.GenericStorage(
                label="bess_fixed",
                nominal_capacity=self.bess_capacity_kwh,
                inputs={b_elec: flows.Flow(nominal_capacity=bess_power)},
                outputs={b_elec: flows.Flow(nominal_capacity=bess_power)},
                loss_rate=bess_cfg.self_discharge_rate_per_hour,
                inflow_conversion_factor=bess_cfg.charge_efficiency,
                outflow_conversion_factor=bess_cfg.discharge_efficiency,
            )
            active_components.append(bess_fixed)
            active_buses.add(b_elec)

        # Variable BESS Expansion Asset
        if self.mode == "investment" and self.config.variable_components_sizing.bess.enabled and self.config.variable_components_sizing.bess.max_capacity > 0:
            eac_bess = economics.annuity(
                capex=bess_cfg.capex_eur_per_kwh,
                n=bess_cfg.lifetime_years,
                wacc=self.wacc,
            ) / 8760.0
            bess_expansion = components.GenericStorage(
                label="bess_expansion",
                nominal_capacity=solph.Investment(
                    ep_costs=eac_bess,
                    maximum=bess_cfg.max_capacity_kwh,
                    minimum=self.config.variable_components_sizing.bess.min_capacity,
                ),
                inputs={b_elec: flows.Flow()},
                outputs={b_elec: flows.Flow()},
                loss_rate=bess_cfg.self_discharge_rate_per_hour,
                inflow_conversion_factor=bess_cfg.charge_efficiency,
                outflow_conversion_factor=bess_cfg.discharge_efficiency,
            )
            active_components.append(bess_expansion)
            active_buses.add(b_elec)

        tes_cfg = self.comp_cfg.tes

        # Fixed TES Asset
        if self.tes_capacity_kwh_th > 0:
            tes_power = self.tes_capacity_kwh_th / 4.0
            tes_fixed = components.GenericStorage(
                label="tes_fixed",
                nominal_capacity=self.tes_capacity_kwh_th,
                inputs={b_heat_lt: flows.Flow(nominal_capacity=tes_power)},
                outputs={b_heat_lt: flows.Flow(nominal_capacity=tes_power)},
                loss_rate=0.005,
                inflow_conversion_factor=0.98,
                outflow_conversion_factor=0.98,
            )
            active_components.append(tes_fixed)
            active_buses.add(b_heat_lt)

        # Variable TES Expansion Asset
        if self.mode == "investment" and self.config.variable_components_sizing.tes.enabled and self.config.variable_components_sizing.tes.max_capacity > 0:
            eac_tes = economics.annuity(
                capex=tes_cfg.capex_eur_per_kwh_th,
                n=tes_cfg.lifetime_years,
                wacc=self.wacc,
            ) / 8760.0
            tes_expansion = components.GenericStorage(
                label="tes_expansion",
                nominal_capacity=solph.Investment(
                    ep_costs=eac_tes,
                    maximum=tes_cfg.max_capacity_kwh_th,
                    minimum=self.config.variable_components_sizing.tes.min_capacity,
                ),
                inputs={b_heat_lt: flows.Flow()},
                outputs={b_heat_lt: flows.Flow()},
                loss_rate=0.005,
                inflow_conversion_factor=0.98,
                outflow_conversion_factor=0.98,
            )
            active_components.append(tes_expansion)
            active_buses.add(b_heat_lt)

        # -------------------------------------------------------
        # 6. SINKS (Demands on Active Buses)
        # -------------------------------------------------------
        if b_elec in active_buses:
            demand_elec = components.Sink(
                label="demand_elec",
                inputs={b_elec: flows.Flow(nominal_capacity=60000.0, fix=1.0)}
            )
            active_components.append(demand_elec)

        if b_steam_ht in active_buses:
            demand_steam = components.Sink(
                label="demand_steam",
                inputs={b_steam_ht: flows.Flow(nominal_capacity=160000.0, fix=1.0)}
            )
            active_components.append(demand_steam)

        if b_heat_lt in active_buses:
            demand_heat = components.Sink(
                label="demand_heat",
                inputs={b_heat_lt: flows.Flow(nominal_capacity=60000.0, fix=1.0)}
            )
            active_components.append(demand_heat)

        # Add active buses and active components to energy system
        es.add(*active_buses, *active_components)

        self.solph_es = es
        return es

    def solve(self, solver_name: str = "appsi_highs", timesteps: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """
        Builds the oemof.solph Model and invokes the solver using oemof convention.
        Default solver is APPSI HiGHS (via highspy). Returns optimization results
        dictionary including cost metrics, solver metadata, and CO2 tracking.
        """
        if self.solph_es is None:
            self.build_energy_system(timesteps=timesteps)

        assert self.solph_es is not None
        self.model = solph.Model(self.solph_es)

        # Remove None suffix placeholders (dual, slack, rc) to prevent Pyomo APPSI None.import_enabled() AttributeError
        for attr in ("dual", "slack", "rc"):
            if hasattr(self.model, attr) and getattr(self.model, attr) is None:
                delattr(self.model, attr)

        # Map 'highs' to Pyomo APPSI HiGHS interface for highspy compatibility
        actual_solver = "appsi_highs" if solver_name in ("highs", "appsi_highs") else solver_name

        if actual_solver == "appsi_highs":
            solver = po.SolverFactory("appsi_highs")
            solver.solve(self.model)
            # Re-assign None placeholders so solph.processing.results checks pass safely
            self.model.dual = None
            self.model.slack = None
            self.model.rc = None
        else:
            self.model.solve(solver=actual_solver, solve_kwargs={"tee": True})

        # Extract objective value and solver metadata via oemof utility
        try:
            meta = solph.processing.meta_results(self.model)
            total_cost_eur = float(meta.get("objective", po.value(self.model.objective)))
        except Exception:
            meta = {"objective": po.value(self.model.objective)}
            total_cost_eur = float(meta["objective"])

        df_m = getattr(self, "_active_df_m", self.df_market.iloc[:168])
        hours = len(df_m)

        # 450,000 tons/year at 8760 hours -> tons per hour * hours simulated
        annual_production_tons = (450000.0 / 8760.0) * hours
        cost_per_ton = total_cost_eur / annual_production_tons

        # Vectorized flow extraction using solph.processing.results
        results = solph.processing.results(self.model)
        flow_data: Dict[str, Any] = {}
        for (i, o), df_res in results.items():
            if hasattr(i, "label") and hasattr(o, "label"):
                flow_key = f"{i.label} -> {o.label}"
                if "sequences" in df_res and "flow" in df_res["sequences"].columns:
                    flow_series = df_res["sequences"]["flow"].iloc[:hours].values
                    flow_data[flow_key] = flow_series

        self.df_flows = pd.DataFrame(flow_data, index=df_m.index)

        # Post-processing: CO2 emission tracking
        co2_results = self._compute_co2_emissions(hours)

        self.solution_meta = {
            "total_cost_eur": total_cost_eur,
            "cost_per_ton_eur": cost_per_ton,
            "timesteps": hours,
            "mode": self.mode,
            "solver_meta": meta,  # Full solver metadata for summary table
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
