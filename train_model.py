# train_model.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--train", default="datasets/train.csv")
parser.add_argument("--test", default="datasets/test.csv")
args = parser.parse_args()

train = pd.read_csv(args.train)
test = pd.read_csv(args.test)

feat_cols = [c for c in train.columns if c not in ('Label','client_id','topic','ts')]
X_train = train[feat_cols]
y_train = train['Label']
X_test = test[feat_cols]
y_test = test['Label']

clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
clf.fit(X_train, y_train)
pred = clf.predict(X_test)
print(classification_report(y_test, pred))
joblib.dump(clf, Path(args.train).parent / 'model_rf.joblib')
print("Saved model_rf.joblib")
