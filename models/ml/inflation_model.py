import os
import joblib
import numpy as np

from sklearn.linear_model import Ridge
from sklearn.linear_model import LogisticRegression
import lightgbm as lgb


class InflationModel:
    """
    Horizon-specific model:

    1M:
        - Regression: LightGBM

    3M:
        - Regression: Ridge + LightGBM (ensemble)
        - Classification: LightGBM

    6M:
        - Regression: Ridge
        - Classification: Logistic Regression
    """

    def __init__(self, horizon: str):
        self.horizon = horizon
        self.feature_columns = None

        # --------------------------------------------------
        # MODELS INITIALIZATION
        # --------------------------------------------------

        if horizon == "1m":
            self.model = lgb.LGBMRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=3
            )

        elif horizon == "3m":
            # Regression
            self.model_ridge = Ridge(alpha=1.0)
            self.model_lgb = lgb.LGBMRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=3
            )

            # Classification
            self.model_clf = lgb.LGBMClassifier(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=3
            )

        elif horizon == "6m":
            # Regression
            self.model = Ridge(alpha=1.0)

            # Classification
            self.model_clf = LogisticRegression(max_iter=1000)

        else:
            raise ValueError(f"Unsupported horizon: {horizon}")

    # --------------------------------------------------
    # TRAIN
    # --------------------------------------------------

    def fit(self, X, y_reg=None, y_clf=None):
        """
        Flexible training:

        - Walk-forward classification → only y_clf
        - Final training → both y_reg and y_clf
        """

        self.feature_columns = X.columns.tolist()

        # --------------------------------------------------
        # 3M MODEL
        # --------------------------------------------------

        if self.horizon == "3m":

            # Regression (nur wenn vorhanden)
            if y_reg is not None:
                self.model_ridge.fit(X, y_reg)
                self.model_lgb.fit(X, y_reg)

            # Classification (separat!)
            if y_clf is not None:
                self.model_clf.fit(X, y_clf)

        # --------------------------------------------------
        # 6M MODEL
        # --------------------------------------------------

        elif self.horizon == "6m":

            if y_reg is not None:
                self.model.fit(X, y_reg)

            if y_clf is not None:
                self.model_clf.fit(X, y_clf)

        # --------------------------------------------------
        # 1M MODEL
        # --------------------------------------------------

        elif self.horizon == "1m":

            if y_reg is not None:
                self.model.fit(X, y_reg)

    # --------------------------------------------------
    # REGRESSION PREDICT
    # --------------------------------------------------

    def predict(self, X):
        X = X[self.feature_columns]

        if self.horizon == "3m":
            pred_ridge = self.model_ridge.predict(X)
            pred_lgb = self.model_lgb.predict(X)

            # Stabiler Hybrid
            return 0.85 * pred_ridge + 0.15 * pred_lgb

        return self.model.predict(X)

    # --------------------------------------------------
    # CLASSIFICATION PREDICT
    # --------------------------------------------------

    def predict_proba(self, X):
        """
        Returns probability of inflation going UP
        """

        if self.horizon not in ["3m", "6m"]:
            return None

        X = X[self.feature_columns]

        probs = self.model_clf.predict_proba(X)[:, 1]
        return probs

    # --------------------------------------------------
    # FEATURE IMPORTANCE (optional)
    # --------------------------------------------------

    def get_feature_importance(self):

        if self.horizon == "3m":
            return dict(zip(
                self.feature_columns,
                self.model_lgb.feature_importances_
            ))

        if self.horizon == "1m":
            return dict(zip(
                self.feature_columns,
                self.model.feature_importances_
            ))

        return None

    # --------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------

    def save_model(self, model_path):

        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        payload = {
            "horizon": self.horizon,
            "feature_columns": self.feature_columns
        }

        if self.horizon == "3m":
            payload["model_ridge"] = self.model_ridge
            payload["model_lgb"] = self.model_lgb
            payload["model_clf"] = self.model_clf

        elif self.horizon == "6m":
            payload["model"] = self.model
            payload["model_clf"] = self.model_clf

        else:
            payload["model"] = self.model

        joblib.dump(payload, model_path)

    # --------------------------------------------------
    # LOAD MODEL
    # --------------------------------------------------

    def load_model(self, model_path):

        payload = joblib.load(model_path)

        self.horizon = payload["horizon"]
        self.feature_columns = payload["feature_columns"]

        if self.horizon == "3m":
            self.model_ridge = payload["model_ridge"]
            self.model_lgb = payload["model_lgb"]
            self.model_clf = payload["model_clf"]

        elif self.horizon == "6m":
            self.model = payload["model"]
            self.model_clf = payload["model_clf"]

        else:
            self.model = payload["model"]

        return self