"""
Industrial baseload demand sinks (Loads) for PyPSA model.
"""

from typing import Optional

import pypsa
from pydantic import BaseModel, Field
from src.components.base import BaseEnergyComponent


class DemandConfig(BaseModel):
    elec_demand_mw: float = Field(default=60.0, ge=0.0, description="Electrical continuous baseload demand in MW")
    steam_demand_mw_th: float = Field(default=160.0, ge=0.0, description="High-temp steam demand in MW_th")
    heat_demand_mw_th: float = Field(default=60.0, ge=0.0, description="Mid-temp process heat demand in MW_th")


class DemandComponent(BaseEnergyComponent):
    """Energy demand sinks attached to b_elec, b_steam_ht, and b_heat_lt buses."""

    def __init__(self, config: Optional[DemandConfig] = None):
        cfg = config or DemandConfig()
        super().__init__("demand_sinks", cfg)
        self.demand_config: DemandConfig = cfg

    def calculate_annualized_capex(self, wacc: float = 0.07) -> float:
        return 0.0

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        # Electricity demand (kW)
        network.add(
            "Load",
            "demand_elec",
            bus="b_elec",
            p_set=self.demand_config.elec_demand_mw * 1000.0,
        )

        # High-temperature steam demand (kW_th)
        network.add(
            "Load",
            "demand_steam",
            bus="b_steam_ht",
            p_set=self.demand_config.steam_demand_mw_th * 1000.0,
        )

        # Mid-temperature process heat demand (kW_th)
        network.add(
            "Load",
            "demand_heat",
            bus="b_heat_lt",
            p_set=self.demand_config.heat_demand_mw_th * 1000.0,
        )
