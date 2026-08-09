"""
PyPSA (Python for Power System Analysis) Energy System Model
for Henkel Düsseldorf Holthausen Flagship Manufacturing Site.

Models dual-temperature thermal quality (High-Temp Steam vs Mid-Temp Process Heat),
configurable grid fee scenarios, CHP, Electric Boilers,
Industrial Heat Pumps, PV, BESS, and Thermal Energy Storage (TES).

Component specifications are loaded from TOML config files in data/components/
and built using modular OOP component classes in src/components/.
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

import logging
import pandas as pd
import numpy as np
import pypsa
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from .components import (
    GridElectricityComponent,
    GridGasComponent,
    GridElectricityConfig,
    GridGasConfig,
    GridExportComponent,
    GridExportConfig,
    PVPPAComponent,
    WindPPAComponent,
    PVPPAConfig,
    WindPPAConfig,
    PVComponent,
    PVComponentConfig,
    compute_pv_normalized_yield,
    GasCHPComponent,
    CHPComponentConfig,
    GasBoilerComponent,
    EBoilerComponent,
    SteamHeatExchangerComponent,
    GasBoilerConfig,
    EBoilerConfig,
    SteamHeatExchangerConfig,
    HTHPComponent,
    HTHPComponentConfig,
    BESSComponent,
    TESComponent,
    BESSComponentConfig,
    TESComponentConfig,
    add_storage_inverter_constraint,
    DemandComponent,
    DemandConfig,
)

# Default path to component configuration directory
DEFAULT_COMPONENTS_DIR = Path(__file__).parent.parent / "data" / "components"

# Default fallback timestep slice (168 hours = 1 week)
DEFAULT_FALLBACK_TIMESTEPS = 168

# Emission factors (tCO2 per MWh)
GAS_EMISSION_FACTOR_T_PER_MWH = 0.201
GRID_ELEC_EMISSION_FACTOR_T_PER_MWH = 0.38


# -----------------------------------------------------------------------------
# CONFIGURATION SCHEMAS (Pydantic Models)
# -----------------------------------------------------------------------------
class FixedSizingConfig(BaseModel):
    """Configuration for fixed existing/installed asset capacities (kW or kWh) and demand overrides."""
    pv: float = Field(default=0.0, ge=0.0, description="Rooftop PV installed capacity in kWp")
    pv_ppa: float = Field(default=0.0, ge=0.0, description="PV PPA contract capacity in kW")
    wind_ppa: float = Field(default=0.0, ge=0.0, description="Wind PPA contract capacity in kW")
    bess: float = Field(default=0.0, ge=0.0, description="Battery Storage capacity in kWh")
    hthp: float = Field(default=15000.0, ge=0.0, description="High-Temp Heat Pump thermal capacity in kW_th")
    tes: float = Field(default=20000.0, ge=0.0, description="Thermal Energy Storage capacity in kWh_th")
    chp_el: float = Field(default=30000.0, ge=0.0, description="Existing CHP electrical capacity in kW")
    chp_th: float = Field(default=30000.0, ge=0.0, description="Existing CHP thermal capacity in kW")
    gas_boiler: float = Field(default=180000.0, ge=0.0, description="Existing Gas Boiler thermal capacity in kW")
    eboiler: float = Field(default=25000.0, ge=0.0, description="Existing Electric Boiler thermal capacity in kW")
    demand_elec_mw: Optional[float] = Field(default=None, ge=0.0, description="Electrical continuous baseload demand override in MW")
    demand_steam_mw_th: Optional[float] = Field(default=None, ge=0.0, description="High-temp steam demand override in MW_th")
    demand_heat_mw_th: Optional[float] = Field(default=None, ge=0.0, description="Mid-temp process heat demand override in MW_th")



class ComponentBounds(BaseModel):
    """Investment optimization bounds for a single asset."""
    enabled: bool = Field(default=True, description="Whether asset is eligible for investment sizing")
    min_capacity: float = Field(default=0.0, ge=0.0, description="Minimum capacity bound")
    max_capacity: float = Field(default=50000.0, ge=0.0, description="Maximum capacity bound")


class VariableSizingConfig(BaseModel):
    """Configuration for variable investment candidate assets."""
    pv: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=True, min_capacity=0.0, max_capacity=25000.0))
    pv_ppa: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=True, min_capacity=0.0, max_capacity=50000.0))
    wind_ppa: ComponentBounds = Field(default_factory=lambda: ComponentBounds(enabled=True, min_capacity=0.0, max_capacity=50000.0))
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
    pv_ppa_strike_price_eur_per_mwh: Optional[float] = Field(default=None, ge=0.0, description="Optional PV PPA strike price override (€/MWh)")
    wind_ppa_strike_price_eur_per_mwh: Optional[float] = Field(default=None, ge=0.0, description="Optional Wind PPA strike price override (€/MWh)")
    co2_tax_eur_per_ton: float = Field(default=85.0, ge=0.0)
    enable_sec19_protection: bool = Field(default=True)
    wacc: float = Field(default=0.07, ge=0.0, le=0.30)
    market_path: Optional[Path] = None
    solar_path: Optional[Path] = None


# -----------------------------------------------------------------------------
# COMPONENT TOML CONFIG LOADERS
# -----------------------------------------------------------------------------
class ComponentConfigs(BaseModel):
    """Container holding all validated component configurations from TOML."""
    pv: PVComponentConfig
    pv_ppa: PVPPAConfig = Field(default_factory=PVPPAConfig)
    wind_ppa: WindPPAConfig = Field(default_factory=WindPPAConfig)
    bess: BESSComponentConfig
    chp: CHPComponentConfig
    eboiler: EBoilerConfig
    hthp: HTHPComponentConfig
    tes: TESComponentConfig = Field(default_factory=TESComponentConfig)
    demand: DemandConfig = Field(default_factory=DemandConfig)



def parse_config_date(date_str: str) -> pd.Timestamp:
    """Parses date string supporting DD/MM/YYYY, YYYY-MM-DD, and ISO datetime strings."""
    try:
        return pd.to_datetime(date_str, dayfirst=True)
    except Exception:
        return pd.to_datetime(date_str)


def load_component_config(components_dir: Path = DEFAULT_COMPONENTS_DIR) -> ComponentConfigs:
    """Loads all TOML config files from the components directory and validates with Pydantic."""
    raw_configs: Dict[str, Dict] = {}
    for toml_path in sorted(components_dir.glob("*.toml")):
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        section_name = list(data.keys())[0]
        raw_configs[section_name] = data[section_name]

    model_map = {
        "pv": PVComponentConfig,
        "bess": BESSComponentConfig,
        "chp": CHPComponentConfig,
        "eboiler": EBoilerConfig,
        "hthp": HTHPComponentConfig,
    }

    validated: Dict[str, Any] = {}
    for name, model_cls in model_map.items():
        raw_data = raw_configs.get(name)
        if raw_data is None:
            raise FileNotFoundError(
                f"Missing TOML config for component '{name}'. Expected: {components_dir / f'{name}.toml'}"
            )
        validated[name] = model_cls(**raw_data)

    if "pv_ppa" in raw_configs:
        validated["pv_ppa"] = PVPPAConfig(**raw_configs["pv_ppa"])
    else:
        validated["pv_ppa"] = PVPPAConfig()

    if "wind_ppa" in raw_configs:
        validated["wind_ppa"] = WindPPAConfig(**raw_configs["wind_ppa"])
    else:
        validated["wind_ppa"] = WindPPAConfig()

    if "tes" in raw_configs:
        validated["tes"] = TESComponentConfig(**raw_configs["tes"])
    else:
        validated["tes"] = TESComponentConfig()

    if "demand" in raw_configs:
        validated["demand"] = DemandConfig(**raw_configs["demand"])
    else:
        validated["demand"] = DemandConfig()

    return ComponentConfigs(**validated)


# -----------------------------------------------------------------------------
# PYPSA HENKEL ENERGY SYSTEM CLASS
# -----------------------------------------------------------------------------
class HenkelEnergySystem:
    """
    Object-Oriented PyPSA Framework for Henkel Düsseldorf Holthausen Energy System Optimization.
    Supports Operational Dispatch Sizing and Investment Sizing using PyPSA Network architecture.
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

        # Fixed sizing capacities
        self.pv_capacity_kwp = self.config.fixed_components_sizing.pv
        self.pv_ppa_capacity_kw = self.config.fixed_components_sizing.pv_ppa
        self.wind_ppa_capacity_kw = self.config.fixed_components_sizing.wind_ppa
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

        self.df_market.index = pd.to_datetime(self.df_market.index, utc=True).tz_localize(None)

        if df_solar is not None:
            self.df_solar = df_solar.copy()
        else:
            s_path = self.config.solar_path or (Path(solar_path) if solar_path else base_data_dir / "solar_data_duesseldorf_2025.csv")
            self.df_solar = pd.read_csv(s_path, index_col=0, parse_dates=True)

        self.df_solar.index = pd.to_datetime(self.df_solar.index, utc=True).tz_localize(None)

        comp_dir = components_dir or DEFAULT_COMPONENTS_DIR
        self.comp_cfg = load_component_config(comp_dir)

        # Apply PPA strike price overrides from FacilityProjectConfig if specified
        if self.config.pv_ppa_strike_price_eur_per_mwh is not None:
            self.comp_cfg.pv_ppa.strike_price_eur_per_mwh = self.config.pv_ppa_strike_price_eur_per_mwh
        if self.config.wind_ppa_strike_price_eur_per_mwh is not None:
            self.comp_cfg.wind_ppa.strike_price_eur_per_mwh = self.config.wind_ppa_strike_price_eur_per_mwh

        # Active continuous electrical demand attribute (MW)
        self.demand_elec_mw = (
            self.config.fixed_components_sizing.demand_elec_mw
            if self.config.fixed_components_sizing.demand_elec_mw is not None
            else self.comp_cfg.demand.elec_demand_mw
        )

        # PyPSA network and solution state
        self.network: Optional[pypsa.Network] = None
        self.results: Optional[Dict[str, Any]] = None

    def build_energy_system(self, timesteps: Optional[int] = None, **kwargs) -> pypsa.Network:
        """Constructs the PyPSA Network derived from config start_time and end_time using src/components."""
        start_dt = parse_config_date(self.config.start_time)
        end_dt = parse_config_date(self.config.end_time)

        df_m = self.df_market.loc[start_dt:end_dt]
        df_s = self.df_solar.loc[start_dt:end_dt]

        if df_m.empty:
            fallback_ts = timesteps if timesteps else DEFAULT_FALLBACK_TIMESTEPS
            logger.warning(
                "Date slicing for window %s to %s returned empty dataset. Falling back to first %d timesteps.",
                self.config.start_time,
                self.config.end_time,
                fallback_ts,
            )
            df_m = self.df_market.iloc[:fallback_ts]
            df_s = self.df_solar.iloc[:fallback_ts]
        elif timesteps is not None and timesteps < len(df_m):
            df_m = df_m.iloc[:timesteps]
            df_s = df_s.iloc[:timesteps]

        self._active_df_m = df_m
        self._active_df_s = df_s

        n = pypsa.Network()
        n.set_snapshots(df_m.index)

        # PyPSA snapshot weightings discipline
        n.snapshot_weightings["generators"] = 1.0
        n.snapshot_weightings["stores"] = 1.0
        num_snapshots = len(df_m)
        if self.mode == "investment" and num_snapshots > 0:
            annual_scale = 8760.0 / num_snapshots
            n.snapshot_weightings["objective"] = annual_scale
        else:
            n.snapshot_weightings["objective"] = 1.0

        # Add carrier buses with Henkel Düsseldorf Holthausen coordinates (x=longitude, y=latitude)
        n.add("Bus", "b_elec", carrier="electricity", x=6.8320, y=51.1720)
        n.add("Bus", "b_gas", carrier="gas", x=6.8310, y=51.1710)
        n.add("Bus", "b_steam_ht", carrier="steam_ht", x=6.8340, y=51.1730)
        n.add("Bus", "b_heat_lt", carrier="heat_lt", x=6.8350, y=51.1715)

        # 1. Grid Electricity and Natural Gas Import Components
        grid_p_nom = 1.25 * self.demand_elec_mw * 1000.0 if self.enable_sec19_protection else 1e6
        grid_elec_cfg = GridElectricityConfig(p_nom=grid_p_nom)

        if self.enable_sec19_protection:
            grid_elec_cost_kwh = np.asarray(df_m["elec_total_sec19_eur_mwh"], dtype=float) / 1000.0
        else:
            grid_elec_cost_kwh = np.asarray(df_m["elec_total_standard_eur_mwh"], dtype=float) / 1000.0

        grid_elec = GridElectricityComponent(
            price_series=pd.Series(grid_elec_cost_kwh, index=df_m.index),
            config=grid_elec_cfg,
        )
        #If the user enables CO2 tax config, then additional gas cost calculation will be proceeded, if not, then the total gas cost (CO2 included) will be used
        grid_elec.build_component(n, wacc=self.wacc)
        if self.co2_tax_eur_per_ton:
            gas_cost_eur_kwh = (
                np.asarray(df_m["gas_spot_eur_mwh"], dtype=float)
                + (self.co2_tax_eur_per_ton * GAS_EMISSION_FACTOR_T_PER_MWH)
            ) / 1000.0
        else:
            gas_cost_eur_kwh = (  np.asarray(df_m["gas_total_eur_mwh"], dtype=float)   ) / 1000.0

        grid_gas = GridGasComponent(price_series=pd.Series(gas_cost_eur_kwh, index=df_m.index))
        grid_gas.build_component(n, wacc=self.wacc)

        # Grid Export Component (Selling surplus electricity back to grid at wholesale spot price)
        spot_price_series = pd.Series(np.asarray(df_m["elec_spot_eur_mwh"], dtype=float), index=df_m.index)
        grid_export = GridExportComponent(spot_price_series=spot_price_series)
        grid_export.build_component(n, wacc=self.wacc)

        # 2. Demand Sinks (configurable via demand.toml and FixedSizingConfig)
        demand_cfg = self.comp_cfg.demand.model_copy()
        if self.config.fixed_components_sizing.demand_elec_mw is not None:
            demand_cfg.elec_demand_mw = self.config.fixed_components_sizing.demand_elec_mw
        if self.config.fixed_components_sizing.demand_steam_mw_th is not None:
            demand_cfg.steam_demand_mw_th = self.config.fixed_components_sizing.demand_steam_mw_th
        if self.config.fixed_components_sizing.demand_heat_mw_th is not None:
            demand_cfg.heat_demand_mw_th = self.config.fixed_components_sizing.demand_heat_mw_th

        demand = DemandComponent(demand_cfg)
        demand.build_component(n)

        # Emergency Zero-Cost Thermal Heat Dump Generators (absorbs excess heat at EUR 0.0 marginal cost)
        n.add(
            "Generator",
            "steam_dump",
            bus="b_steam_ht",
            p_nom=1e6,
            p_min_pu=-1.0,
            p_max_pu=0.0,
            marginal_cost=0.0,
        )
        n.add(
            "Generator",
            "heat_dump",
            bus="b_heat_lt",
            p_nom=1e6,
            p_min_pu=-1.0,
            p_max_pu=0.0,
            marginal_cost=0.0,
        )

        # 3. Solar PV Generator & PPA Generators
        is_pv_ext = (self.mode == "investment") and self.config.variable_components_sizing.pv.enabled
        pv_cfg = PVComponentConfig(
            installed_capacity_kw=self.pv_capacity_kwp,
            is_extendable=is_pv_ext,
            max_capacity_kw=self.config.variable_components_sizing.pv.max_capacity if is_pv_ext else 25000.0,
            capex_eur_per_kw=self.comp_cfg.pv.capex_eur_per_kw,
            opex_eur_per_kw_year=self.comp_cfg.pv.opex_eur_per_kw_year,
            lifetime_years=self.comp_cfg.pv.lifetime_years,
        )
        pv_comp = PVComponent(config=pv_cfg, df_solar=df_s)
        pv_comp.build_component(n, wacc=self.wacc)

        # 3b. PV PPA Component
        is_pv_ppa_ext = (self.mode == "investment") and self.config.variable_components_sizing.pv_ppa.enabled
        pv_ppa_cfg = PVPPAConfig(
            installed_capacity_kw=self.pv_ppa_capacity_kw,
            is_extendable=is_pv_ppa_ext,
            max_capacity_kw=self.config.variable_components_sizing.pv_ppa.max_capacity if is_pv_ppa_ext else 50000.0,
            strike_price_eur_per_mwh=self.comp_cfg.pv_ppa.strike_price_eur_per_mwh,
            annual_fee_eur_per_kw_year=self.comp_cfg.pv_ppa.annual_fee_eur_per_kw_year,
        )
        pv_profile = df_s["pv_normalized_yield"] if "pv_normalized_yield" in df_s.columns else pd.Series(pv_comp.compute_pv_normalized_yield(df_s), index=df_s.index)
        pv_ppa_comp = PVPPAComponent(pv_profile=pv_profile, config=pv_ppa_cfg)
        pv_ppa_comp.build_component(n, wacc=self.wacc)

        # 3c. Wind PPA Component
        is_wind_ppa_ext = (self.mode == "investment") and self.config.variable_components_sizing.wind_ppa.enabled
        wind_ppa_cfg = WindPPAConfig(
            installed_capacity_kw=self.wind_ppa_capacity_kw,
            is_extendable=is_wind_ppa_ext,
            max_capacity_kw=self.config.variable_components_sizing.wind_ppa.max_capacity if is_wind_ppa_ext else 50000.0,
            strike_price_eur_per_mwh=self.comp_cfg.wind_ppa.strike_price_eur_per_mwh,
            annual_fee_eur_per_kw_year=self.comp_cfg.wind_ppa.annual_fee_eur_per_kw_year,
        )
        if "wind_normalized_yield" in df_s.columns:
            wind_profile = df_s["wind_normalized_yield"]
        else:
            from .external_api import generate_wind_normalized_yield
            wind_profile = generate_wind_normalized_yield(df_s.index)
        wind_ppa_comp = WindPPAComponent(wind_profile=wind_profile, config=wind_ppa_cfg)
        wind_ppa_comp.build_component(n, wacc=self.wacc)

        # 4. CHP Unit (Gas -> Elec + Steam_HT)
        is_chp_ext = (self.mode == "investment") and self.config.variable_components_sizing.chp.enabled
        chp_cfg = CHPComponentConfig(
            capacity_el_kw=self.cap_chp_el,
            electrical_efficiency=self.comp_cfg.chp.electrical_efficiency,
            thermal_efficiency=self.comp_cfg.chp.thermal_efficiency,
            is_extendable=is_chp_ext,
            max_capacity_el_kw=self.config.variable_components_sizing.chp.max_capacity if is_chp_ext else 50000.0,
        )
        chp_comp = GasCHPComponent(chp_cfg)
        chp_comp.build_component(n, wacc=self.wacc)

        # 5. Boilers & Exchanger
        gb_cfg = GasBoilerConfig(
            capacity_th_kw=self.cap_gas_boiler,
            thermal_efficiency=0.92,
            is_extendable=(self.mode == "investment" and self.config.variable_components_sizing.gas_boiler.enabled),
        )
        gb_comp = GasBoilerComponent(gb_cfg)
        gb_comp.build_component(n, wacc=self.wacc)

        eb_cfg = EBoilerConfig(
            capacity_th_kw=self.cap_eboiler,
            thermal_efficiency=self.comp_cfg.eboiler.thermal_efficiency,
            is_extendable=(self.mode == "investment" and self.config.variable_components_sizing.eboiler.enabled),
        )
        eb_comp = EBoilerComponent(eb_cfg)
        eb_comp.build_component(n, wacc=self.wacc)

        hx_comp = SteamHeatExchangerComponent()
        hx_comp.build_component(n, wacc=self.wacc)

        # 6. High-Temperature Heat Pump (HTHP)
        is_hthp_ext = (self.mode == "investment") and self.config.variable_components_sizing.hthp.enabled
        hthp_cfg = HTHPComponentConfig(
            capacity_th_kw=self.hthp_capacity_kw_th,
            cop=self.comp_cfg.hthp.cop,
            is_extendable=is_hthp_ext,
            max_capacity_th_kw=self.config.variable_components_sizing.hthp.max_capacity if is_hthp_ext else 40000.0,
            capex_eur_per_kw_th=self.comp_cfg.hthp.capex_eur_per_kw_th,
            opex_eur_per_kw_th_year=self.comp_cfg.hthp.opex_eur_per_kw_th_year,
            lifetime_years=self.comp_cfg.hthp.lifetime_years,
        )
        hthp_comp = HTHPComponent(hthp_cfg)
        hthp_comp.build_component(n, wacc=self.wacc)

        # 7. Storage Units (BESS & TES)
        is_bess_ext = (self.mode == "investment") and self.config.variable_components_sizing.bess.enabled
        bess_cfg = BESSComponentConfig(
            installed_capacity_kwh=self.bess_capacity_kwh,
            is_extendable=is_bess_ext,
            max_capacity_kwh=self.config.variable_components_sizing.bess.max_capacity if is_bess_ext else 50000.0,
            capex_eur_per_kwh=self.comp_cfg.bess.capex_eur_per_kwh,
            opex_eur_per_kwh_year=self.comp_cfg.bess.opex_eur_per_kwh_year,
            lifetime_years=self.comp_cfg.bess.lifetime_years,
            charge_efficiency=self.comp_cfg.bess.charge_efficiency,
            discharge_efficiency=self.comp_cfg.bess.discharge_efficiency,
        )
        bess_comp = BESSComponent(bess_cfg)
        bess_comp.build_component(n, wacc=self.wacc)

        is_tes_ext = (self.mode == "investment") and self.config.variable_components_sizing.tes.enabled
        tes_cfg = TESComponentConfig(
            installed_capacity_kwh=self.tes_capacity_kwh_th,
            is_extendable=is_tes_ext,
            max_capacity_kwh=self.config.variable_components_sizing.tes.max_capacity if is_tes_ext else 100000.0,
            capex_eur_per_kwh=self.comp_cfg.tes.capex_eur_per_kwh,
            opex_eur_per_kwh_year=1.0,
            lifetime_years=self.comp_cfg.tes.lifetime_years,
        )
        tes_comp = TESComponent(tes_cfg)
        tes_comp.build_component(n, wacc=self.wacc)

        self.network = n
        return n

    def solve(
        self,
        solver_name: str = "highs",
        timesteps: Optional[int] = None,
        solver_options: Optional[Dict[str, Any]] = None,
        quiet: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Solves the PyPSA energy system optimization problem and synthesizes results."""
        if self.network is None:
            self.build_energy_system(timesteps=timesteps)

        n = self.network

        # Configure solver options and logging
        opts = solver_options.copy() if solver_options is not None else {}
        if quiet:
            import logging

            logging.getLogger("pypsa").setLevel(logging.ERROR)
            logging.getLogger("linopy").setLevel(logging.ERROR)
            if solver_name.lower() == "highs" and "log_to_console" not in opts:
                opts["log_to_console"] = False

        def apply_c_rate_coupling(net: pypsa.Network, snapshots: pd.Index) -> None:
            """Couples extendable storage charger/discharger link capacities to store energy capacity."""
            if "bess" in net.stores.index and getattr(net.stores.loc["bess"], "e_nom_extendable", False):
                c_rate = 0.5
                if "bess_charger" in net.links.index and "bess_discharger" in net.links.index:
                    net.model.add_constraints(
                        net.model["Link-p_nom"].loc["bess_charger"] == net.model["Store-e_nom"].loc["bess"] * c_rate,
                        name="bess_charger_c_rate",
                    )
                    net.model.add_constraints(
                        net.model["Link-p_nom"].loc["bess_discharger"] == net.model["Store-e_nom"].loc["bess"] * c_rate,
                        name="bess_discharger_c_rate",
                    )
            if "tes" in net.stores.index and getattr(net.stores.loc["tes"], "e_nom_extendable", False):
                c_rate = 0.25
                if "tes_charger" in net.links.index and "tes_discharger" in net.links.index:
                    net.model.add_constraints(
                        net.model["Link-p_nom"].loc["tes_charger"] == net.model["Store-e_nom"].loc["tes"] * c_rate,
                        name="tes_charger_c_rate",
                    )
                    net.model.add_constraints(
                        net.model["Link-p_nom"].loc["tes_discharger"] == net.model["Store-e_nom"].loc["tes"] * c_rate,
                        name="tes_discharger_c_rate",
                    )

            # Strategy C: Add continuous shared-inverter throughput exclusivity constraint
            if "bess" in net.stores.index:
                add_storage_inverter_constraint(net, "bess")
            if "tes" in net.stores.index:
                add_storage_inverter_constraint(net, "tes")

        # PyPSA Pre-Optimization Consistency Check & Sanitization
        n.sanitize()
        n.consistency_check()

        # Optimize using linopy / highs
        n.optimize(
            solver_name=solver_name,
            solver_options=opts if opts else None,
            extra_functionality=apply_c_rate_coupling,
            include_objective_constant=False,
            **kwargs,
        )

        # Calculate OPEX (operational cost of imports scaled to annual equivalent in investment mode)
        annual_weight = float(n.snapshot_weightings.objective.iloc[0]) if hasattr(n.snapshot_weightings.objective, "iloc") else float(n.snapshot_weightings.objective)
        grid_elec_p = n.generators_t.p["grid_electricity"]
        if "grid_electricity" in n.generators_t.marginal_cost.columns:
            grid_elec_mc = n.generators_t.marginal_cost["grid_electricity"]
        else:
            grid_elec_mc = n.generators.loc["grid_electricity", "marginal_cost"]
        elec_cost_total = float((grid_elec_p * grid_elec_mc).sum()) * annual_weight

        grid_gas_p = n.generators_t.p["grid_gas"]
        if "grid_gas" in n.generators_t.marginal_cost.columns:
            grid_gas_mc = n.generators_t.marginal_cost["grid_gas"]
        else:
            grid_gas_mc = n.generators.loc["grid_gas", "marginal_cost"]
        gas_cost_total = float((grid_gas_p * grid_gas_mc).sum()) * annual_weight

        pv_ppa_cost = 0.0
        if "pv_ppa" in n.generators.index:
            p_pv_ppa = n.generators_t.p["pv_ppa"]
            mc_pv_ppa = n.generators_t.marginal_cost["pv_ppa"] if "pv_ppa" in n.generators_t.marginal_cost.columns else n.generators.loc["pv_ppa", "marginal_cost"]
            pv_ppa_cost = float((p_pv_ppa * mc_pv_ppa).sum()) * annual_weight

        wind_ppa_cost = 0.0
        if "wind_ppa" in n.generators.index:
            p_wind_ppa = n.generators_t.p["wind_ppa"]
            mc_wind_ppa = n.generators_t.marginal_cost["wind_ppa"] if "wind_ppa" in n.generators_t.marginal_cost.columns else n.generators.loc["wind_ppa", "marginal_cost"]
            wind_ppa_cost = float((p_wind_ppa * mc_wind_ppa).sum()) * annual_weight

        grid_export_revenue_eur = 0.0
        grid_export_mwh = 0.0
        if "grid_export" in n.generators.index and "grid_export" in n.generators_t.p.columns:
            # PyPSA generator with p_min_pu=-1.0, p_max_pu=0.0 stores export flow as negative p (p <= 0)
            p_grid_export = np.maximum(0.0, - n.generators_t.p["grid_export"])
            spot_price_mwh = np.asarray(self.df_market.loc[n.snapshots, "elec_spot_eur_mwh"], dtype=float)
            grid_export_revenue_eur = float((p_grid_export * spot_price_mwh / 1000.0).sum()) * annual_weight
            grid_export_mwh = float(p_grid_export.sum() / 1000.0) * annual_weight

        opex_total = elec_cost_total + gas_cost_total + pv_ppa_cost + wind_ppa_cost - grid_export_revenue_eur

        # Calculate CAPEX (annualized investment costs)
        capex_total = 0.0
        if self.mode == "investment":
            # Sum capital costs of extendable generators, links, stores
            for c in ["Generator", "Link", "Store"]:
                df_comp = getattr(n, c.lower() + "s")
                if "p_nom_extendable" in df_comp.columns:
                    ext = df_comp[df_comp["p_nom_extendable"]]
                    capex_total += float((ext["p_nom_opt"] * ext["capital_cost"]).sum())
                if "e_nom_extendable" in df_comp.columns:
                    ext = df_comp[df_comp["e_nom_extendable"]]
                    capex_total += float((ext["e_nom_opt"] * ext["capital_cost"]).sum())

        total_cost = opex_total + capex_total

        # Calculate Emissions
        gas_mwh = float(grid_gas_p.sum()) / 1000.0
        elec_mwh = float(grid_elec_p.sum()) / 1000.0
        emissions_t_co2 = (gas_mwh * GAS_EMISSION_FACTOR_T_PER_MWH) + (elec_mwh * GRID_ELEC_EMISSION_FACTOR_T_PER_MWH) 

        # Sec19 peak grid demand check & audit verification
        peak_grid_kw = float(grid_elec_p.max())
        sec19_violation = peak_grid_kw > 1.25 * self.demand_elec_mw * 1000.0

        # Optimal sizing dictionary
        optimal_capacities = {}
        if "solar_pv" in n.generators.index:
            optimal_capacities["pv_kwp"] = float(n.generators.loc["solar_pv", "p_nom_opt" if "p_nom_opt" in n.generators.columns else "p_nom"])
        if "pv_ppa" in n.generators.index:
            optimal_capacities["pv_ppa_kw"] = float(n.generators.loc["pv_ppa", "p_nom_opt" if "p_nom_opt" in n.generators.columns else "p_nom"])
        if "wind_ppa" in n.generators.index:
            optimal_capacities["wind_ppa_kw"] = float(n.generators.loc["wind_ppa", "p_nom_opt" if "p_nom_opt" in n.generators.columns else "p_nom"])
        if "bess" in n.stores.index:
            optimal_capacities["bess_kwh"] = float(n.stores.loc["bess", "e_nom_opt" if "e_nom_opt" in n.stores.columns else "e_nom"])
        if "heat_pump" in n.links.index:
            p_opt = float(n.links.loc["heat_pump", "p_nom_opt" if "p_nom_opt" in n.links.columns else "p_nom"])
            optimal_capacities["hthp_kw_th"] = p_opt * self.comp_cfg.hthp.cop
        if "tes" in n.stores.index:
            optimal_capacities["tes_kwh_th"] = float(n.stores.loc["tes", "e_nom_opt" if "e_nom_opt" in n.stores.columns else "e_nom"])

        results = {
            "status": "ok",
            "total_cost_eur": total_cost,
            "opex_eur": opex_total,
            "capex_annualized_eur": capex_total,
            "elec_cost_eur": elec_cost_total,
            "gas_cost_eur": gas_cost_total,
            "pv_ppa_cost_eur": pv_ppa_cost,
            "wind_ppa_cost_eur": wind_ppa_cost,
            "grid_export_revenue_eur": grid_export_revenue_eur,
            "grid_export_mwh": grid_export_mwh,
            "emissions_t_co2": emissions_t_co2,
            "peak_grid_demand_kw": peak_grid_kw,
            "sec19_violation": sec19_violation,
            "optimal_capacities": optimal_capacities,
            "network": n,
        }

        self.results = results
        return results
