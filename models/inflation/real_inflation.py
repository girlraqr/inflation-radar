def consumer_score(cpi, food, energy, rent):
    """
    Consumer inflation score
    """
    return (cpi + food + energy + rent) / 4


def asset_score(gold, stocks):
    """
    Asset inflation score
    """
    return (gold + stocks) / 2


def monetary_score(m2_growth, interest_rate):
    """
    Monetary inflation score
    """
    return m2_growth - interest_rate


def real_inflation(consumer, asset, monetary):
    """
    Combined inflation estimate
    """

    consumer_weight = 0.5
    asset_weight = 0.2
    monetary_weight = 0.3

    return (
        consumer_weight * consumer +
        asset_weight * asset +
        monetary_weight * monetary
    )