import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

print("Chargement dataset...")

df = pd.read_csv("dataset_clean_final.csv")

# ===== INPUT =====
X = df["Customer_Issue"]

# ===== TARGETS =====
y_difficulty = df["Difficulty"]
y_priority = df["Priority"]
y_auto = df["Auto_Resolve"]

def train_model(target, name):

    print(f"Training model: {name}")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer()),
        ("clf", RandomForestClassifier(n_estimators=100))
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, target, test_size=0.2, random_state=42
    )

    pipeline.fit(X_train, y_train)

    score = pipeline.score(X_test, y_test)
    print(f"{name} accuracy:", score)

    joblib.dump(pipeline, f"{name}_model.pkl")

train_model(y_difficulty, "difficulty")
train_model(y_priority, "priority")
train_model(y_auto, "auto_resolve")

print("ML models saved!")