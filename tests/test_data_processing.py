import pandas as pd

from data.processing.transforms import (
    calculate_yoy,
    calculate_mom,
    latest_yoy,
    latest_mom
)


def mock_dataframe():

    data = {
        "date": pd.date_range("2022-01-01", periods=24, freq="ME"),
        "value": list(range(100, 124))
    }

    return pd.DataFrame(data)


def test_calculate_yoy():

    df = mock_dataframe()

    result = calculate_yoy(df)

    assert "yoy" in result.columns
    assert isinstance(result["yoy"].iloc[-1], float)


def test_calculate_mom():

    df = mock_dataframe()

    result = calculate_mom(df)

    assert "mom" in result.columns
    assert isinstance(result["mom"].iloc[-1], float)


def test_latest_yoy():

    df = mock_dataframe()

    value = latest_yoy(df)

    assert isinstance(value, float)


def test_latest_mom():

    df = mock_dataframe()

    value = latest_mom(df)

    assert isinstance(value, float)