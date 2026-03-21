import json
import os


DEFAULT_PATH = "storage/model_metrics.json"


def save_model_metrics(metrics: dict, path: str = DEFAULT_PATH):
    """
    Speichert Model Metrics (MAE, RMSE, Skill etc.)
    """

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"[INFO] Metrics gespeichert: {path}")


def load_model_metrics(path: str = DEFAULT_PATH) -> dict:
    """
    Lädt gespeicherte Metrics
    """

    if not os.path.exists(path):
        print("[WARNUNG] Keine Metrics-Datei gefunden")
        return {}

    with open(path, "r") as f:
        return json.load(f)