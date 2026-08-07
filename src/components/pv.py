"""
Solar PV Rooftop generator component for PyPSA model.
"""

import pypsa
import pandas as pd
from typing import Optional
from pydantic import BaseModel, Field
from .base import BaseEnergyComponent, BaseComponentConfig


import numpy as np
import logging

logger = logging.getLogger(__name__)


class PVComponentConfig(BaseComponentConfig):
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

    def __init__(
        self,
        config: PVComponentConfig,
        df_solar: Optional[pd.DataFrame] = None,
        pv_profile: Optional[pd.Series] = None,
    ):
        super().__init__(config.name, config)
        self.pv_config: PVComponentConfig = config

        if pv_profile is not None:
            self.pv_profile = pv_profile
        elif df_solar is not None:
            yield_arr = self.compute_pv_normalized_yield(df_solar)
            self.pv_profile = pd.Series(yield_arr, index=df_solar.index)
        else:
            raise ValueError("PVComponent requires either 'df_solar' or 'pv_profile'.")

    @staticmethod
    def compute_pv_normalized_yield(
        df_solar: pd.DataFrame,
        lat: float = 51.1783,
        lon: float = 6.8445,
        tilt: float = 38.0,
        azimuth: float = 180.0,
    ) -> np.ndarray:
        """Computes or retrieves normalized PV generation profile (0..1+ AC kW per kWp installed)."""
        if "pv_normalized_yield" in df_solar.columns:
            return np.clip(np.asarray(df_solar["pv_normalized_yield"], dtype=float), 0.0, 1.2)

        try:
            import pvlib

            times = df_solar.index
            solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
            dni_extra = pvlib.irradiance.get_extra_radiation(times)
            total_irrad = pvlib.irradiance.get_total_irradiance(
                surface_tilt=tilt,
                surface_azimuth=azimuth,
                solar_zenith=solpos["apparent_zenith"],
                solar_azimuth=solpos["azimuth"],
                dni=df_solar["dni"],
                ghi=df_solar["ghi"],
                dhi=df_solar["dhi"],
                dni_extra=dni_extra,
                model="haydavies",
            )
            poa_global = total_irrad["poa_global"].fillna(0.0)
            temp_air = df_solar["temp_air"] if "temp_air" in df_solar.columns else 15.0
            cell_temp = pvlib.temperature.faiman(poa_global, temp_air)
            dc_power = pvlib.pvsystem.pvwatts_dc(poa_global, cell_temp, pdc0=1.0, gamma_pdc=-0.004)
            return np.clip(np.asarray(dc_power, dtype=float), 0.0, 1.2)
        except (ImportError, KeyError, ValueError, AttributeError) as err:
            logger.warning(
                "pvlib simulation calculation failed (%s). Falling back to GHI irradiance model.", err
            )
            ghi = np.asarray(df_solar["ghi"], dtype=float) / 1000.0
            return np.clip(ghi, 0.0, 1.0)

    def build_component(self, network: pypsa.Network, wacc: float = 0.07) -> None:
        capital_cost = self.get_capital_cost(wacc)

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


def compute_pv_normalized_yield(
    df_solar: pd.DataFrame,
    lat: float = 51.1783,
    lon: float = 6.8445,
    tilt: float = 38.0,
    azimuth: float = 180.0,
) -> np.ndarray:
    """Module-level function alias delegating to PVComponent.compute_pv_normalized_yield."""
    return PVComponent.compute_pv_normalized_yield(df_solar, lat=lat, lon=lon, tilt=tilt, azimuth=azimuth)
