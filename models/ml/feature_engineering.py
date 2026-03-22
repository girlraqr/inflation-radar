import pandas as pd
import numpy as np


# --------------------------------------------------
# FEATURE SETS (bleibt wie gehabt)
# --------------------------------------------------

FEATURE_SETS = {
    "1m": [
        "cpi_yoy",
        "core_cpi_yoy",
        "ppi_yoy",
        "inflation_momentum",
        "oil_mom",
        "yield_curve_10y_2y",
        "real_rate_ff"
    ],
    "3m": [
        "cpi_yoy",
        "inflation_trend_3m",
        "inflation_acceleration",
        "oil_trend_3m",
        "yield_curve_10y_2y",
        "real_rate_10y"
    ],
    "6m": [
        "cpi_yoy",
        "inflation_trend_6m",
        "growth_vs_inflation",
        "oil_trend_6m",
        "yield_curve_10y_3m",
        "real_rate_10y"
    ]
}


# --------------------------------------------------
# FEATURE ENGINEERING
# --------------------------------------------------

class FeatureEngineering:

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def validate(self):

        if not isinstance(self.df.index, pd.DatetimeIndex):
            raise ValueError("[ERROR] Index muss DatetimeIndex sein")

        # 🔥 Month-End Check
        if not all(self.df.index.is_month_end):
            raise ValueError("[ERROR] Daten sind nicht Month-End basiert!")

        print("[INFO] Monthly Frequency bestätigt (Month-End Index)")

    # --------------------------------------------------
    # FEATURE BUILDING
    # --------------------------------------------------

    def create_features(self):

        self.validate()

        df = self.df.copy()

        print("[INFO] Rows vor Feature Engineering:", len(df))

        # --------------------------------------------------
        # BASIC TRANSFORMS
        # --------------------------------------------------

        if "core_cpi" in df.columns:
            df["core_cpi_yoy"] = df["core_cpi"].pct_change(12, fill_method=None) * 100

        if "ppi" in df.columns:
            df["ppi_yoy"] = df["ppi"].pct_change(12, fill_method=None) * 100

        if "unemployment_rate" in df.columns:
            df["unemployment_change"] = df["unemployment_rate"].diff()

        if "money_supply" in df.columns:
            df["m2_growth_yoy"] = df["money_supply"].pct_change(12, fill_method=None)

        # --------------------------------------------------
        # YIELD CURVES
        # --------------------------------------------------

        if "ust_10y" in df.columns and "ust_2y" in df.columns:
            df["yield_curve_10y_2y"] = df["ust_10y"] - df["ust_2y"]

        if "ust_10y" in df.columns and "ust_3m" in df.columns:
            df["yield_curve_10y_3m"] = df["ust_10y"] - df["ust_3m"]

        # --------------------------------------------------
        # REAL RATES
        # --------------------------------------------------

        if "fed_funds" in df.columns:
            df["real_rate_ff"] = df["fed_funds"] - df["cpi_yoy"]

        if "ust_10y" in df.columns:
            df["real_rate_10y"] = df["ust_10y"] - df["cpi_yoy"]

        # --------------------------------------------------
        # OIL FEATURES
        # --------------------------------------------------

        if "wti_oil" in df.columns:
            df["oil_yoy"] = df["wti_oil"].pct_change(12, fill_method=None)
            df["oil_mom"] = df["wti_oil"].pct_change(1, fill_method=None)
            df["oil_trend_3m"] = df["wti_oil"].rolling(3).mean()
            df["oil_trend_6m"] = df["wti_oil"].rolling(6).mean()

        # --------------------------------------------------
        # INFLATION FEATURES
        # --------------------------------------------------

        df["inflation_momentum"] = df["cpi_yoy"].diff()
        df["inflation_trend_3m"] = df["cpi_yoy"].rolling(3).mean()
        df["inflation_trend_6m"] = df["cpi_yoy"].rolling(6).mean()
        df["inflation_acceleration"] = df["inflation_momentum"].diff()

        # --------------------------------------------------
        # LAGS
        # --------------------------------------------------

        df["cpi_lag_1"] = df["cpi_yoy"].shift(1)
        df["cpi_lag_3"] = df["cpi_yoy"].shift(3)
        df["cpi_lag_6"] = df["cpi_yoy"].shift(6)

        # --------------------------------------------------
        # 🔥 STABILISIERUNG (WICHTIG)
        # --------------------------------------------------

        print("[INFO] NaN Anteil pro Spalte (Top 10):")
        print(df.isna().mean().sort_values(ascending=False).head(10))

        # 🔥 Forward Fill (Makro Standard)
        df = df.sort_index()
        df = df.ffill()

        # 🔥 Nur komplett kaputte Reihen entfernen
        threshold = int(len(df.columns) * 0.7)
        df = df.dropna(thresh=threshold)

        print("[INFO] Rows nach Stabilisierung:", len(df))

        return df