"""
Boiler and Heat Exchanger link components for PyPSA model.
"""

from typing import Optional

import pypsa
from pydantic import BaseModel, Field
from .base import BaseEnergyComponent, BaseComponentConfig


class GasBoilerConfig(BaseComponentConfig):
    name: str = "gas_boiler"
    bus_in: str = "b_gas"
    bus_out: str = "b_steam_ht"
    thermal_efficiency: float = Field(default=0.92, ge=0.0, le=1.0)
    capacity_th_kw: float = Field(default=180000.0, ge=0.0)
    capex_eur_per_kw_th: float = Field(default=150.0, ge=0.0)
    opex_eur_per_kw_th_year: float = Field(default=3.0, ge=0.0)
    lifetime_years: int = Field(default=25, ge=1)
    is_extendable: bool = Field(default=False)
    min_capacity_th_kw: float = Field(default=0.0, ge=0.0)
    max_capacity_th_kw: float = Field(default=200000.0, ge=0.0)


class EBoilerConfig(BaseComponentConfig):
    name: str = "electric_boiler"
    bus_in: str = "b_elec"
    bus_out: str = "b_steam_ht"
    thermal_efficiency: float = Field(default=0.98, ge=0.0, le=1.0)
    capacity_th_kw: float = Field(default=25000.0, ge=0.0)
    capex_eur_per_kw_th: float = Field(default=100.0, ge=0.0)
    opex_eur_per_kw_th_year: float = Field(default=2.0, ge=0.0)
    lifetime_years: int = Field(default=20, ge=1)
    is_extendable: bool = Field(default=False)
    min_capacity_th_kw: float = Field(default=0.0, ge=0.0)
    max_capacity_th_kw: float = Field(default=50000.0, ge=0.0)


class SteamHeatExchangerConfig(BaseComponentConfig):
    name: str = "steam_to_heat_exchanger"
    bus_in: str = "b_steam_ht"
    bus_out: str = "b_heat_lt"
    efficiency: float = Field(default=0.98, ge=0.0, le=1.0)
    capacity_th_kw: float = Field(default=100000.0, ge=0.0)


class GasBoilerComponent(BaseEnergyComponent):
    """Natural gas boiler converting gas to high-temperature steam."""

    def __init__(self, config: GasBoilerConfig):
        super().__init__(config.name, config)
        self.boiler_config: GasBoilerConfig = config

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        capital_cost = self.get_capital_cost(wacc)
        eff = self.boiler_config.thermal_efficiency
        if self.boiler_config.is_extendable:
            network.add(
                "Link",
                self.name,
                bus0=self.boiler_config.bus_in,
                bus1=self.boiler_config.bus_out,
                efficiency=eff,
                p_nom_extendable=True,
                p_nom_min=self.boiler_config.min_capacity_th_kw / eff,
                p_nom_max=self.boiler_config.max_capacity_th_kw / eff,
                capital_cost=capital_cost * eff,
            )
        else:
            network.add(
                "Link",
                self.name,
                bus0=self.boiler_config.bus_in,
                bus1=self.boiler_config.bus_out,
                efficiency=eff,
                p_nom=self.boiler_config.capacity_th_kw / eff if eff > 0 else 0.0,
                p_nom_extendable=False,
            )


class EBoilerComponent(BaseEnergyComponent):
    """Electrode boiler converting electricity to high-temperature steam."""

    def __init__(self, config: EBoilerConfig):
        super().__init__(config.name, config)
        self.boiler_config: EBoilerConfig = config

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        capital_cost = self.get_capital_cost(wacc)
        eff = self.boiler_config.thermal_efficiency
        if self.boiler_config.is_extendable:
            network.add(
                "Link",
                self.name,
                bus0=self.boiler_config.bus_in,
                bus1=self.boiler_config.bus_out,
                efficiency=eff,
                p_nom_extendable=True,
                p_nom_min=self.boiler_config.min_capacity_th_kw / eff,
                p_nom_max=self.boiler_config.max_capacity_th_kw / eff,
                capital_cost=capital_cost * eff,
            )
        else:
            network.add(
                "Link",
                self.name,
                bus0=self.boiler_config.bus_in,
                bus1=self.boiler_config.bus_out,
                efficiency=eff,
                p_nom=self.boiler_config.capacity_th_kw / eff if eff > 0 else 0.0,
                p_nom_extendable=False,
            )


class SteamHeatExchangerComponent(BaseEnergyComponent):
    """Steam-to-process-heat exchanger converting high-temp steam to mid-temp heat."""

    def __init__(self, config: Optional[SteamHeatExchangerConfig] = None):
        cfg = config or SteamHeatExchangerConfig()
        super().__init__(cfg.name, cfg)

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        eff = self.config.efficiency
        network.add(
            "Link",
            self.name,
            bus0=self.config.bus_in,
            bus1=self.config.bus_out,
            efficiency=eff,
            p_nom=self.config.capacity_th_kw / eff,
            p_nom_extendable=False,
        )
