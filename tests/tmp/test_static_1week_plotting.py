import pytest
import warnings
import pandas as pd
import pypsa
from typing import Dict, Any
from src.optimization_model import FacilityProjectConfig
from src.utils import (
    plot_dispatch_stacks_interactive,
    plot_market_prices_interactive,
    plot_dispatch_stacks_static,
    plot_market_prices_static,
    plot_scenario_cost_per_ton,
    _slice_snapshots_by_window,
)


@pytest.fixture
def dummy_results() -> Dict[str, Any]:
    """Creates a minimal solved PyPSA network for plotting tests."""
    n = pypsa.Network()
    snapshots = pd.date_range("2025-01-01 00:00", "2025-01-15 23:00", freq="1h")
    n.set_snapshots(snapshots)

    # Buses
    n.add("Bus", "b_elec")
    n.add("Bus", "b_gas")

    # Generators
    n.add("Generator", "grid_electricity", bus="b_elec", p_nom=1000)
    n.generators_t.p["grid_electricity"] = pd.Series(500.0, index=snapshots)
    n.generators_t.marginal_cost["grid_electricity"] = pd.Series(0.12, index=snapshots)  # 120 €/MWh

    n.add("Generator", "grid_gas", bus="b_gas", p_nom=2000)
    n.generators_t.p["grid_gas"] = pd.Series(800.0, index=snapshots)
    n.generators_t.marginal_cost["grid_gas"] = pd.Series(0.04, index=snapshots)  # 40 €/MWh

    config = FacilityProjectConfig(start_time="01/01/2025", end_time="15/01/2025")
    return {"network": n, "config": config, "total_cost_eur": 5000000.0}


def test_slice_snapshots_default(dummy_results):
    n = dummy_results["network"]
    config = dummy_results["config"]

    # Default should select start_time from config
    sliced = _slice_snapshots_by_window(n, start_time=None, duration_days=7.0, config=config)
    assert len(sliced) == 169  # 7 days * 24 + 1 endpoint inclusive
    assert sliced[0] == pd.Timestamp("2025-01-01 00:00:00")
    assert sliced[-1] == pd.Timestamp("2025-01-08 00:00:00")


def test_slice_snapshots_custom_date(dummy_results):
    n = dummy_results["network"]
    config = dummy_results["config"]

    sliced = _slice_snapshots_by_window(n, start_time="05/01/2025 00:00:00", duration_days=7.0, config=config)
    assert len(sliced) == 169
    assert sliced[0] == pd.Timestamp("2025-01-05 00:00:00")
    assert sliced[-1] == pd.Timestamp("2025-01-12 00:00:00")


def test_slice_snapshots_out_of_bounds_warning(dummy_results):
    n = dummy_results["network"]
    config = dummy_results["config"]

    with pytest.warns(UserWarning, match="outside the optimization period"):
        sliced = _slice_snapshots_by_window(n, start_time="01/01/2030 00:00:00", duration_days=7.0, config=config)

    # Should fall back to default start_time without crashing
    assert sliced[0] == pd.Timestamp("2025-01-01 00:00:00")


def test_plot_dispatch_stacks_static_mode(dummy_results):
    # Call static function directly
    fig = plot_dispatch_stacks_static(dummy_results, start_time="01/01/2025 00:00:00", duration_days=7.0)
    assert fig is not None

    # Call interactive wrapper with mode="static"
    fig2 = plot_dispatch_stacks_interactive(dummy_results, mode="static", start_time="01/01/2025 00:00:00")
    assert fig2 is not None


def test_plot_market_prices_static_mode(dummy_results):
    fig = plot_market_prices_static(dummy_results, start_time="01/01/2025 00:00:00")
    assert fig is not None

    fig2 = plot_market_prices_interactive(dummy_results, mode="static", start_time="01/01/2025 00:00:00")
    assert fig2 is not None


def test_interactive_mode_warning(dummy_results):
    with pytest.warns(UserWarning, match="start_time.*active for static viewing mode"):
        fig = plot_market_prices_interactive(dummy_results, mode="interactive", start_time="01/01/2025 00:00:00")
    assert fig is not None


def test_plot_scenario_cost_per_ton_static_default(dummy_results):
    fig = plot_scenario_cost_per_ton({
        "Baseline": 145.20,
        "Operation Hub": dummy_results,
    })
    assert fig is not None

