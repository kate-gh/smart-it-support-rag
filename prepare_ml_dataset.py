import pandas as pd
import numpy as np


print("Chargement du dataset...")
df = pd.read_csv("data/customer_support_tickets.csv")

print(f"Colonnes disponibles : {df.columns.tolist()}")
print(f"Nombre de lignes     : {len(df)}")
print(f"Valeurs 'priority'   : {df['priority'].value_counts().to_dict()}")
print(f"Valeurs 'type'       : {df['type'].value_counts().to_dict()}")
print(f"Valeurs 'language'   : {df['language'].value_counts().to_dict()}")

#SEULEMENT FR / EN
df = df[df["language"].isin(["fr", "en", "FR", "EN"])]
print(f"\nAprès filtrage FR/EN : {len(df)} lignes")

#  CONSTRUIRE LA COLONNE Customer_Issue

# On fusionne subject + body pour avoir un texte riche
def build_issue(row):
    subject = str(row.get("subject", "")).strip()
    body    = str(row.get("body",    "")).strip()
    if body and body != "nan":
        return f"{subject} {body[:300]}"  # limiter le body à 300 chars
    return subject

df["Customer_Issue"] = df.apply(build_issue, axis=1)

#  COLONNE : Priority (normaliser)

# Standardiser les valeurs
priority_map = {
    "high":     "High",
    "medium":   "Medium",
    "low":      "Low",
    "critical": "Critical",
    "High":     "High",
    "Medium":   "Medium",
    "Low":      "Low",
    "Critical": "Critical",
}
df["Priority"] = df["priority"].map(priority_map).fillna("Medium")

print(f"\nDistribution Priority :\n{df['Priority'].value_counts()}")

#  COLONNE : Difficulty (dérivée de priority + type)

# Règle métier :
#   Incident + High/Critical  → Hard
#   Incident + Medium         → Medium
#   Request / Problem + Low   → Easy
#   Autres                    → Medium

def derive_difficulty(row):
    t = str(row.get("type", "")).lower()
    p = str(row.get("priority", "")).lower()

    if t == "incident" and p in ["high", "critical"]:
        return "Hard"
    elif t == "incident" and p == "medium":
        return "Medium"
    elif t in ["request", "problem"] and p == "low":
        return "Easy"
    elif p in ["high", "critical"]:
        return "Hard"
    elif p == "low":
        return "Easy"
    else:
        return "Medium"

df["Difficulty"] = df.apply(derive_difficulty, axis=1)

print(f"\nDistribution Difficulty :\n{df['Difficulty'].value_counts()}")

#  COLONNE : Auto_Resolve (dérivée de priority + type)

# Règle métier :
#   Low priority + Request     → Yes (peut être résolu automatiquement)
#   High/Critical + Incident   → No  (nécessite intervention humaine)
#   Autres                     → Yes ou No selon probabilité

def derive_auto_resolve(row):
    t = str(row.get("type", "")).lower()
    p = str(row.get("priority", "")).lower()

    if p in ["high", "critical"] and t == "incident":
        return "No"
    elif p == "low":
        return "Yes"
    elif t == "request" and p == "medium":
        return "Yes"
    elif t == "incident" and p == "medium":
        return "No"
    else:
        return "Yes"

df["Auto_Resolve"] = df.apply(derive_auto_resolve, axis=1)

print(f"\nDistribution Auto_Resolve :\n{df['Auto_Resolve'].value_counts()}")

#  NETTOYAGE FINAL

df = df.dropna(subset=["Customer_Issue"])
df = df[df["Customer_Issue"].str.len() > 20]

# Garder seulement les colonnes jjjjjjjjjjjj
df_final = df[["Customer_Issue", "Difficulty", "Priority", "Auto_Resolve"]].copy()
df_final = df_final.reset_index(drop=True)

print(f"\nDataset final : {len(df_final)} lignes")
print(df_final.head(5))

#  SAUVEGARDE

df_final.to_csv("dataset_clean_final.csv", index=False, encoding="utf-8")
print(f"\n dataset_clean_final.csv sauvegardé avec {len(df_final)} lignes")
print("Tu peux maintenant relancer : python train_ml_models.py")