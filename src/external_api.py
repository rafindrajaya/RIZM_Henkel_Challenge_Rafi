"""
External API Connector and Data Benchmark Pipeline for Henkel Düsseldorf.

Retrieves and pre-processes:
1. German Day-Ahead Electricity Spot Market Prices (SMARD / ENTSO-E proxy).
2. Trading Hub Europe (THE) Natural Gas Prices & CO2 Tax Surcharges.
3. Düsseldorf Solar Irradiance Weather Profile via Open-Meteo API & pvlib simulation.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import pandas as pd
import requests

DATA_DIR = Path(__file__).parent.parent / "data"
DUESSELDORF_LAT = 51.1783
DUESSELDORF_LON = 6.8445


def fetch_smard_electricity_prices(year: int = 2025) -> pd.Series:
    """
    Fetches real hourly Day-Ahead wholesale electricity spot prices (€/MWh) for Germany (bidding zone DE)
    from Bundesnetzagentur SMARD API (filter 4169).
    """
    import datetime

    url_index = "https://www.smard.de/app/chart_data/4169/DE/index_hour.json"
    response = requests.get(url_index, timeout=10)
    response.raise_for_status()

    timestamps = response.json().get("timestamps", [])
    target_timestamps = [
        ts
        for ts in timestamps
        if datetime.datetime.fromtimestamp(ts / 1000, tz=datetime.timezone.utc).year == year
    ]

    all_series = []
    for ts in target_timestamps:
        data_url = f"https://www.smard.de/app/chart_data/4169/DE/4169_DE_hour_{ts}.json"
        res = requests.get(data_url, timeout=10)
        if res.status_code == 200:
            all_series.extend(res.json().get("series", []))

    if not all_series:
        raise ValueError(f"No SMARD data series retrieved for year {year}")

    df_smard = pd.DataFrame(all_series, columns=["timestamp_ms", "elec_spot_eur_mwh"]).dropna()
    df_smard["timestamp"] = (
        pd.to_datetime(df_smard["timestamp_ms"], unit="ms", utc=True)
        .dt.tz_localize(None)
    )
    df_smard = df_smard.drop_duplicates(subset=["timestamp"]).set_index("timestamp").sort_index()

    start_str = f"{year}-01-01 00:00:00"
    end_str = f"{year}-12-31 23:00:00"
    series = df_smard.loc[start_str:end_str, "elec_spot_eur_mwh"]
    print(f"[Info] Fetched {len(series)} hourly SMARD {year} spot prices in UTC (Mean: €{series.mean():.2f}/MWh)")
    return series


def fetch_open_meteo_solar(
    lat: float = DUESSELDORF_LAT,
    lon: float = DUESSELDORF_LON,
    year: int = 2025,
) -> pd.DataFrame:
    """
    Fetches hourly solar irradiance (GHI, DNI, DHI) and temperature for Düsseldorf
    from Open-Meteo Historical Weather API.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m",
        "timezone": "UTC",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()["hourly"]

        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(data["time"]),
                "ghi": data["shortwave_radiation"],
                "dni": data["direct_normal_irradiance"],
                "dhi": data["diffuse_radiation"],
                "temp_air": data["temperature_2m"],
            }
        ).set_index("timestamp")

        return df
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"[Warning] Live Open-Meteo API fetch failed ({type(e).__name__}: {e}). Falling back to synthetic solar model.")
        return generate_synthetic_solar_data(year=year)


def generate_synthetic_solar_data(year: int = 2025) -> pd.DataFrame:
    """Generates physically sound solar irradiance profile for Düsseldorf if offline."""
    np.random.seed(42)
    times = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31 23:00", freq="h")
    day_of_year = times.dayofyear
    hour = times.hour

    solar_noon_offset = np.abs(hour - 12)
    seasonal_factor = np.sin((day_of_year - 80) * 2 * np.pi / 365) * 0.4 + 0.6
    diurnal_factor = np.maximum(0, np.cos(solar_noon_offset * np.pi / 7.5))

    ghi = 850 * diurnal_factor * seasonal_factor * (0.8 + 0.4 * np.random.rand(len(times)))
    ghi = np.clip(ghi, 0, 1000)
    dni = ghi * 0.7
    dhi = ghi * 0.3
    temp_air = 10 + 12 * np.sin((day_of_year - 100) * 2 * np.pi / 365) + 4 * np.sin((hour - 6) * np.pi / 12)

    return pd.DataFrame({"ghi": ghi, "dni": dni, "dhi": dhi, "temp_air": temp_air}, index=times)


def generate_benchmark_market_data(year: int = 2025) -> pd.DataFrame:
    """
    Generates 2025 German energy market dataset:
    - Electricity Spot Price (€/MWh): Fetched live from SMARD API (filter 4169) with synthetic fallback.
    - Natural Gas THE Benchmark (€/MWh): 2025 Baseline €42/MWh with seasonal heating demand shape.
    - CO2 Surcharge (€/ton): €85/ton ETS/BEHG -> €17.085/MWh_gas surcharge.
    - Grid Fees: €25/MWh standard, €3.75/MWh (§19 StromNEV 85% discount).
    """
    times = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31 23:00", freq="h")
    month = times.month

    # Try fetching real SMARD spot prices in UTC
    try:
        smard_series = fetch_smard_electricity_prices(year=year)
        smard_series.index = pd.to_datetime(smard_series.index)
        if smard_series.index.tz is not None:
            smard_series.index = smard_series.index.tz_localize(None)
        # Reindex to ensure full hourly coverage
        elec_spot = smard_series.reindex(times).ffill().bfill().values
    except Exception as e:
        print(f"[Warning] Live SMARD API fetch failed ({e}). Generating benchmark electricity profile.")
        np.random.seed(42)
        hour = times.hour
        is_weekend = times.weekday >= 5
        diurnal_shape = np.where(
            (hour >= 11) & (hour <= 15),
            -25.0,
            np.where((hour >= 7) & (hour <= 9) | (hour >= 17) & (hour <= 20), 30.0, 0.0),
        )
        seasonal_shape = np.cos((month - 1) * 2 * np.pi / 12) * 20.0
        weekend_shape = np.where(is_weekend, -15.0, 0.0)
        noise = np.random.normal(0, 12, len(times))
        elec_spot = 85.0 + diurnal_shape + seasonal_shape + weekend_shape + noise
        elec_spot = np.clip(elec_spot, -10.0, 300.0)

    # 2025 Natural Gas baseline (Trading Hub Europe benchmark: ~€42/MWh average)
    np.random.seed(42)
    gas_base = 42.0 + np.cos((month - 1) * 2 * np.pi / 12) * 6.0 + np.random.normal(0, 2, len(times))
    gas_base = np.clip(gas_base, 25.0, 95.0)

    co2_price_eur_per_ton = 85.0
    gas_emission_factor_t_per_mwh = 0.201
    co2_tax_per_mwh_gas = co2_price_eur_per_ton * gas_emission_factor_t_per_mwh

    gas_total_cost = gas_base + co2_tax_per_mwh_gas

    grid_fee_standard = 25.0
    grid_fee_reduced_sec19 = 3.75

    df = pd.DataFrame(
        {
            "elec_spot_eur_mwh": elec_spot,
            "gas_spot_eur_mwh": gas_base,
            "co2_tax_eur_mwh_gas": co2_tax_per_mwh_gas,
            "gas_total_eur_mwh": gas_total_cost,
            "grid_fee_standard_eur_mwh": grid_fee_standard,
            "grid_fee_sec19_eur_mwh": grid_fee_reduced_sec19,
            "elec_total_standard_eur_mwh": elec_spot + grid_fee_standard,
            "elec_total_sec19_eur_mwh": elec_spot + grid_fee_reduced_sec19,
        },
        index=times,
    )
    df.index.name = "timestamp"

    return df


def compute_optimal_pv_yield(
    df_solar: pd.DataFrame,
    lat: float = DUESSELDORF_LAT,
    lon: float = DUESSELDORF_LON,
    tilt: float = 38.0,
    azimuth: float = 180.0,
) -> np.ndarray:
    """
    Computes optimal normalized PV generation profile (AC kW per kWp installed) for Düsseldorf coordinates
    using pvlib physical solar position, Hay-Davies irradiance transposition, Faiman cell temperature,
    and PVWatts DC/AC system modeling with thermal losses.
    """
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
        ac_yield = dc_power * 0.96
        return np.clip(np.asarray(ac_yield, dtype=float), 0.0, 1.2)
    except Exception as e:
        print(f"[Warning] pvlib optimal yield computation fallback ({e}). Using GHI proxy.")
        ghi = np.asarray(df_solar["ghi"], dtype=float) / 1000.0
        return np.clip(ghi, 0.0, 1.0)


def prepare_data_files(year: int = 2025, force_repopulate: bool = True) -> Tuple[Path, Path]:
    """Generates, enriches with optimal PV yield profile, and writes CSV dataset files into data/ directory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    market_path = DATA_DIR / f"market_data_{year}.csv"
    solar_path = DATA_DIR / f"solar_data_duesseldorf_{year}.csv"

    if force_repopulate or not market_path.exists():
        market_df = generate_benchmark_market_data(year=year)
        market_df.to_csv(market_path)
        print(f"[Info] Saved repopulated market data to {market_path}")

    if force_repopulate or not solar_path.exists():
        solar_df = fetch_open_meteo_solar(year=year)
        solar_df["pv_normalized_yield"] = compute_optimal_pv_yield(
            solar_df, lat=DUESSELDORF_LAT, lon=DUESSELDORF_LON, tilt=38.0, azimuth=180.0
        )
        solar_df.to_csv(solar_path)
        print(f"[Info] Saved repopulated solar weather data with cached pv_normalized_yield to {solar_path}")

    return market_path, solar_path


def verify_solver_availability(solver_name: str = "appsi_highs") -> bool:
    """Verifies that Pyomo appsi_highs and highspy solver are installed and available."""
    try:
        import highspy
        import pyomo.environ as po

        opt = po.SolverFactory(solver_name)
        available = opt.available()
        if available:
            ver = f"{highspy.HIGHS_VERSION_MAJOR}.{highspy.HIGHS_VERSION_MINOR}.{highspy.HIGHS_VERSION_PATCH}"
            print(f"[Info] Solver '{solver_name}' (highspy v{ver}) verified available.")
        return available
    except Exception as e:
        print(f"[Warning] Solver '{solver_name}' check failed: {e}")
        return False


if __name__ == "__main__":
    m_p, s_p = prepare_data_files(year=2025, force_repopulate=True)
    solver_ok = verify_solver_availability()
    print(f"Data repopulation complete. Solver verified: {solver_ok}")

