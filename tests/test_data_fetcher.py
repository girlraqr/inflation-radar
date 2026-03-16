from data.ingestion.collector import build_indicators
from data.ingestion.collector import build_nowcast


def test_build_indicators():

    indicators = build_indicators()

    assert isinstance(indicators, dict)


def test_build_nowcast():

    result = build_nowcast()

    assert isinstance(result, dict)

    assert "real_inflation_estimate" in result