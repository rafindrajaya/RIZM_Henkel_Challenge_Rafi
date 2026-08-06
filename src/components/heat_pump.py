"""
Industrial High-Temperature Heat Pump (HTHP) component for PyPSA model.
"""

import pypsa
from pydantic import BaseModel, Field
from src.components.base import BaseEnergyComponent


class HTHPComponentConfig(BaseModel):
    name: str = "heat_pump"
    bus_in: str = "b_elec"
    bus_out: str = "b_heat_lt"
    cop: float = Field(default=2.8, ge=1.0, description="Coefficient of Performance (Heat out / Elec in)")
    capacity_th_kw: float = Field(default=15000.0, ge=0.0)
    capex_eur_per_kw_th: float = Field(default=600.0, ge=0.0)
    opex_eur_per_kw_th_year: float = Field(default=10.0, ge=0.0)
    lifetime_years: int = Field(default=20, ge=1)
    is_extendable: bool = Field(default=False)
    min_capacity_th_kw: float = Field(default=0.0, ge=0.0)
    max_capacity_th_kw: float = Field(default=40000.0, ge=0.0)


class HTHPComponent(BaseEnergyComponent):
    """High-Temperature Heat Pump converting electricity to mid-temperature process heat (COP = 2.8)."""

    def __init__(self, config: HTHPComponentConfig):
        super().__init__(config.name, config)
        self.hthp_config: HTHPComponentConfig = config

    def calculate_annualized_capex(self, wacc: float) -> float:
        r = wacc
        n = self.hthp_config.lifetime_years
        if r > 0:
            annuity_factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        else:
            annuity_factor = 1.0 / n
        return float(self.hthp_config.capex_eur_per_kw_th * annuity_factor + self.hthp_config.opex_eur_per_kw_th_year)

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        cop = self.hthp_config.cop
        capital_cost = self.calculate_annualized_capex(wacc) if self.hthp_config.is_extendable else 0.0

        if self.hthp_config.is_extendable:
            network.add(
                "Link",
                self.name,
                bus0=self.hthp_config.bus_in,
                bus1=self.hthp_config.bus_out,
                efficiency=cop,
                p_nom_extendable=True,
                p_nom_min=self.hthp_config.min_capacity_th_kw / cop,
                p_nom_max=self.hthp_config.max_capacity_th_kw / cop,
                capital_cost=capital_cost * cop,
            )
        else:
            network.add(
                "Link",
                self.name,
                bus0=self.hthp_config.bus_in,
                bus1=self.hthp_config.bus_out,
                efficiency=cop,
                p_nom=self.hthp_config.capacity_th_kw / cop if cop > 0 else 0.0,
                p_nom_extendable=False,
            )
