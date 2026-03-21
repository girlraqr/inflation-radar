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

        # --------------------------------------------------
        # DELTA → LEVEL (für 3M / 6M)
        # --------------------------------------------------

        if horizon in ["3m", "6m"]:
            horizon_steps = int(horizon.replace("m", ""))

            current = df.iloc[i]["cpi_yoy"]
            pred = current + pred

            actual = df.iloc[i + horizon_steps]["cpi_yoy"]

        else:
            actual = df.iloc[i]["target_1m"]

        predictions.append(pred)
        actuals.append(actual)

    return np.array(predictions), np.array(actuals)


# --------------------------------------------------
# WALK-FORWARD CLASSIFICATION (🔥 FIX)
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
# METRICS (Regression)
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

    # Directional Accuracy
    if len(y_true) > 1:
        y_true_diff = np.diff(y_true)
        y_pred_diff = np.diff(y_pred)

        directional = np.mean(np.sign(y_true_diff) == np.sign(y_pred_diff))
    else:
        directional = np.nan

    # Naive Benchmark
    naive = pd.Series(y_true).shift(1).values

    valid_mask = ~np.isnan(y_true[1:]) & ~np.isnan(naive[1:])

    if valid_mask.sum() == 0:
        naive_mae = np.nan
    else:
        naive_mae = np.mean(
            np.abs(y_true[1:][valid_mask] - naive[1:][valid_mask])
        )

    if naive_mae == 0 or np.isnan(naive_mae):
        skill = np.nan
    else:
        skill = 1 - (mae / naive_mae)

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "directional_accuracy": float(directional),
        "naive_mae": float(naive_mae),
        "skill": float(skill)
    }


# --------------------------------------------------
# TRAINING PIPELINE
# --------------------------------------------------

def train_all_models(df: pd.DataFrame):

    results = {}

    for horizon in ["1m", "3m", "6m"]:

        print(f"\n🚀 Training {horizon}")

        target_reg, target_clf = get_targets(horizon)
        features = FEATURE_SETS[horizon]

        df_clean = df.dropna(subset=features + [target_reg]).copy()

        model = InflationModel(horizon)

        # --------------------------------------------------
        # REGRESSION (nur 1M relevant)
        # --------------------------------------------------

        if horizon == "1m":

            preds, actuals = walk_forward_regression(
                df_clean,
                features,
                target_reg,
                horizon
            )

            metrics = compute_regression_metrics(actuals, preds)

            print(f"{horizon} Metrics:", metrics)

            X = df_clean[features]
            y = df_clean[target_reg]

            model.fit(X, y_reg=y)

            results[horizon] = metrics

        # --------------------------------------------------
        # CLASSIFICATION (3M / 6M)
        # --------------------------------------------------

        else:

            preds, actuals = walk_forward_classification(
                df_clean,
                features,
                target_clf,
                horizon
            )

            accuracy = (preds == actuals).mean()

            print(f"{horizon} Direction Accuracy: {accuracy:.4f}")

            # Final Training
            X = df_clean[features]
            y_reg = df_clean[target_reg]
            y_clf = df_clean[target_clf]

            model.fit(X, y_reg=y_reg, y_clf=y_clf)

            results[horizon] = {
                "direction_accuracy": float(accuracy)
            }

        # --------------------------------------------------
        # SAVE MODEL
        # --------------------------------------------------

        model.save_model(f"storage/cache/inflation_model_{horizon}.joblib")

    save_model_metrics(results)

    return results