import os
import numpy as np
import pandas as pd

from models.ml.inflation_model import InflationModel
from models.ml.feature_engineering import FEATURE_SETS
from storage.model_metrics import save_model_metrics


# --------------------------------------------------
# TARGET MAPPING
# --------------------------------------------------

def get_targets(horizon):

    if horizon == "1m":
        return "target_1m", None

    if horizon == "3m":
        return "target_3m_delta", "target_3m_direction"

    if horizon == "6m":
        return "target_6m_delta", "target_6m_direction"

    raise ValueError(f"Unknown horizon: {horizon}")


# --------------------------------------------------
# WALK-FORWARD REGRESSION
# --------------------------------------------------

def walk_forward_regression(df, features, target, horizon):

    predictions = []
    actuals = []

    start_idx = max(60, int(len(df) * 0.4))

    for i in range(start_idx, len(df) - 6):

        train = df.iloc[:i]
        test = df.iloc[i:i+1]

        X_train = train[features]
        y_train = train[target]

        X_test = test[features]

        model = InflationModel(horizon)
        model.fit(X_train, y_reg=y_train)

        pred = model.predict(X_test)[0]

        actual = df.iloc[i]["target_1m"]

        predictions.append(pred)
        actuals.append(actual)

    return np.array(predictions), np.array(actuals)


# --------------------------------------------------
# WALK-FORWARD CLASSIFICATION
# --------------------------------------------------

def walk_forward_classification(df, features, target, horizon):

    predictions = []
    actuals = []

    start_idx = max(60, int(len(df) * 0.4))

    for i in range(start_idx, len(df)):

        train = df.iloc[:i]
        test = df.iloc[i:i+1]

        X_train = train[features]
        y_train = train[target]

        X_test = test[features]
        y_test = test[target]

        model = InflationModel(horizon)
        model.fit(X_train, y_reg=None, y_clf=y_train)

        prob = model.predict_proba(X_test)[0]
        pred = int(prob > 0.5)

        predictions.append(pred)
        actuals.append(int(y_test.values[0]))

    return np.array(predictions), np.array(actuals)


# --------------------------------------------------
# METRICS
# --------------------------------------------------

def compute_regression_metrics(y_true, y_pred):

    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            "mae": np.nan,
            "rmse": np.nan,
            "directional_accuracy": np.nan,
            "naive_mae": np.nan,
            "skill": np.nan
        }

    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

    return {
        "mae": float(mae),
        "rmse": float(rmse)
    }


# --------------------------------------------------
# TRAINING PIPELINE
# --------------------------------------------------

def train_all_models(df: pd.DataFrame):

    results = {}

    for horizon in ["1m", "3m", "6m"]:

        print(f"\n🚀 Training {horizon}")

        target_reg, target_clf = get_targets(horizon)
        base_features = FEATURE_SETS[horizon]

        # 🔥 FIX: nur vorhandene Features nutzen
        features = [f for f in base_features if f in df.columns]

        if len(features) < 3:
            raise ValueError(f"Zu wenige Features für {horizon}: {features}")

        print(f"✅ Features: {features}")

        # 🔥 FIX: required cols korrekt
        required_cols = features + [target_reg]
        if target_clf:
            required_cols.append(target_clf)

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Fehlende Spalten: {missing}")

        df_clean = df[required_cols].dropna().copy()

        print(f"📊 Rows: {len(df_clean)}")

        model = InflationModel(horizon)

        # -------------------------
        # 1M Regression
        # -------------------------
        if horizon == "1m":

            preds, actuals = walk_forward_regression(
                df_clean,
                features,
                target_reg,
                horizon
            )

            metrics = compute_regression_metrics(actuals, preds)

            print(f"{horizon} Metrics:", metrics)

            model.fit(df_clean[features], y_reg=df_clean[target_reg])

            results[horizon] = metrics

        # -------------------------
        # 3M / 6M Classification
        # -------------------------
        else:

            preds, actuals = walk_forward_classification(
                df_clean,
                features,
                target_clf,
                horizon
            )

            accuracy = (preds == actuals).mean()

            print(f"{horizon} Accuracy: {accuracy:.4f}")

            model.fit(
                df_clean[features],
                y_reg=df_clean[target_reg],
                y_clf=df_clean[target_clf]
            )

            results[horizon] = {
                "direction_accuracy": float(accuracy)
            }

        model.save_model(f"storage/cache/inflation_model_{horizon}.joblib")

    save_model_metrics(results)

    return results


# --------------------------------------------------
# SERVICE WRAPPER
# --------------------------------------------------

class TrainingService:

    @staticmethod
    def run_full_pipeline(deploy: bool = True):

        print("🚀 Starting training pipeline...")

        df_dataset = pd.read_csv(
            "storage/cache/ml_dataset.csv",
            index_col=0,
            parse_dates=True
        )

        df_features = pd.read_csv(
            "storage/cache/ml_features.csv",
            index_col=0,
            parse_dates=True
        )

        df = df_dataset.copy()

        # 🔥 SAFE MERGE
        for col in df_features.columns:
            if col not in df.columns:
                df[col] = df_features[col]

        print(f"✅ Final DF: {df.shape}")

        return train_all_models(df)

    @staticmethod
    def run_training_by_mode():

        from storage.training_config import get_mode

        if get_mode() == "manual":
            return {"status": "skipped"}

        return TrainingService.run_full_pipeline()