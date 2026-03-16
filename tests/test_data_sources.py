from data.sources.fred_source import get_fred_latest


def test_fred_series_returns_number():

    value = get_fred_latest("CPIAUCSL")

    assert isinstance(value, float)