print("🚀 NEW VERSION RUNNING 🚀")

from services.portfolio_engine_service import PortfolioEngineService
from services.signal_ranking_service import SignalRankingService
from live.services.allocation_snapshot_service import AllocationSnapshotService
from services.performance_engine_service import PerformanceEngineService


def run_test(user_id: int = 1):
    print("=== TEST: PERFORMANCE PIPELINE ===")

    ranking_service = SignalRankingService()
    portfolio_service = PortfolioEngineService()
    snapshot_service = AllocationSnapshotService()
    performance_service = PerformanceEngineService()

    print("-> fetching ranked signals...")
    signals = ranking_service.get_ranked_signals(user_id=user_id, premium=True)
    print(f"signals: {len(signals) if signals else 0}")

    print("-> building portfolio...")
    portfolio = portfolio_service.build_portfolio(
        user_id=user_id,
        ranked_signals=signals or [],
        persist_snapshot=False,
    )

    print("-> persisting snapshot...")
    snapshot_service.persist_snapshot(
        user_id=user_id,
        portfolio=portfolio,
    )

    print("-> loading performance...")
    result = performance_service.build_performance(user_id=user_id)

    print("\n=== PERFORMANCE RESULT ===")
    print(f"History points: {len(result.history)}")

    print("\n--- HISTORY ---")
    for row in result.history:
        print(row)

    print("\n--- SUMMARY ---")
    print(result.summary)


if __name__ == "__main__":
    run_test()