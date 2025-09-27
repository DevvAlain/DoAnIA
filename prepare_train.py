# prepare_train.py
import pandas as pd
import glob, argparse
from sklearn.model_selection import train_test_split
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("indir", help="directory with features_*.csv")
parser.add_argument("--outdir", default="datasets")
args = parser.parse_args()

files = glob.glob(f"{args.indir}/features_*.csv")
if not files:
    raise SystemExit("No features_*.csv found in " + args.indir)

dfs = [pd.read_csv(f) for f in files]
df = pd.concat(dfs, ignore_index=True)
print("Total rows (concat):", len(df))

if 'Label' not in df.columns:
    df['Label'] = 'normal'

feat_cols = ['value','payload_length','qos','retain_flag','dup_flag','msgid_present','iat_sec']
feat_cols = [c for c in feat_cols if c in df.columns]
df = df.dropna(subset=feat_cols)
X = df[feat_cols]
y = df['Label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)

outdir = Path(args.outdir)
outdir.mkdir(parents=True, exist_ok=True)
pd.concat([X_train, y_train], axis=1).to_csv(outdir / "train.csv", index=False)
pd.concat([X_test, y_test], axis=1).to_csv(outdir / "test.csv", index=False)
print("Saved train/test to", outdir)
