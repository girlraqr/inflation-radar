import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd

from models.ml.feature_engineering import FeatureEngineering
from models.ml.inflation_model import InflationModel


def main():
    df = pd.read_csv("storage/cache/ml_dataset.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.set_index("date")

    fe = FeatureEngineering(df)
    features = fe.create_features()

    latest = features.iloc[-1:]

    model = InflationModel(horizon="3m")

    # 🔥 DAS ist der richtige Call
    model.load_model("storage/cache/inflation_model_3m.joblib")

    proba = model.predict_proba(latest)

    print("\n=== DEBUG PREDICT_PROBA ===")
    print("RAW OUTPUT:")
    print(proba)
    print("TYPE:", type(proba))

    try:
        print("proba[0]:", proba[0])
    except Exception:
        pass

    try:
        print("proba[0][1]:", proba[0][1])
    except Exception:
        pass


if __name__ == "__main__":
    main()