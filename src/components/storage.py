"""
BESS and Thermal Energy Storage (TES) components for PyPSA model.
"""

import pypsa
from pydantic import Field
from .base import BaseEnergyComponent, BaseComponentConfig


class BESSComponentConfig(BaseComponentConfig):
    name: str = "bess"
    bus: str = "b_elec"
    capex_eur_per_kwh: float = Field(default=350.0, ge=0.0)
    opex_eur_per_kwh_year: float = Field(default=5.0, ge=0.0)
    lifetime_years: int = Field(default=15, ge=1)
    round_trip_efficiency: float = Field(default=0.90, ge=0.0, le=1.0)
    charge_efficiency: float = Field(default=0.95, ge=0.0, le=1.0)
    discharge_efficiency: float = Field(default=0.95, ge=0.0, le=1.0)
    self_discharge_rate_per_hour: float = Field(default=0.0001, ge=0.0)
    min_soc: float = Field(default=0.05, ge=0.0, le=1.0)  # 5% Minimum SOC limit
    initial_soc: float = Field(default=0.05, ge=0.0, le=1.0)  # 5% Initial SOC
    e_cyclic: bool = Field(default=True, description="Enable cyclic state of charge constraint (e_start == e_end)")
    c_rate: float = Field(default=0.5, ge=0.0)
    marginal_cost_eur_per_kwh: float = Field(default=0.0015, ge=0.0)  # €1.5/MWh small penalty to prevent LP simultaneous cycling
    installed_capacity_kwh: float = Field(default=0.0, ge=0.0)
    is_extendable: bool = Field(default=False)
    min_capacity_kwh: float = Field(default=0.0, ge=0.0)
    max_capacity_kwh: float = Field(default=50000.0, ge=0.0)


class TESComponentConfig(BaseComponentConfig):
    name: str = "tes"
    bus: str = "b_heat_lt"
    capex_eur_per_kwh: float = Field(default=50.0, ge=0.0)
    opex_eur_per_kwh_year: float = Field(default=1.0, ge=0.0)
    lifetime_years: int = Field(default=30, ge=1)
    round_trip_efficiency: float = Field(default=0.96, ge=0.0, le=1.0)
    charge_efficiency: float = Field(default=0.98, ge=0.0, le=1.0)
    discharge_efficiency: float = Field(default=0.98, ge=0.0, le=1.0)
    loss_rate_per_hour: float = Field(default=0.005, ge=0.0)
    min_soc: float = Field(default=0.05, ge=0.0, le=1.0)  # 5% Minimum SOC limit
    initial_soc: float = Field(default=0.05, ge=0.0, le=1.0)  # 5% Initial SOC
    e_cyclic: bool = Field(default=True, description="Enable cyclic state of charge constraint (e_start == e_end)")
    c_rate: float = Field(default=0.25, ge=0.0)
    marginal_cost_eur_per_kwh: float = Field(default=0.0015, ge=0.0)  # €1.5/MWh small penalty to prevent LP simultaneous cycling
    installed_capacity_kwh: float = Field(default=20000.0, ge=0.0)
    is_extendable: bool = Field(default=False)
    min_capacity_kwh: float = Field(default=0.0, ge=0.0)
    max_capacity_kwh: float = Field(default=100000.0, ge=0.0)


class BESSComponent(BaseEnergyComponent):
    """Battery Energy Storage System using PyPSA Store + Charger/Discharger Links."""

    def __init__(self, config: BESSComponentConfig):
        super().__init__(config.name, config)
        self.bess_config: BESSComponentConfig = config

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        bus_bess = f"{self.name}_bus"
        network.add("Bus", bus_bess, carrier="electricity_stored", x=6.8325, y=51.1725)

        capital_cost = self.get_capital_cost(wacc)

        if self.bess_config.is_extendable:
            network.add(
                "Store",
                self.name,
                bus=bus_bess,
                e_nom_extendable=True,
                e_nom_min=self.bess_config.min_capacity_kwh,
                e_nom_max=self.bess_config.max_capacity_kwh,
                e_min_pu=self.bess_config.min_soc,
                e_cyclic=self.bess_config.e_cyclic,
                standing_loss=self.bess_config.self_discharge_rate_per_hour,
                capital_cost=capital_cost,
            )
            network.add(
                "Link",
                f"{self.name}_charger",
                bus0=self.bess_config.bus,
                bus1=bus_bess,
                efficiency=self.bess_config.charge_efficiency,
                p_nom_extendable=True,
                p_nom_min=self.bess_config.min_capacity_kwh * self.bess_config.c_rate,
                p_nom_max=self.bess_config.max_capacity_kwh * self.bess_config.c_rate,
                marginal_cost=self.bess_config.marginal_cost_eur_per_kwh,
            )
            network.add(
                "Link",
                f"{self.name}_discharger",
                bus0=bus_bess,
                bus1=self.bess_config.bus,
                efficiency=self.bess_config.discharge_efficiency,
                p_nom_extendable=True,
                p_nom_min=self.bess_config.min_capacity_kwh * self.bess_config.c_rate,
                p_nom_max=self.bess_config.max_capacity_kwh * self.bess_config.c_rate,
                marginal_cost=self.bess_config.marginal_cost_eur_per_kwh,
            )
        else:
            e_nom = self.bess_config.installed_capacity_kwh
            p_max = e_nom * self.bess_config.c_rate
            network.add(
                "Store",
                self.name,
                bus=bus_bess,
                e_nom=e_nom,
                e_nom_extendable=False,
                e_min_pu=self.bess_config.min_soc,
                e_initial=e_nom * self.bess_config.initial_soc,
                e_cyclic=self.bess_config.e_cyclic,
                standing_loss=self.bess_config.self_discharge_rate_per_hour,
            )
            network.add(
                "Link",
                f"{self.name}_charger",
                bus0=self.bess_config.bus,
                bus1=bus_bess,
                efficiency=self.bess_config.charge_efficiency,
                p_nom=p_max,
                p_nom_extendable=False,
                marginal_cost=self.bess_config.marginal_cost_eur_per_kwh,
            )
            network.add(
                "Link",
                f"{self.name}_discharger",
                bus0=bus_bess,
                bus1=self.bess_config.bus,
                efficiency=self.bess_config.discharge_efficiency,
                p_nom=p_max,
                p_nom_extendable=False,
                marginal_cost=self.bess_config.marginal_cost_eur_per_kwh,
            )


class TESComponent(BaseEnergyComponent):
    """Thermal Energy Storage System using PyPSA Store + Charger/Discharger Links."""

    def __init__(self, config: TESComponentConfig):
        super().__init__(config.name, config)
        self.tes_config: TESComponentConfig = config

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        bus_tes = f"{self.name}_bus"
        network.add("Bus", bus_tes, carrier="heat_stored", x=6.8355, y=51.1710)

        capital_cost = self.get_capital_cost(wacc)

        if self.tes_config.is_extendable:
            network.add(
                "Store",
                self.name,
                bus=bus_tes,
                e_nom_extendable=True,
                e_nom_min=self.tes_config.min_capacity_kwh,
                e_nom_max=self.tes_config.max_capacity_kwh,
                e_min_pu=self.tes_config.min_soc,
                e_cyclic=self.tes_config.e_cyclic,
                standing_loss=self.tes_config.loss_rate_per_hour,
                capital_cost=capital_cost,
            )
            network.add(
                "Link",
                f"{self.name}_charger",
                bus0=self.tes_config.bus,
                bus1=bus_tes,
                efficiency=self.tes_config.charge_efficiency,
                p_nom_extendable=True,
                p_nom_min=self.tes_config.min_capacity_kwh * self.tes_config.c_rate,
                p_nom_max=self.tes_config.max_capacity_kwh * self.tes_config.c_rate,
                marginal_cost=self.tes_config.marginal_cost_eur_per_kwh,
            )
            network.add(
                "Link",
                f"{self.name}_discharger",
                bus0=bus_tes,
                bus1=self.tes_config.bus,
                efficiency=self.tes_config.discharge_efficiency,
                p_nom_extendable=True,
                p_nom_min=self.tes_config.min_capacity_kwh * self.tes_config.c_rate,
                p_nom_max=self.tes_config.max_capacity_kwh * self.tes_config.c_rate,
                marginal_cost=self.tes_config.marginal_cost_eur_per_kwh,
            )
        else:
            e_nom = self.tes_config.installed_capacity_kwh
            p_max = e_nom * self.tes_config.c_rate
            network.add(
                "Store",
                self.name,
                bus=bus_tes,
                e_nom=e_nom,
                e_nom_extendable=False,
                e_min_pu=self.tes_config.min_soc,
                e_initial=e_nom * self.tes_config.initial_soc,
                e_cyclic=self.tes_config.e_cyclic,
                standing_loss=self.tes_config.loss_rate_per_hour,
            )
            network.add(
                "Link",
                f"{self.name}_charger",
                bus0=self.tes_config.bus,
                bus1=bus_tes,
                efficiency=self.tes_config.charge_efficiency,
                p_nom=p_max,
                p_nom_extendable=False,
                marginal_cost=self.tes_config.marginal_cost_eur_per_kwh,
            )
            network.add(
                "Link",
                f"{self.name}_discharger",
                bus0=bus_tes,
                bus1=self.tes_config.bus,
                efficiency=self.tes_config.discharge_efficiency,
                p_nom=p_max,
                p_nom_extendable=False,
                marginal_cost=self.tes_config.marginal_cost_eur_per_kwh,
            )


def add_storage_inverter_constraint(network: pypsa.Network, storage_name: str) -> None:
    """Adds Linopy constraint ensuring p_charger(t) + p_discharger(t) <= p_inverter_nominal for any storage component."""
    charger_name = f"{storage_name}_charger"
    discharger_name = f"{storage_name}_discharger"
    if charger_name not in network.links.index or discharger_name not in network.links.index:
        return

    m = network.model
    p_ch = m["Link-p"].sel(name=charger_name)
    p_dis = m["Link-p"].sel(name=discharger_name)

    if getattr(network.links.loc[charger_name], "p_nom_extendable", False) and "Link-p_nom" in m.variables:
        p_nom = m["Link-p_nom"].loc[charger_name]
    else:
        p_nom = float(network.links.loc[charger_name, "p_nom"])

    m.add_constraints(
        p_ch + p_dis <= p_nom,
        name=f"custom_{storage_name}_inverter_capacity",
    )
