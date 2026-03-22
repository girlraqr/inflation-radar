import pandas as pd

from models.ml.feature_engineering import FeatureEngineering


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    🔥 Mapping deiner Spalten → Feature Engine erwartet
    """

    mapping = {
        "oil_price": "wti_oil",
        "fed_rate": "fed_funds",
        "10y_treasury": "ust_10y",
        "2y_treasury": "ust_2y",
        "sp500": "sp500",  # ok
        "m2": "money_supply",
        "unemployment": "unemployment_rate",
    }

    df = df.rename(columns=mapping)

    print("✅ Columns mapped")

    return df


def main():

    print("🚀 Feature Engineering gestartet")

    # --------------------------------------------------
    # LOAD DATASET
    # --------------------------------------------------

    path = "storage/cache/ml_dataset.csv"

    df = pd.read_csv(path, index_col=0, parse_dates=True)

    print("Dataset geladen")
    print(df.tail())

    # --------------------------------------------------
    # 🔥 FIX: COLUMN MAPPING
    # --------------------------------------------------

    df = rename_columns(df)

    # --------------------------------------------------
    # FEATURE ENGINEERING
    # --------------------------------------------------

    features = FeatureEngineering(df)

    feature_df = features.create_features()

    print("Feature Dataset erstellt")
    print(feature_df.tail())
    print("Shape:", feature_df.shape)

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    output_path = "storage/cache/ml_features.csv"

    feature_df.to_csv(output_path)

    print(f"💾 Saved → {output_path}")


if __name__ == "__main__":
    main()