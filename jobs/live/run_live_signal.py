from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live.services.live_signal_service import LiveSignalService  # noqa: E402


def main() -> None:
    service = LiveSignalService()
    payload = service.build_and_publish_live_signal()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()