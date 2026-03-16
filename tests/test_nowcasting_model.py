from models.inflation.nowcast import (
    calculate_consumer_inflation_score,
    calculate_monetary_pressure_score,
    calculate_asset_inflation_score,
    calculate_real_inflation_nowcast,
    calculate_hidden_inflation,
)


def test_consumer_inflation_score():
    indicators = {
        "cpi_yoy": 2.5,
        "core_cpi_yoy": 3.0,
        "food_yoy": 5.0,
        "energy_yoy": 6.0,
        "rent_yoy": 4.0,
        "transport_yoy": 3.0,
        "medical_yoy": 2.0,
        "ppi_yoy": 1.5,
    }

    score = calculate_consumer_inflation_score(indicators)

    assert isinstance(score, float)
    assert score > 0


def test_monetary_pressure_score():
    indicators = {
        "m2_yoy": 6.0,
        "m3_yoy": 5.5,
        "bank_credit_yoy": 4.0,
        "central_bank_balance_yoy": 3.0,
        "policy_rate": 2.0,
        "real_rate": -1.5,
        "yield_curve_slope": 1.0,
        "loan_growth_yoy": 3.5,
    }

    score = calculate_monetary_pressure_score(indicators)

    assert isinstance(score, float)
    assert score > 0


def test_asset_inflation_score():
    indicators = {
        "gold_yoy": 12.0,
        "silver_yoy": 10.0,
        "commodity_index_yoy": 8.0,
        "oil_yoy": 6.0,
        "sp500_yoy": 9.0,
        "global_equities_yoy": 7.0,
        "real_estate_yoy": 5.0,
        "construction_costs_yoy": 4.0,
        "bitcoin_yoy": 15.0,
        "em_equities_yoy": 6.0,
    }

    score = calculate_asset_inflation_score(indicators)

    assert isinstance(score, float)
    assert score > 0


def test_hidden_inflation():
    hidden = calculate_hidden_inflation(5.5, 2.5)

    assert hidden == 3.0


def test_real_inflation_nowcast():
    indicators = {
        "cpi_yoy": 2.5,
        "core_cpi_yoy": 3.0,
        "food_yoy": 5.0,
        "energy_yoy": 6.0,
        "rent_yoy": 4.0,
        "transport_yoy": 3.0,
        "medical_yoy": 2.0,
        "ppi_yoy": 1.5,
        "m2_yoy": 6.0,
        "m3_yoy": 5.0,
        "bank_credit_yoy": 4.0,
        "central_bank_balance_yoy": 3.0,
        "policy_rate": 2.0,
        "real_rate": -1.0,
        "yield_curve_slope": 1.0,
        "loan_growth_yoy": 3.0,
        "gold_yoy": 10.0,
        "silver_yoy": 8.0,
        "commodity_index_yoy": 7.0,
        "oil_yoy": 6.0,
        "sp500_yoy": 9.0,
        "global_equities_yoy": 7.0,
        "real_estate_yoy": 5.0,
        "construction_costs_yoy": 4.0,
        "bitcoin_yoy": 12.0,
        "em_equities_yoy": 6.0,
    }

    result = calculate_real_inflation_nowcast(indicators)

    assert isinstance(result, dict)
    assert "consumer_score" in result
    assert "monetary_score" in result
    assert "asset_score" in result
    assert "official_cpi" in result
    assert "real_inflation_estimate" in result
    assert "hidden_inflation" in result
    assert result["real_inflation_estimate"] > 0