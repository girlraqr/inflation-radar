import json
import os

CONFIG_PATH = "storage/training_config.json"


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"mode": "manual"}

    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def set_mode(mode: str):
    config = load_config()
    config["mode"] = mode
    save_config(config)
    return config


def get_mode():
    return load_config().get("mode", "manual")