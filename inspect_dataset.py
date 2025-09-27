# inspect_dataset.py
import pandas as pd
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("infile", help="CSV file to inspect")
args = parser.parse_args()

p = Path(args.infile)
df = pd.read_csv(p)
print(f"File: {p}, rows: {len(df)}, columns: {list(df.columns)}\n")
print("Head:")
print(df.head(5).to_string(index=False))
print("\nDtypes:")
print(df.dtypes)
# useful uniques
for col in ["client_id","topic","Label","protocol","packet_type"]:
    if col in df.columns:
        print(f"\nUnique values for {col} (up to 10):")
        print(df[col].dropna().unique()[:10])
