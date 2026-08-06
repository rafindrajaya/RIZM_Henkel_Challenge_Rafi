"""
Grid import components (Electricity and Natural Gas) for PyPSA model.
"""

import pypsa
import pandas as pd
from typing import Optional
from pydantic import BaseModel
from src.components.base import BaseEnergyComponent


class GridElectricityConfig(BaseModel):
    name: str = "grid_electricity"
    bus: str = "b_elec"
    p_nom: float = 1e6  # High upper bound for grid import capacity (kW)


class GridGasConfig(BaseModel):
    name: str = "grid_gas"
    bus: str = "b_gas"
    p_nom: float = 1e6  # High upper bound for gas grid import capacity (kW)


class GridElectricityComponent(BaseEnergyComponent):
    """Electricity grid import generator with dynamic spot/tariff price series."""

    def __init__(self, price_series: pd.Series, config: Optional[GridElectricityConfig] = None):
        cfg = config or GridElectricityConfig()
        super().__init__(cfg.name, cfg)
        self.price_series = price_series

    def build_component(self, network: pypsa.Network) -> None:
        network.add(
            "Generator",
            self.name,
            bus=self.config.bus,
            p_nom=self.config.p_nom,
            marginal_cost=self.price_series.values,
            p_min_pu=0.0,
            p_max_pu=1.0,
        )

    def calculate_annualized_capex(self, wacc: float) -> float:
        return 0.0


class GridGasComponent(BaseEnergyComponent):
    """Natural gas grid import generator with spot price + CO2 surcharge."""

    def __init__(self, price_series: pd.Series, config: Optional[GridGasConfig] = None):
        cfg = config or GridGasConfig()
        super().__init__(cfg.name, cfg)
        self.price_series = price_series

    def build_component(self, network: pypsa.Network) -> None:
        network.add(
            "Generator",
            self.name,
            bus=self.config.bus,
            p_nom=self.config.p_nom,
            marginal_cost=self.price_series.values,
            p_min_pu=0.0,
            p_max_pu=1.0,
        )

    def calculate_annualized_capex(self, wacc: float) -> float:
        return 0.0
