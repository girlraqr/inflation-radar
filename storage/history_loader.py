import json
from pathlib import Path
from datetime import datetime


SNAPSHOT_DIR = Path("storage/snapshots")
SNAPSHOT_FILE = SNAPSHOT_DIR / "inflation_history.json"


def ensure_history_file():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    if not SNAPSHOT_FILE.exists():
        SNAPSHOT_FILE.write_text("[]", encoding="utf-8")


def load_history():
    ensure_history_file()

    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_history(history):
    ensure_history_file()

    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def append_snapshot(snapshot):
    history = load_history()

    snapshot_date = snapshot.get("date")
    if snapshot_date:
        history = [item for item in history if item.get("date") != snapshot_date]

    history.append(snapshot)
    history = sorted(history, key=lambda x: x.get("date", ""))

    save_history(history)


def create_snapshot(real_inflation, nowcast, regime, gold_signal):
    return {
        "date": datetime.utcnow().date().isoformat(),
        "real_inflation": float(real_inflation),
        "nowcast": float(nowcast),
        "regime": regime,
        "gold_signal": gold_signal,
    }