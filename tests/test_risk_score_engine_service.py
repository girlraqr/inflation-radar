from services.risk_score_engine_service import RiskScoreEngineService


def test_calculate_scores_returns_valid_range():
    service = RiskScoreEngineService()

    ranked_signals = [
        {"signal": "disinflation", "conviction": 0.82, "score": 85},
        {"signal": "disinflation", "conviction": 0.75, "score": 72},
        {"signal": "neutral", "conviction": 0.65, "score": 55},
    ]

    portfolio = {
        "positions": [
            {"symbol": "SPY", "target_weight": 0.50},
            {"symbol": "IEF", "target_weight": 0.25},
            {"symbol": "GLD", "target_weight": 0.25},
        ]
    }

    result = service.calculate_scores(
        ranked_signals=ranked_signals,
        portfolio=portfolio,
        current_drawdown=-0.06,
    )

    assert 0.0 <= result["confidence_score"] <= 1.0
    assert 0.0 <= result["risk_score"] <= 1.0
    assert result["components"]["signal_count"] == 3


def test_concentrated_portfolio_has_higher_risk():
    service = RiskScoreEngineService()

    signals = [
        {"signal": "neutral", "conviction": 0.80},
        {"signal": "neutral", "conviction": 0.78},
        {"signal": "neutral", "conviction": 0.76},
    ]

    diversified = {
        "positions": [
            {"symbol": "SPY", "target_weight": 0.34},
            {"symbol": "IEF", "target_weight": 0.33},
            {"symbol": "GLD", "target_weight": 0.33},
        ]
    }

    concentrated = {
        "positions": [
            {"symbol": "SPY", "target_weight": 0.80},
            {"symbol": "IEF", "target_weight": 0.10},
            {"symbol": "GLD", "target_weight": 0.10},
        ]
    }

    diversified_result = service.calculate_scores(
        ranked_signals=signals,
        portfolio=diversified,
        current_drawdown=0.0,
    )

    concentrated_result = service.calculate_scores(
        ranked_signals=signals,
        portfolio=concentrated,
        current_drawdown=0.0,
    )

    assert concentrated_result["risk_score"] > diversified_result["risk_score"]