from __future__ import annotations

from datetime import datetime
from dateutil.relativedelta import relativedelta

from services.signal_ranking_service import SignalRankingService
from services.portfolio_engine_service import PortfolioEngineService
from live.services.allocation_snapshot_service import AllocationSnapshotService


def run_backfill(
    user_id: int = 1,
    start_date: str = "2024-01-01",
    end_date: str = "2025-08-01",
):
    print("=== BUILD HISTORICAL SNAPSHOTS (SIGNAL-DRIVEN) ===")
    print(f"user_id={user_id}")
    print(f"range={start_date} -> {end_date}")

    ranking_service = SignalRankingService()
    portfolio_service = PortfolioEngineService()
    snapshot_service = AllocationSnapshotService()

    current = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    count = 0

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")

        print(f"\n--- {date_str} ---")

        # ---------------------------------------------------
        # SIGNALS (HISTORISCH!)
        # ---------------------------------------------------

        signals = ranking_service.get_ranked_signals_for_date(
            user_id=user_id,
            premium=True,
            as_of_date=date_str,  # 🔥 WICHTIG!
        )

        print(f"signals: {len(signals) if signals else 0}")

        if signals:
            print("top signals:", [s.get("symbol") for s in signals[:3]])

        # ---------------------------------------------------
        # PORTFOLIO
        # ---------------------------------------------------

        portfolio = portfolio_service.build_portfolio(
            user_id=user_id,
            ranked_signals=signals or [],
            persist_snapshot=False,
        )

        # ---------------------------------------------------
        # 🔥 DEBUG (HIER IST DER WICHTIGE TEIL)
        # ---------------------------------------------------

        print("\n--- DEBUG WEIGHTS ---")
        print(f"date: {date_str}")

        positions = portfolio.get("positions", [])

        if not positions:
            print("⚠️ NO POSITIONS!")
        else:
            for p in positions:
                print(
                    f"{p.get('symbol')} → {round(float(p.get('target_weight', 0)), 4)}"
                )

        # ---------------------------------------------------
        # SNAPSHOT
        # ---------------------------------------------------

        snapshot_service.persist_snapshot(
            user_id=user_id,
            portfolio=portfolio,
            snapshot_date=date_str,
        )

        count += 1
        current += relativedelta(months=1)

    print("\n=== DONE ===")
    print(f"snapshots_created={count}")


if __name__ == "__main__":
    run_backfill()