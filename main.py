import sys
import argparse
from datetime import datetime, timezone

from fastapi import FastAPI

# Router
from api.routes.portfolio_routes import router as portfolio_router
from api.routes.auth.auth_routes import router as auth_router

# (Optional: weitere Router hier einbinden)
# from api.routes.signal_routes import router as signal_router


# =========================
# FASTAPI APP
# =========================

app = FastAPI(title="Inflation Radar API")
app.include_router(auth_router)
app.include_router(portfolio_router)
# app.include_router(signal_router)


# =========================
# CLI (optional behalten)
# =========================

def print_header():
    now = datetime.now(timezone.utc)

    print("\n")
    print("=" * 60)
    print(" REAL INFLATION RADAR")
    print("=" * 60)
    print(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)
    print("\n")


def run_cli():
    """
    Minimal CLI fallback (Pipeline wurde entfernt).
    Kann später wieder erweitert werden.
    """

    parser = argparse.ArgumentParser(
        description="Inflation Radar CLI (minimal mode)"
    )

    parser.add_argument(
        "--health",
        action="store_true",
        help="Check if system is running",
    )

    args = parser.parse_args()

    if args.health:
        print("OK — Inflation Radar running")
        return

    print_header()
    print("CLI pipeline currently disabled.")
    print("Use API instead: http://127.0.0.1:8000")


# =========================
# ENTRYPOINT
# =========================

def main():
    run_cli()


if __name__ == "__main__":
    main()