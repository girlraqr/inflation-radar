def gold_signal(real_inflation, interest_rate):
    """
    Gold signal based on real interest rates
    """

    # sicherstellen dass Zahlen verwendet werden
    real_inflation = float(real_inflation)
    interest_rate = float(interest_rate)

    real_rate = interest_rate - real_inflation

    if real_rate < -1:
        return "STRONG GOLD SIGNAL"

    elif real_rate < 0:
        return "GOLD POSITIVE"

    else:
        return "NEUTRAL"


def inflation_regime(real_inflation):
    """
    Inflation regime classification
    """

    real_inflation = float(real_inflation)

    if real_inflation > 7:
        return "HIGH INFLATION REGIME"

    elif real_inflation > 4:
        return "MODERATE INFLATION"

    else:
        return "LOW INFLATION"