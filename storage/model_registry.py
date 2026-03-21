import json
import os
from datetime import datetime

REGISTRY_PATH = "storage/model_registry.json"


def _default_registry():
    return {
        "models": {},
        "updated_at": None
    }


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return _default_registry()

    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return _default_registry()

        if "models" not in data:
            data["models"] = {}

        if "updated_at" not in data:
            data["updated_at"] = None

        return data

    except (json.JSONDecodeError, OSError):
        return _default_registry()


def save_registry(registry):
    registry["updated_at"] = datetime.utcnow().isoformat()

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def get_model_entry(horizon: str):
    registry = load_registry()
    return registry["models"].get(horizon)


def upsert_model_entry(
    horizon: str,
    target_column: str,
    model_path: str,
    metrics: dict,
    status: str,
    training_mode: str,
    notes: str = ""
):
    registry = load_registry()

    registry["models"][horizon] = {
        "target_column": target_column,
        "model_path": model_path,
        "metrics": {
            "rmse": float(metrics["rmse"]),
            "r2": float(metrics["r2"])
        },
        "status": status,
        "training_mode": training_mode,
        "notes": notes,
        "updated_at": datetime.utcnow().isoformat()
    }

    save_registry(registry)
    return registry["models"][horizon]