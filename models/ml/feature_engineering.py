import pandas as pd


class FeatureEngineering:
    """
    Feature Engineering für Monthly Macro-Daten.

    Annahmen:
    - Input-Daten sind MONTHLY
    - Index ist DatetimeIndex (Month-End)
    - Keine Targets hier (nur Features!)
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    # --------------------------------------------------
    # Helper Funktionen
    # --------------------------------------------------

    def safe_series(self, col: str) -> pd.Series:
        if col not in self.df.columns:
            print(f"[WARNUNG] Spalte fehlt: {col}")
            return pd.Series(index=self.df.index, dtype=float)
        return self.df[col]

    @staticmethod
    def yoy(series: pd.Series) -> pd.Series:
        return series.pct_change(12, fill_method=None) * 100

    @staticmethod
    def mom(series: pd.Series) -> pd.Series:
        return series.pct_change(1, fill_method=None) * 100

    # --------------------------------------------------
    # Feature Engineering
    # --------------------------------------------------

    def create_features(self) -> pd.DataFrame:
        df = self.df.copy()

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------

        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("[ERROR] Index ist kein DatetimeIndex!")

        if not all(df.index.is_month_end):
            raise ValueError("[ERROR] Daten sind nicht Month-End basiert!")

        print("[INFO] Monthly Frequency bestätigt (Month-End Index)")

        # --------------------------------------------------
        # Inflation
        # --------------------------------------------------

        df["cpi_yoy"] = self.yoy(self.safe_series("cpi"))
        df["core_cpi_yoy"] = self.yoy(self.safe_series("core_cpi"))
        df["ppi_yoy"] = self.yoy(self.safe_series("ppi"))

        # --------------------------------------------------
        # Labor
        # --------------------------------------------------

        df["unemployment_change"] = self.safe_series("unemployment").diff()
        df["payrolls_yoy"] = self.yoy(self.safe_series("nonfarm_payrolls"))
        df["wages_yoy"] = self.yoy(self.safe_series("avg_hourly_earnings"))

        # --------------------------------------------------
        # Money
        # --------------------------------------------------

        df["m2_growth_yoy"] = self.yoy(self.safe_series("money_supply"))

        # --------------------------------------------------
        # Rates
        # --------------------------------------------------

        df["yield_curve_10y_2y"] = (
            self.safe_series("ust_10y") - self.safe_series("ust_2y")
        )

        df["yield_curve_10y_3m"] = (
            self.safe_series("ust_10y") - self.safe_series("ust_3m")
        )

        df["real_rate_ff"] = (
            self.safe_series("fed_funds") - df["cpi_yoy"]
        )

        df["real_rate_10y"] = (
            self.safe_series("ust_10y")
            - self.safe_series("inflation_expectations_10y")
        )

        # --------------------------------------------------
        # Growth
        # --------------------------------------------------

        df["gdp_yoy"] = self.yoy(self.safe_series("gdp")).ffill()

        df["industrial_production_yoy"] = self.yoy(
            self.safe_series("industrial_production")
        )

        df["housing_starts_yoy"] = self.yoy(
            self.safe_series("housing_starts")
        )

        df["retail_sales_yoy"] = self.yoy(
            self.safe_series("retail_sales")
        )

        # --------------------------------------------------
        # Inflation Expectations
        # --------------------------------------------------

        breakeven = self.safe_series("inflation_expectations_10y")

        df["breakeven_10y_change"] = breakeven.diff()
        df["breakeven_trend"] = breakeven.rolling(3).mean()

        # --------------------------------------------------
        # Commodities
        # --------------------------------------------------

        oil = self.safe_series("wti_oil")

        df["oil_yoy"] = self.yoy(oil)
        df["oil_mom"] = self.mom(oil)
        df["oil_trend_3m"] = oil.rolling(3).mean()
        df["oil_trend_6m"] = oil.rolling(6).mean()

        # --------------------------------------------------
        # Credit
        # --------------------------------------------------

        df["credit_spread_baa_aaa"] = (
            self.safe_series("baa_corp_yield")
            - self.safe_series("aaa_corp_yield")
        )

        # --------------------------------------------------
        # Dollar
        # --------------------------------------------------

        df["dollar_yoy"] = self.yoy(
            self.safe_series("broad_dollar_index")
        )

        # --------------------------------------------------
        # Inflation Dynamics (nur für 1M / 6M sinnvoll)
        # --------------------------------------------------

        df["inflation_momentum"] = df["cpi_yoy"].diff()
        df["inflation_trend_3m"] = df["cpi_yoy"].rolling(3).mean()
        df["inflation_trend_6m"] = df["cpi_yoy"].rolling(6).mean()
        df["inflation_acceleration"] = df["cpi_yoy"].diff().diff()

        # --------------------------------------------------
        # Cross Features
        # --------------------------------------------------

        df["growth_vs_inflation"] = df["gdp_yoy"] - df["cpi_yoy"]
        df["policy_gap"] = self.safe_series("fed_funds") - df["cpi_yoy"]

        # --------------------------------------------------
        # Forward / Regime Features
        # --------------------------------------------------

        df["yield_curve_change"] = df["yield_curve_10y_2y"].diff()
        df["real_rate_change"] = df["real_rate_ff"].diff()

        # --------------------------------------------------
        # Lags (nur für bestimmte Horizons sinnvoll)
        # --------------------------------------------------

        df["cpi_lag_1"] = df["cpi_yoy"].shift(1)
        df["cpi_lag_3"] = df["cpi_yoy"].shift(3)
        df["cpi_lag_6"] = df["cpi_yoy"].shift(6)

        # --------------------------------------------------
        # CLEANING
        # --------------------------------------------------

        df = df.replace([float("inf"), float("-inf")], pd.NA)

        before = len(df)
        df = df.dropna()
        after = len(df)

        print(f"[INFO] Rows vor dropna: {before}")
        print(f"[INFO] Rows nach dropna: {after}")

        return df


# --------------------------------------------------
# 🔥 FINAL FEATURE SETS (ALPHA VERSION)
# --------------------------------------------------

FEATURE_SETS = {

    # --------------------------------------------------
    # 1M → kurzfristig (CPI erlaubt)
    # --------------------------------------------------
    "1m": [
        "cpi_yoy",
        "core_cpi_yoy",
        "cpi_lag_1",
        "inflation_momentum",
        "oil_mom",
        "yield_curve_10y_2y",
        "real_rate_ff",
    ],

    # --------------------------------------------------
    # 3M → 🔥 KEIN CPI → echtes Forward Signal
    # --------------------------------------------------
    "3m": [
        "oil_trend_3m",
        "yield_curve_10y_2y",
        "breakeven_trend",
    ],

    # --------------------------------------------------
    # 6M → strukturell stark (bereits gut)
    # --------------------------------------------------
    "6m": [
        "inflation_trend_6m",
        "cpi_lag_6",
        "oil_trend_6m",
        "yield_curve_10y_3m",
        "real_rate_10y",
        "breakeven_trend",
        "credit_spread_baa_aaa",
    ],
}