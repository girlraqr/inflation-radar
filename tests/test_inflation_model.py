from models.inflation.real_inflation import consumer_score
from models.inflation.real_inflation import asset_score
from models.inflation.real_inflation import monetary_score
from models.inflation.real_inflation import real_inflation


def test_consumer_score():

    result = consumer_score(3, 4, 5, 6)

    assert result == 4.5


def test_asset_score():

    result = asset_score(8, 6)

    assert result == 7


def test_monetary_score():

    result = monetary_score(6, 2)

    assert result == 4


def test_real_inflation():

    consumer = 4
    asset = 7
    monetary = 4

    result = real_inflation(consumer, asset, monetary)

    assert result > 0