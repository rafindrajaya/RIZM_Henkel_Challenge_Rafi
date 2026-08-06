"""
Base interface for OOP energy system components in PyPSA.
"""

from abc import ABC, abstractmethod
import pypsa
from pydantic import BaseModel


class BaseEnergyComponent(ABC):
    """Abstract Base Class for all PyPSA energy system components."""

    def __init__(self, name: str, config: BaseModel):
        self.name = name
        self.config = config

    @abstractmethod
    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        """Attach PyPSA elements (buses, generators, links, stores, loads) to network."""
        pass

    @abstractmethod
    def calculate_annualized_capex(self, wacc: float) -> float:
        """Calculate Annualized Capital Cost (EAC) per unit capacity in EUR/unit/year."""
        pass
