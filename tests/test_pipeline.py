from models.inflation.real_inflation import consumer_score
from models.inflation.real_inflation import asset_score
from models.inflation.real_inflation import monetary_score
from models.inflation.real_inflation import real_inflation


def test_full_pipeline():

    consumer = consumer_score(3, 5, 6, 4)

    asset = asset_score(8, 7)

    monetary = monetary_score(6, 3)

    real = real_inflation(consumer, asset, monetary)

    assert real > 0