from statistics import mean


def clamp(value, min_value=-20.0, max_value=20.0):
    """
    Begrenze extreme Ausreißer, damit das Modell stabil bleibt.
    """
    return max(min_value, min(max_value, value))


def safe_mean(values, default=0.0):
    """
    Mittelwert nur über numerische Werte.
    """
    numeric_values = [
        float(v) for v in values
        if isinstance(v, (int, float))
    ]

    if not numeric_values:
        return default

    return mean(numeric_values)


def yoy_change(current, previous):
    """
    Year-over-year Veränderung in Prozent.
    Beispiel:
    current=110, previous=100 -> 10.0
    """
    if previous in (0, None):
        return 0.0

    return ((current - previous) / previous) * 100.0


def normalize_level(value, neutral=0.0, scale=1.0):
    """
    Normiert Werte grob auf eine vergleichbare Skala.
    Beispiel:
    value=6, neutral=2, scale=2 -> 2.0
    """
    if scale == 0:
        return 0.0

    return (value - neutral) / scale


def calculate_consumer_inflation_score(indicators):
    """
    Berechnet den lebensnahen Inflationsscore.

    Erwartete Keys, falls vorhanden:
    - cpi_yoy
    - core_cpi_yoy
    - food_yoy
    - energy_yoy
    - rent_yoy
    - transport_yoy
    - medical_yoy
    - ppi_yoy
    """

    weights = {
        "cpi_yoy": 0.18,
        "core_cpi_yoy": 0.12,
        "food_yoy": 0.18,
        "energy_yoy": 0.18,
        "rent_yoy": 0.18,
        "transport_yoy": 0.08,
        "medical_yoy": 0.04,
        "ppi_yoy": 0.04,
    }

    weighted_values = []
    total_weight = 0.0

    for key, weight in weights.items():
        if key in indicators and isinstance(indicators[key], (int, float)):
            weighted_values.append(clamp(indicators[key]) * weight)
            total_weight += weight

    if total_weight == 0:
        return 0.0

    return sum(weighted_values) / total_weight


def calculate_monetary_pressure_score(indicators):
    """
    Berechnet monetären Inflationsdruck.

    Erwartete Keys, falls vorhanden:
    - m2_yoy
    - m3_yoy
    - bank_credit_yoy
    - central_bank_balance_yoy
    - policy_rate
    - real_rate
    - yield_curve_slope
    - loan_growth_yoy

    Interpretation:
    - höhere Geldmengen-/Kreditdynamik -> inflationär
    - stark negative Realzinsen -> inflationär
    """

    positive_pressure = []
    negative_pressure = []

    if "m2_yoy" in indicators:
        positive_pressure.append(clamp(indicators["m2_yoy"]))

    if "m3_yoy" in indicators:
        positive_pressure.append(clamp(indicators["m3_yoy"]))

    if "bank_credit_yoy" in indicators:
        positive_pressure.append(clamp(indicators["bank_credit_yoy"]))

    if "central_bank_balance_yoy" in indicators:
        positive_pressure.append(clamp(indicators["central_bank_balance_yoy"]))

    if "loan_growth_yoy" in indicators:
        positive_pressure.append(clamp(indicators["loan_growth_yoy"]))

    if "real_rate" in indicators:
        # Negative Realzinsen = inflationär
        negative_pressure.append(clamp(-indicators["real_rate"]))

    if "yield_curve_slope" in indicators:
        # leichte positive Zusatzinformation, aber gering gewichtet
        positive_pressure.append(clamp(indicators["yield_curve_slope"] * 0.5))

    if "policy_rate" in indicators:
        # hohe Nominalzinsen wirken etwas bremsend
        negative_pressure.append(clamp(indicators["policy_rate"] * 0.3))

    pos = safe_mean(positive_pressure, default=0.0)
    neg = safe_mean(negative_pressure, default=0.0)

    score = (0.7 * pos) + (0.3 * neg)

    return clamp(score, -20.0, 20.0)


def calculate_asset_inflation_score(indicators):
    """
    Misst, ob Liquidität in Assets läuft.

    Erwartete Keys, falls vorhanden:
    - gold_yoy
    - silver_yoy
    - commodity_index_yoy
    - oil_yoy
    - sp500_yoy
    - global_equities_yoy
    - real_estate_yoy
    - construction_costs_yoy
    - bitcoin_yoy
    - em_equities_yoy
    """

    weights = {
        "gold_yoy": 0.20,
        "silver_yoy": 0.08,
        "commodity_index_yoy": 0.15,
        "oil_yoy": 0.10,
        "sp500_yoy": 0.10,
        "global_equities_yoy": 0.07,
        "real_estate_yoy": 0.15,
        "construction_costs_yoy": 0.05,
        "bitcoin_yoy": 0.03,
        "em_equities_yoy": 0.07,
    }

    weighted_values = []
    total_weight = 0.0

    for key, weight in weights.items():
        if key in indicators and isinstance(indicators[key], (int, float)):
            weighted_values.append(clamp(indicators[key]) * weight)
            total_weight += weight

    if total_weight == 0:
        return 0.0

    return sum(weighted_values) / total_weight


def calculate_hidden_inflation(real_inflation_estimate, official_cpi):
    """
    Differenz zwischen Modell und offizieller Inflation.
    """
    return real_inflation_estimate - official_cpi


def calculate_real_inflation_nowcast(indicators):
    """
    Hauptfunktion für die Nowcast-Schätzung.

    Erwartet ein Dictionary mit möglichst vielen vorbereiteten Kennzahlen.
    Rückgabe:
    {
        "consumer_score": ...,
        "monetary_score": ...,
        "asset_score": ...,
        "official_cpi": ...,
        "real_inflation_estimate": ...,
        "hidden_inflation": ...
    }
    """

    consumer_score = calculate_consumer_inflation_score(indicators)
    monetary_score = calculate_monetary_pressure_score(indicators)
    asset_score = calculate_asset_inflation_score(indicators)

    official_cpi = float(indicators.get("cpi_yoy", 0.0))

    real_inflation_estimate = (
        0.50 * consumer_score +
        0.30 * monetary_score +
        0.20 * asset_score
    )

    hidden_inflation = calculate_hidden_inflation(
        real_inflation_estimate=real_inflation_estimate,
        official_cpi=official_cpi
    )

    return {
        "consumer_score": round(consumer_score, 2),
        "monetary_score": round(monetary_score, 2),
        "asset_score": round(asset_score, 2),
        "official_cpi": round(official_cpi, 2),
        "real_inflation_estimate": round(real_inflation_estimate, 2),
        "hidden_inflation": round(hidden_inflation, 2),
    }