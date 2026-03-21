import requests
import pandas as pd
from config import FRED_API_KEY


BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class FredSource:

    def get_series(self, series_id, start_date="1960-01-01"):

        params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "observation_start": start_date
        }

        response = requests.get(BASE_URL, params=params, timeout=30)

        if response.status_code != 200:
            raise Exception(f"FRED API Error: {response.status_code}")

        data = response.json()

        if "observations" not in data:
            raise Exception(f"FRED response error: {data}")

        df = pd.DataFrame(data["observations"])

        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        df = df.set_index("date")

        return df[["value"]]


# --------------------------------------------------
# Backwards Compatibility (für bestehende Pipeline)
# --------------------------------------------------

def get_fred_series(series_id, start_date="1960-01-01"):
    """
    Alte Funktion für bestehende Module.
    """
    source = FredSource()
    return source.get_series(series_id, start_date)