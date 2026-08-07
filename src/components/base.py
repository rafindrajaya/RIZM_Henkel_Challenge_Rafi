"""
Base interface and shared financial/lifecycle abstractions for OOP energy system components in PyPSA.
"""

from abc import ABC, abstractmethod
import pypsa
from pydantic import BaseModel, Field


def calculate_annuity_capex(
    capex_per_unit: float,
    opex_per_unit_year: float,
    lifetime_years: int,
    wacc: float,
) -> float:
    """Calculates Equivalent Annualized Cost (EAC) per unit of capacity.

    Args:
        capex_per_unit: Overnight capital expenditure per unit (EUR/unit).
        opex_per_unit_year: Fixed annual operation and maintenance cost (EUR/unit/year).
        lifetime_years: Asset economic lifetime in years.
        wacc: Weighted Average Cost of Capital (discount rate).

    Returns:
        Annualized capital and fixed operational cost (EUR/unit/year).
    """
    n = max(lifetime_years, 1)
    if wacc > 0:
        annuity_factor = (wacc * (1 + wacc) ** n) / ((1 + wacc) ** n - 1)
    else:
        annuity_factor = 1.0 / n
    return float(capex_per_unit * annuity_factor + opex_per_unit_year)


class BaseComponentConfig(BaseModel):
    """Base Pydantic configuration model for energy system components."""

    name: str
    is_extendable: bool = Field(default=False, description="Whether capacity optimization is enabled")
    lifetime_years: int = Field(default=20, ge=1, description="Economic asset lifetime in years")


class BaseEnergyComponent(ABC):
    """Abstract Base Class for all PyPSA energy system components."""

    def __init__(self, name: str, config: BaseModel):
        self.name = name
        self.config = config

    @property
    def is_extendable(self) -> bool:
        """Returns True if the component has extendable investment capacity."""
        return getattr(self.config, "is_extendable", False)

    def calculate_annualized_capex(self, wacc: float = 0.07) -> float:
        """Calculate Annualized Capital Cost (EAC) per unit capacity in EUR/unit/year."""
        capex = float(
            getattr(
                self.config,
                "capex_eur_per_kw",
                getattr(
                    self.config,
                    "capex_eur_per_kw_th",
                    getattr(self.config, "capex_eur_per_kwh", getattr(self.config, "capex_eur_per_kw_el", 0.0)),
                ),
            )
        )
        opex = float(
            getattr(
                self.config,
                "opex_eur_per_kw_year",
                getattr(
                    self.config,
                    "opex_eur_per_kw_th_year",
                    getattr(self.config, "opex_eur_per_kwh_year", getattr(self.config, "opex_eur_per_kw_el_year", 0.0)),
                ),
            )
        )
        lifetime = int(getattr(self.config, "lifetime_years", 20))
        annual_fee = float(getattr(self.config, "annual_fee_eur_per_kw_year", 0.0))

        if capex > 0.0 or opex > 0.0:
            return calculate_annuity_capex(capex, opex, lifetime, wacc)
        return annual_fee

    def get_capital_cost(self, wacc: float = 0.07) -> float:
        """Returns annualized capital cost if extendable, else 0.0 for fixed capacity assets."""
        return self.calculate_annualized_capex(wacc) if self.is_extendable else 0.0

    @abstractmethod
    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        """Attach PyPSA elements (buses, generators, links, stores, loads) to network."""
        pass
