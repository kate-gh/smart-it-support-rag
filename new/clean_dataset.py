import pandas as pd

df = pd.read_csv("data/chatbot_rag_final.csv")

# Étape 1 : Garder seulement les bonnes sources
df_clean = df[df["source"].isin(["synthetic_groq", "kaggle_it_helpdesk"])]
print(f"Après filtrage source : {len(df_clean)} lignes")

# Étape 2 : Fix — regex=False + patterns simples
bad_patterns = [
    "Dear [Name]",
    "[Name]",
    "\\\"name\\\"",
    "SendGrid",
    "medical data",
    "investment analysis",
    "SaaS project",
    "healthcare"
]

# ✅ regex=False → recherche littérale, pas regex
mask = ~df_clean["answer"].apply(
    lambda x: any(p.lower() in x.lower() for p in bad_patterns)
)
df_clean = df_clean[mask]
print(f"Après suppression placeholders : {len(df_clean)} lignes")

# Étape 3 : Supprimer doublons
df_clean = df_clean.drop_duplicates(subset=["answer"])
print(f"Après déduplication : {len(df_clean)} lignes")

# Étape 4 : Aligner catégories
cat_mapping = {
    "IT Support - General" : "IT Support",
    "Technical Support"    : "IT Support",
    "Product Support"      : "Software & Applications",
    "Email & Communication": "Software & Applications",
}
df_clean["category"] = df_clean["category"].replace(cat_mapping)

df_clean.to_csv("data/chatbot_rag_clean.csv", index=False)
print(f"✅ Dataset propre sauvegardé : {len(df_clean)} lignes")

# Vérification rapide
print("\n=== APERÇU ===")
print(df_clean["category"].value_counts())
print(df_clean["source"].value_counts())