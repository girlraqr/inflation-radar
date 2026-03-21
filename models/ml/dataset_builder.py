import pandas as pd


class DatasetBuilder:

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def validate(self):
        if not isinstance(self.df.index, pd.DatetimeIndex):
            raise ValueError("Index muss DatetimeIndex sein")

        if "cpi_yoy" not in self.df.columns:
            raise ValueError("cpi_yoy fehlt")

    def build_targets(self):

        df = self.df.copy()

        # -------------------------
        # Regression Targets
        # -------------------------

        df["target_1m"] = df["cpi_yoy"].shift(-1)
        df["target_3m"] = df["cpi_yoy"].shift(-3)
        df["target_6m"] = df["cpi_yoy"].shift(-6)

        df["target_3m_delta"] = df["target_3m"] - df["cpi_yoy"]
        df["target_6m_delta"] = df["target_6m"] - df["cpi_yoy"]

        # -------------------------
        # 🔥 Classification Targets
        # -------------------------

        df["target_3m_direction"] = (df["target_3m_delta"] > 0).astype(int)
        df["target_6m_direction"] = (df["target_6m_delta"] > 0).astype(int)

        return df

    def clean(self, df):

        target_cols = [
            "target_1m",
            "target_3m",
            "target_6m",
            "target_3m_delta",
            "target_6m_delta",
            "target_3m_direction",
            "target_6m_direction"
        ]

        return df.dropna(subset=target_cols)

    def build(self):

        self.validate()

        df = self.build_targets()
        df = self.clean(df)

        return df


def build_ml_dataset(df: pd.DataFrame) -> pd.DataFrame:
    return DatasetBuilder(df).build()