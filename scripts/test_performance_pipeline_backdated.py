from services.portfolio_engine_service import PortfolioEngineService
from services.signal_ranking_service import SignalRankingService
from live.services.allocation_snapshot_service import AllocationSnapshotService


def run_test(user_id: int = 1, snapshot_date: str = "2025-12-31"):
    print("=== TEST: PERFORMANCE PIPELINE BACKDATED ===")
    print(f"snapshot_date={snapshot_date}")

    ranking_service = SignalRankingService()
    portfolio_service = PortfolioEngineService()
    snapshot_service = AllocationSnapshotService()

    print("-> fetching ranked signals...")
    signals = ranking_service.get_ranked_signals(user_id=user_id, premium=True)
    print(f"signals: {len(signals) if signals else 0}")

    print("-> building portfolio...")
    portfolio = portfolio_service.build_portfolio(
        user_id=user_id,
        ranked_signals=signals or [],
        persist_snapshot=False,
    )

    print("-> persisting snapshot + triggering performance...")
    result = snapshot_service.persist_snapshot(
        user_id=user_id,
        portfolio=portfolio,
        snapshot_date=snapshot_date,
    )

    print("RESULT:")
    print(result)


if __name__ == "__main__":
    run_test(user_id=1, snapshot_date="2025-10-01")
    run_test(user_id=1, snapshot_date="2025-11-01")
    run_test(user_id=1, snapshot_date="2025-12-01")
    run_test(user_id=1, snapshot_date="2026-01-01")
    run_test(user_id=1, snapshot_date="2026-02-01")
    run_test(user_id=1, snapshot_date="2026-03-01")
    run_test()