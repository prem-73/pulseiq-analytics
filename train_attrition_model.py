import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = Path("data/external/emp_attrition.csv")
OUTPUT_DIR = Path("models")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)
df = df.dropna(subset=["Attrition"]).copy()
df["Attrition"] = df["Attrition"].astype(str).str.strip().str.lower()
df = df[df["Attrition"].isin(["yes", "no"])].copy()

y = df["Attrition"].map({"no": 0, "yes": 1})

X = df.drop(columns=["Attrition", "EmployeeNumber", "EmployeeCount", "Over18", "StandardHours"], errors="ignore")
X = X.loc[:, X.nunique(dropna=False) > 1]

numeric_features = X.select_dtypes(include=["number"]).columns.tolist()
categorical_features = X.select_dtypes(exclude=["number"]).columns.tolist()

numeric_pipeline = Pipeline([
("imputer", SimpleImputer(strategy="median")),
("scaler", StandardScaler())
])

categorical_pipeline = Pipeline([
("imputer", SimpleImputer(strategy="most_frequent")),
("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer([
("numeric", numeric_pipeline, numeric_features),
("categorical", categorical_pipeline, categorical_features)
])

model = Pipeline([
("preprocessor", preprocessor),
("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42))
])

X_train, X_test, y_train, y_test = train_test_split(
X, y, test_size=0.25, random_state=42, stratify=y
)

model.fit(X_train, y_train)
predictions = model.predict(X_test)
probabilities = model.predict_proba(X_test)[:, 1]

metrics = {
"dataset": "External IBM HR attrition dataset",
"dataset_rows": int(len(df)),
"training_rows": int(len(X_train)),
"test_rows": int(len(X_test)),
"positive_attrition_records": int(y.sum()),
"accuracy": float(accuracy_score(y_test, predictions)),
"precision": float(precision_score(y_test, predictions, zero_division=0)),
"recall": float(recall_score(y_test, predictions, zero_division=0)),
"f1_score": float(f1_score(y_test, predictions, zero_division=0)),
"roc_auc": float(roc_auc_score(y_test, probabilities)),
"threshold": 0.5,
"random_state": 42,
"limitations": [
"External dataset, not the internship company's actual workforce.",
"No confirmed exit dates or voluntary/involuntary exit types.",
"Test results do not establish performance on a new company.",
"Predicted probabilities are estimates, not certainties."
]
}

joblib.dump(model, OUTPUT_DIR / "attrition_model.joblib")

metrics_path = OUTPUT_DIR / "attrition_model_metrics.json"
metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

print("=== ATTRITION MODEL VALIDATION ===")
print(json.dumps(metrics, indent=2))
print("\n=== CLASSIFICATION REPORT ===")
print(classification_report(y_test, predictions, labels=[0, 1], target_names=["No Attrition", "Attrition"], zero_division=0))
print("=== CONFUSION MATRIX ===")
print(confusion_matrix(y_test, predictions, labels=[0, 1]))
print("\nSaved model:", OUTPUT_DIR / "attrition_model.joblib")
print("Saved metrics:", OUTPUT_DIR / "attrition_model_metrics.json")
print("\nNOTE: This model uses external data, not company employee records.")
