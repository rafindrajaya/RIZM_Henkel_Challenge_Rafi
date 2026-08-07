"""
Grid import components (Electricity and Natural Gas) for PyPSA model.
"""

from typing import Optional
import pandas as pd
import pypsa
from pydantic import Field
from .base import BaseEnergyComponent, BaseComponentConfig


class GridElectricityConfig(BaseComponentConfig):
    name: str = "grid_electricity"
    bus: str = "b_elec"
    p_nom: float = 1e6  # High upper bound for grid import capacity (kW)


class GridGasConfig(BaseComponentConfig):
    name: str = "grid_gas"
    bus: str = "b_gas"
    p_nom: float = 1e6  # High upper bound for gas grid import capacity (kW)


class GridElectricityComponent(BaseEnergyComponent):
    """Electricity grid import generator with dynamic spot/tariff price series."""

    def __init__(self, price_series: pd.Series, config: Optional[GridElectricityConfig] = None):
        cfg = config or GridElectricityConfig()
        super().__init__(cfg.name, cfg)
        self.price_series = price_series

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        network.add(
            "Generator",
            self.name,
            bus=self.config.bus,
            p_nom=self.config.p_nom,
            marginal_cost=self.price_series.values,
            p_min_pu=0.0,
            p_max_pu=1.0,
        )


class GridGasComponent(BaseEnergyComponent):
    """Natural gas grid import generator with spot price + CO2 surcharge."""

    def __init__(self, price_series: pd.Series, config: Optional[GridGasConfig] = None):
        cfg = config or GridGasConfig()
        super().__init__(cfg.name, cfg)
        self.price_series = price_series

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        network.add(
            "Generator",
            self.name,
            bus=self.config.bus,
            p_nom=self.config.p_nom,
            marginal_cost=self.price_series.values,
            p_min_pu=0.0,
            p_max_pu=1.0,
        )


class PVPPAConfig(BaseComponentConfig):
    name: str = "pv_ppa"
    bus: str = "b_elec"
    strike_price_eur_per_mwh: float = Field(default=55.0, ge=0.0)      # €55/MWh pay-as-produced strike price
    annual_fee_eur_per_kw_year: float = Field(default=3.0, ge=0.0)    # €3/kW-year capacity commitment fee
    installed_capacity_kw: float = Field(default=0.0, ge=0.0)
    is_extendable: bool = Field(default=False)
    min_capacity_kw: float = Field(default=0.0, ge=0.0)
    max_capacity_kw: float = Field(default=50000.0, ge=0.0)


class WindPPAConfig(BaseComponentConfig):
    name: str = "wind_ppa"
    bus: str = "b_elec"
    strike_price_eur_per_mwh: float = Field(default=65.0, ge=0.0)      # €65/MWh pay-as-produced strike price
    annual_fee_eur_per_kw_year: float = Field(default=4.0, ge=0.0)    # €4/kW-year capacity commitment fee
    installed_capacity_kw: float = Field(default=0.0, ge=0.0)
    is_extendable: bool = Field(default=False)
    min_capacity_kw: float = Field(default=0.0, ge=0.0)
    max_capacity_kw: float = Field(default=50000.0, ge=0.0)


class PVPPAComponent(BaseEnergyComponent):
    """Off-site Solar PV Power Purchase Agreement (Pay-as-Produced Generator)."""

    def __init__(self, pv_profile: pd.Series, config: Optional[PVPPAConfig] = None):
        cfg = config or PVPPAConfig()
        super().__init__(cfg.name, cfg)
        self.ppa_config: PVPPAConfig = cfg
        self.pv_profile = pv_profile

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        marginal_cost_kwh = self.ppa_config.strike_price_eur_per_mwh / 1000.0
        capital_cost = self.get_capital_cost(wacc)

        if self.ppa_config.is_extendable:
            network.add(
                "Generator",
                self.name,
                bus=self.ppa_config.bus,
                p_nom_extendable=True,
                p_nom_min=self.ppa_config.min_capacity_kw,
                p_nom_max=self.ppa_config.max_capacity_kw,
                p_max_pu=self.pv_profile.values,
                marginal_cost=marginal_cost_kwh,
                capital_cost=capital_cost,
            )
        else:
            network.add(
                "Generator",
                self.name,
                bus=self.ppa_config.bus,
                p_nom=self.ppa_config.installed_capacity_kw,
                p_nom_extendable=False,
                p_max_pu=self.pv_profile.values,
                marginal_cost=marginal_cost_kwh,
            )


class WindPPAComponent(BaseEnergyComponent):
    """Off-site Onshore Wind Power Purchase Agreement (Pay-as-Produced Generator)."""

    def __init__(self, wind_profile: pd.Series, config: Optional[WindPPAConfig] = None):
        cfg = config or WindPPAConfig()
        super().__init__(cfg.name, cfg)
        self.ppa_config: WindPPAConfig = cfg
        self.wind_profile = wind_profile

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        marginal_cost_kwh = self.ppa_config.strike_price_eur_per_mwh / 1000.0
        capital_cost = self.get_capital_cost(wacc)

        if self.ppa_config.is_extendable:
            network.add(
                "Generator",
                self.name,
                bus=self.ppa_config.bus,
                p_nom_extendable=True,
                p_nom_min=self.ppa_config.min_capacity_kw,
                p_nom_max=self.ppa_config.max_capacity_kw,
                p_max_pu=self.wind_profile.values,
                marginal_cost=marginal_cost_kwh,
                capital_cost=capital_cost,
            )
        else:
            network.add(
                "Generator",
                self.name,
                bus=self.ppa_config.bus,
                p_nom=self.ppa_config.installed_capacity_kw,
                p_nom_extendable=False,
                p_max_pu=self.wind_profile.values,
                marginal_cost=marginal_cost_kwh,
            )
