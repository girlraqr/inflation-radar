import pandas as pd

from data.sources.fred_source import get_fred_series
from config import FRED_SERIES
from models.ml.dataset_builder import DatasetBuilder


def load_macro_dataframe():

    data = {}

    for name, series_id in FRED_SERIES.items():

        try:
            df = get_fred_series(series_id)

            if df is None or df.empty:
                continue

            df = df.rename(columns={"value": name})

            data[name] = df[name]

        except Exception:
            print(f"⚠️ Fehler bei {name}")

    if not data:
        raise ValueError("Keine Daten geladen")

    df = pd.concat(data.values(), axis=1)

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    print(f"✅ Raw Macro DF: {df.shape}")

    return df


def resample_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """
    🔥 WICHTIG: bringt alle Daten auf Month-End
    """

    df = df.resample("M").last()

    print(f"✅ Monthly DF: {df.shape}")

    return df


def add_cpi_yoy(df: pd.DataFrame) -> pd.DataFrame:

    cpi_candidates = ["cpi", "CPIAUCSL", "headline_cpi"]

    cpi_col = None
    for col in df.columns:
        if col.lower() in [c.lower() for c in cpi_candidates]:
            cpi_col = col
            break

    if cpi_col is None:
        raise ValueError(f"Keine CPI-Spalte gefunden. Vorhanden: {df.columns.tolist()}")

    print(f"✅ CPI column erkannt: {cpi_col}")

    df["cpi_yoy"] = df[cpi_col].pct_change(12) * 100

    return df


def main():

    print("🚀 Building ML dataset...")

    # --------------------------------------------------
    # STEP 1: RAW DATA
    # --------------------------------------------------

    df_raw = load_macro_dataframe()

    # --------------------------------------------------
    # STEP 2: MONTH-END FIX
    # --------------------------------------------------

    df_raw = resample_monthly(df_raw)

    # --------------------------------------------------
    # STEP 3: CPI YoY
    # --------------------------------------------------

    df_raw = add_cpi_yoy(df_raw)

    # --------------------------------------------------
    # STEP 4: DATASET BUILDER
    # --------------------------------------------------

    builder = DatasetBuilder(df_raw)

    df_dataset = builder.build()

    print(f"✅ Dataset built: {df_dataset.shape}")

    # --------------------------------------------------
    # STEP 5: SAVE
    # --------------------------------------------------

    output_path = "storage/cache/ml_dataset.csv"

    df_dataset.to_csv(output_path)

    print(f"💾 Saved → {output_path}")

    print(df_dataset.tail())


if __name__ == "__main__":
    main()