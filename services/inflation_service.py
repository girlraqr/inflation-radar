from data.ingestion.collector import build_indicators
from models.inflation.real_inflation import (
    consumer_score,
    asset_score,
    monetary_score,
    real_inflation,
)
from models.inflation.nowcast import calculate_real_inflation_nowcast
from storage.history_loader import load_history


def get_inflation_data():
    indicators = build_indicators()

    consumer = consumer_score(
        indicators.get("cpi_yoy", 0),
        indicators.get("core_cpi_yoy", 0),
        indicators.get("ppi_yoy", 0),
        indicators.get("oil_price_yoy", 0),
    )

    asset = asset_score(
        indicators.get("sp500_yoy", 0),
        indicators.get("sp500_mom", 0),
    )

    monetary = monetary_score(
        indicators.get("m2_yoy", 0),
        indicators.get("fed_rate_yoy", 0),
    )

    real = real_inflation(consumer, asset, monetary)

    nowcast_data = calculate_real_inflation_nowcast(indicators)

    if isinstance(nowcast_data, dict):
        nowcast_value = float(nowcast_data.get("real_inflation_estimate", 0))
    else:
        nowcast_value = float(nowcast_data)

    history = load_history()

    return {
        "consumer_score": float(consumer),
        "asset_score": float(asset),
        "monetary_score": float(monetary),
        "real_inflation": float(real),
        "nowcast": nowcast_data,
        "nowcast_value": nowcast_value,
        "history": history,
    }