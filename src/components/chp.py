"""
Gas Combined Heat and Power (CHP) component for PyPSA model.
"""

import pypsa
from pydantic import BaseModel, Field
from src.components.base import BaseEnergyComponent


class CHPComponentConfig(BaseModel):
    name: str = "gas_chp"
    bus_in: str = "b_gas"
    bus_el: str = "b_elec"
    bus_th: str = "b_steam_ht"
    electrical_efficiency: float = Field(default=0.40, ge=0.0, le=1.0)
    thermal_efficiency: float = Field(default=0.45, ge=0.0, le=1.0)
    capacity_el_kw: float = Field(default=30000.0, ge=0.0)
    capex_eur_per_kw_el: float = Field(default=1200.0, ge=0.0)
    opex_eur_per_kw_el_year: float = Field(default=25.0, ge=0.0)
    lifetime_years: int = Field(default=25, ge=1)
    is_extendable: bool = Field(default=False)
    min_capacity_el_kw: float = Field(default=0.0, ge=0.0)
    max_capacity_el_kw: float = Field(default=50000.0, ge=0.0)


class GasCHPComponent(BaseEnergyComponent):
    """Combined Heat and Power unit modeled as a 2-output PyPSA Link (gas -> elec + steam_ht)."""

    def __init__(self, config: CHPComponentConfig):
        super().__init__(config.name, config)
        self.chp_config: CHPComponentConfig = config

    def calculate_annualized_capex(self, wacc: float) -> float:
        r = wacc
        n = self.chp_config.lifetime_years
        if r > 0:
            annuity_factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        else:
            annuity_factor = 1.0 / n
        eac = self.chp_config.capex_eur_per_kw_el * annuity_factor + self.chp_config.opex_eur_per_kw_el_year
        return float(eac)

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        # In PyPSA Link, efficiency is output/input for bus1.
        # bus0 = b_gas (input)
        # bus1 = b_elec (output 1) -> efficiency = eta_el
        # bus2 = b_steam_ht (output 2) -> efficiency2 = eta_th
        capital_cost = self.calculate_annualized_capex(wacc) if self.chp_config.is_extendable else 0.0

        if self.chp_config.is_extendable:
            network.add(
                "Link",
                self.name,
                bus0=self.chp_config.bus_in,
                bus1=self.chp_config.bus_el,
                bus2=self.chp_config.bus_th,
                efficiency=self.chp_config.electrical_efficiency,
                efficiency2=self.chp_config.thermal_efficiency,
                p_nom_extendable=True,
                p_nom_min=self.chp_config.min_capacity_el_kw / self.chp_config.electrical_efficiency,
                p_nom_max=self.chp_config.max_capacity_el_kw / self.chp_config.electrical_efficiency,
                capital_cost=capital_cost * self.chp_config.electrical_efficiency,
            )
        else:
            p_nom_in = self.chp_config.capacity_el_kw / self.chp_config.electrical_efficiency if self.chp_config.electrical_efficiency > 0 else 0.0
            network.add(
                "Link",
                self.name,
                bus0=self.chp_config.bus_in,
                bus1=self.chp_config.bus_el,
                bus2=self.chp_config.bus_th,
                efficiency=self.chp_config.electrical_efficiency,
                efficiency2=self.chp_config.thermal_efficiency,
                p_nom=p_nom_in,
                p_nom_extendable=False,
            )
