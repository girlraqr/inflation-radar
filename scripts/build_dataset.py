from models.ml.dataset_builder import DatasetBuilder

builder = DatasetBuilder()

df = builder.save_dataset()

print("Dataset created")
print(df.tail())