"""
Solar PV Rooftop generator component for PyPSA model.
"""

import pypsa
import pandas as pd
from typing import Optional
from pydantic import BaseModel, Field
from src.components.base import BaseEnergyComponent


class PVComponentConfig(BaseModel):
    name: str = "solar_pv"
    bus: str = "b_elec"
    capex_eur_per_kw: float = Field(default=800.0, ge=0.0)
    opex_eur_per_kw_year: float = Field(default=12.0, ge=0.0)
    lifetime_years: int = Field(default=25, ge=1)
    installed_capacity_kw: float = Field(default=0.0, ge=0.0)
    is_extendable: bool = Field(default=False)
    min_capacity_kw: float = Field(default=0.0, ge=0.0)
    max_capacity_kw: float = Field(default=25000.0, ge=0.0)


class PVComponent(BaseEnergyComponent):
    """Solar PV Generator component using normalized yield profile (p_max_pu)."""

    def __init__(self, pv_profile: pd.Series, config: PVComponentConfig):
        super().__init__(config.name, config)
        self.pv_profile = pv_profile
        self.pv_config: PVComponentConfig = config

    def calculate_annualized_capex(self, wacc: float) -> float:
        r = wacc
        n = self.pv_config.lifetime_years
        if r > 0:
            annuity_factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        else:
            annuity_factor = 1.0 / n
        eac = self.pv_config.capex_eur_per_kw * annuity_factor + self.pv_config.opex_eur_per_kw_year
        return float(eac)

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        capital_cost = self.calculate_annualized_capex(wacc) if self.pv_config.is_extendable else 0.0

        if self.pv_config.is_extendable:
            network.add(
                "Generator",
                self.name,
                bus=self.pv_config.bus,
                p_nom_extendable=True,
                p_nom_min=self.pv_config.min_capacity_kw,
                p_nom_max=self.pv_config.max_capacity_kw,
                p_max_pu=self.pv_profile.values,
                marginal_cost=0.0,
                capital_cost=capital_cost,
            )
        else:
            network.add(
                "Generator",
                self.name,
                bus=self.pv_config.bus,
                p_nom=self.pv_config.installed_capacity_kw,
                p_nom_extendable=False,
                p_max_pu=self.pv_profile.values,
                marginal_cost=0.0,
            )
