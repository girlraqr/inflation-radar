import pandas as pd
from models.ml.feature_engineering import FeatureEngineering

print("Feature Engineering gestartet")

df = pd.read_csv(
    "storage/cache/ml_dataset.csv",
    index_col="date",
    parse_dates=True
)
print(type(df.index))
print(df.index[:5])
print("Dataset geladen")
print(df.tail())

features = FeatureEngineering(df)
feature_df = features.create_features()

feature_df.to_csv("storage/cache/ml_features.csv")

print("Feature Dataset erstellt")
print(feature_df.tail())
print("Shape:", feature_df.shape)