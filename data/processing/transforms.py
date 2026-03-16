import pandas as pd


def clean_series(df):
    """
    Säubert eine FRED Zeitreihe
    """

    df = df.copy()

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna()

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date")

    return df


def calculate_yoy(df):
    """
    Berechnet Year-over-Year Veränderung
    """

    df = clean_series(df)

    df["yoy"] = df["value"].pct_change(periods=12) * 100

    return df


def calculate_mom(df):
    """
    Berechnet Month-over-Month Veränderung
    """

    df = clean_series(df)

    df["mom"] = df["value"].pct_change(periods=1) * 100

    return df


def latest_yoy(df):
    """
    Gibt den neuesten YoY Wert zurück
    """

    df = calculate_yoy(df)

    value = df.iloc[-1]["yoy"]

    return float(value)


def latest_mom(df):
    """
    Gibt den neuesten MoM Wert zurück
    """

    df = calculate_mom(df)

    value = df.iloc[-1]["mom"]

    return float(value)


def moving_average(series, window=3):
    """
    Glättung von Zeitreihen
    """

    return series.rolling(window).mean()


def build_indicator_dict(series_dict):
    """
    Wandelt DataFrames in ein Indicator Dictionary um
    """

    indicators = {}

    for name, df in series_dict.items():

        try:

            indicators[f"{name}_yoy"] = latest_yoy(df)

            indicators[f"{name}_mom"] = latest_mom(df)

        except Exception:

            indicators[f"{name}_yoy"] = 0.0
            indicators[f"{name}_mom"] = 0.0

    return indicators