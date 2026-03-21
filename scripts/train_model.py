import pandas as pd

from models.ml.dataset_builder import build_ml_dataset
from services.ml.training_service import train_all_models


def load_features(path="storage/cache/ml_features.csv") -> pd.DataFrame:
    df = pd.read_csv(path, index_col="date")
    df.index = pd.to_datetime(df.index)

    print(f"[INFO] Daten geladen: {len(df)} rows")
    return df


def main():

    print("\n🚀 Starting Inflation Model Training Pipeline\n")

    # --------------------------------------------------
    # LOAD FEATURES
    # --------------------------------------------------

    df = load_features()

    # --------------------------------------------------
    # BUILD DATASET (inkl. Targets)
    # --------------------------------------------------

    df = build_ml_dataset(df)

    print(f"[INFO] Dataset nach Target-Build: {len(df)} rows")

    # --------------------------------------------------
    # TRAIN MODELS
    # --------------------------------------------------

    results = train_all_models(df)

    print("\n📊 FINAL RESULTS:")
    for horizon, metrics in results.items():
        print(f"\n{horizon.upper()}:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")

    print("\n✅ Training complete\n")


if __name__ == "__main__":
    main()