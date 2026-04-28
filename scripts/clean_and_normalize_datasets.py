import pandas as pd

DATASET_1 = "data/customer_support_tickets.csv"
DATASET_2 = "data/IT-helpdesk-synthetic-tickets.csv"
DATASET_3 = "data/ticket_classification_IT_EN.xlsx"
OUTPUT_PATH = "data/final_clean_dataset.csv"

def clean_text(text):
    if pd.isna(text):
        return ""
    
    text = str(text)
    
    # supprimer espaces
    text = " ".join(text.split())
    
    # supprimer caractères spéciaux simples
    text = text.replace("\n", " ")
    
    return text.strip()

print("Chargement des datasets...")
df1 = pd.read_csv(DATASET_1)
df2 = pd.read_csv(DATASET_2)
df3 = pd.read_excel(DATASET_3)

print("Traitement de dataset 1")
df1.columns = df1.columns.str.lower()
df1["question"] = df1["subject"].fillna("") + " " + df1["body"].fillna("")

df1["answer"] = df1["answer"]

df1["category"] = df1["queue"]

df1["priority"] = df1["priority"]

df1["auto_resolution"] = True

# colonnes finales
df1 = df1[["question", "answer", "priority", "category", "auto_resolution"]]

print("Traitement de dataset 2")

df2["question"] = df2["subject"].fillna("") + " " + df2["description"].fillna("")
df2["category"] = df2["category"]
df2["answer"] = ""

df2["auto_resolution"] = False

df2 = df2[["question", "answer", "priority", "category", "auto_resolution"]]    

print("Traitement de dataset 3")

df3.columns = df3.columns.str.lower()

df3["question"] = df3["text"]

df3["answer"] = ""

# priorité par défaut
df3["priority"] = "medium"

df3["category"] = df3["category"] + " - " + df3["subcategory"]

# auto résolution
df3["auto_resolution"] = False

df3 = df3[["question", "answer", "priority", "category", "auto_resolution"]]

# merge datasets

print("Fusion des datasets...")

df = pd.concat([df1, df2, df3], ignore_index=True)

print("Nettoyage global...")

# supprimer nulls
df = df.dropna(subset=["question"])

# supprimer vides
df = df[df["question"].str.strip() != ""]

# nettoyage texte
df["question"] = df["question"].apply(clean_text)
df["answer"] = df["answer"].apply(clean_text)

# supprimer duplication
df = df.drop_duplicates(subset=["question"])

# FILTRAGE LANGUE (ENGLISH ONLY)

def is_english(text):
    # simple heuristic
    return all(ord(c) < 128 for c in text)

df = df[df["question"].apply(is_english)]

df = df.reset_index(drop=True)

df.to_csv(OUTPUT_PATH, index=False)
print("\nDataset final créé :", OUTPUT_PATH)
print("Nombre final :", len(df))