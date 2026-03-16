from config import FRED_SERIES
from data.sources.fred_source import get_fred_series
from data.processing.transforms import build_indicator_dict
from models.inflation.nowcast import calculate_real_inflation_nowcast


def fetch_raw_series():
    """
    Lädt alle Makroindikatoren aus der FRED API.
    """

    raw_data = {}

    for name, series_id in FRED_SERIES.items():

        try:

            df = get_fred_series(series_id)

            raw_data[name] = df

        except Exception as e:

            print(f"Warning: failed loading {name}")

    return raw_data


def build_indicators():

    """
    Wandelt Zeitreihen in YoY/MoM Indikatoren um.
    """

    raw_series = fetch_raw_series()

    indicators = build_indicator_dict(raw_series)

    return indicators


def build_nowcast():

    """
    Führt komplette Inflationsschätzung aus.
    """

    indicators = build_indicators()

    result = calculate_real_inflation_nowcast(indicators)

    return result


def run_pipeline():

    """
    Komplettes Pipeline-Ergebnis.
    """

    result = build_nowcast()

    return result