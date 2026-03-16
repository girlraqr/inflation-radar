import requests
import pandas as pd
from config import FRED_API_KEY

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def get_fred_series(series_id):
    """
    Returns full time series as DataFrame
    """

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json"
    }

    try:

        response = requests.get(BASE_URL, params=params, timeout=10)

        response.raise_for_status()

        data = response.json()

        observations = data["observations"]

        df = pd.DataFrame(observations)

        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        df["date"] = pd.to_datetime(df["date"])

        df = df.dropna()

        return df

    except Exception as e:

        print("FRED ERROR:", e)
        print("Warning: using mock data")

        dates = pd.date_range("2022-01-01", periods=24, freq="ME")

        values = list(range(100, 124))

        return pd.DataFrame({
            "date": dates,
            "value": values
        })


def get_fred_latest(series_id):
    """
    Returns latest value as float
    """

    df = get_fred_series(series_id)

    return float(df.iloc[-1]["value"])