from services.signal_asset_mapping_service import SignalAssetMappingService


def test_disinflation_maps_to_equities_bias():
    service = SignalAssetMappingService()

    result = service.map_single_signal(
        signal="disinflation",
        conviction=0.90,
        regime="disinflation",
    )

    assert "SPY" in result.asset_weights
    assert "QQQ" in result.asset_weights
    assert result.asset_weights["SPY"] > 0
    assert result.asset_weights["QQQ"] > 0
    assert abs(sum(result.asset_weights.values()) - 1.0) < 1e-9


def test_inflation_spike_maps_to_real_assets():
    service = SignalAssetMappingService()

    result = service.map_single_signal(
        signal="inflation_spike",
        conviction=0.95,
        regime="inflation_spike",
    )

    assert "DBC" in result.asset_weights or "GLD" in result.asset_weights
    assert abs(sum(result.asset_weights.values()) - 1.0) < 1e-9


def test_portfolio_mapping_combines_multiple_signals():
    service = SignalAssetMappingService()

    result = service.map_signals_to_assets(
        signals=[
            {"signal": "inflation_cooling", "conviction": 0.8},
            {"signal": "disinflation", "conviction": 0.7},
            {"signal": "inflation_spike", "conviction": 0.2},
        ],
        regime="disinflation",
        top_n=3,
    )

    assert "weights" in result
    assert "mapping_breakdown" in result
    assert abs(sum(result["weights"].values()) - 1.0) < 1e-9
    assert len(result["mapping_breakdown"]) == 3


def test_unknown_signal_falls_back_to_default():
    service = SignalAssetMappingService()

    result = service.map_single_signal(
        signal="something_custom_and_unknown",
        conviction=0.5,
        regime="neutral",
    )

    assert "SHY" in result.asset_weights
    assert abs(sum(result.asset_weights.values()) - 1.0) < 1e-9