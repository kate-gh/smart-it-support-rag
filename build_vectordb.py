import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import uuid
import re

# ---------- CONFIGURATION ----------
DATASET_PATH = "data/customer_support_tickets.csv"  
CHROMA_PATH  = "./vector_db"
COLLECTION_NAME = "it_support_knowledge"
BATCH_SIZE = 100  # insertion par batch pour éviter les erreurs mémoire

print("Chargement du dataset...")

df = pd.read_csv(DATASET_PATH)

# ---------- EXPLORATION INITIALE ----------
# Affiche les colonnes disponibles pour vérifier la structure du fichier
print("Colonnes disponibles :", df.columns.tolist())
print("Nombre de lignes :", len(df))
print(df.head(3))

# ---------- NETTOYAGE ----------
# On garde uniquement les lignes qui ont un problème ET une solution
# Les noms de colonnes exacts peuvent varier selon la version du dataset —
# adapte-les si nécessaire après avoir vu l'output ci-dessus

# Colonnes typiques du dataset Tobi Bueck multilingue :
# 'subject' ou 'ticket_subject' → description du problème
# 'body' ou 'ticket_body'       → détail du problème
# 'answer' ou 'response'        → solution de l'agent

# ⚠️ Adapter ces noms si les colonnes affichées sont différentes
COL_PROBLEM  = "subject"   # colonne du titre/problème
COL_DETAIL   = "body"      # colonne du détail (optionnel)
COL_SOLUTION = "answer"    # colonne de la réponse/solution
COL_LANG     = "language"  # colonne de la langue (fr / en)

# Vérification que les colonnes existent
for col in [COL_PROBLEM, COL_SOLUTION]:
    if col not in df.columns:
        raise ValueError(f"Colonne '{col}' introuvable. Colonnes disponibles : {df.columns.tolist()}")

# Supprimer les lignes avec valeurs manquantes sur les colonnes clés
df = df.dropna(subset=[COL_PROBLEM, COL_SOLUTION])

# ---------- FILTRAGE PAR LANGUE ----------
# On garde uniquement le français et l'anglais
if COL_LANG in df.columns:
    df = df[df[COL_LANG].isin(["fr", "en", "FR", "EN", "french", "english"])]
    print(f"Lignes après filtrage FR/EN : {len(df)}")
else:
    print("Colonne langue introuvable, on garde toutes les langues.")

# ---------- CONSTRUCTION DU TEXTE DE DOCUMENT ----------
# On fusionne problème + solution en un seul document texte
# C'est ce texte qui sera embedé et stocké dans ChromaDB

def build_document(row):
    problem  = str(row[COL_PROBLEM]).strip()
    solution = str(row[COL_SOLUTION]).strip()

    # Ajouter le détail si disponible
    detail = ""
    if COL_DETAIL in df.columns and pd.notna(row.get(COL_DETAIL)):
        detail = str(row[COL_DETAIL]).strip()
        detail = f"\nDétail : {detail}"

    return f"Problème : {problem}{detail}\nSolution : {solution}"

df["document"] = df.apply(build_document, axis=1)

# Nettoyage basique du texte
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)          # espaces multiples
    text = re.sub(r'[^\w\sÀ-ÿ.,!?:;\-()]', '', text)  # caractères spéciaux inutiles
    return text.strip()

df["document"] = df["document"].apply(clean_text)

# Supprimer les documents trop courts (< 30 caractères = probablement vides)
df = df[df["document"].str.len() > 30]

print(f"Documents prêts pour l'insertion : {len(df)}")

# ---------- EMBEDDING MODEL ----------
print("Chargement du modèle d'embedding...")

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# ---------- CHROMA DB ----------
print("Connexion à ChromaDB...")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Supprimer l'ancienne collection si elle existe pour repartir propre
try:
    chroma_client.delete_collection(name=COLLECTION_NAME)
    print("Ancienne collection supprimée.")
except Exception:
    pass

collection = chroma_client.create_collection(name=COLLECTION_NAME)

# ---------- INSERTION PAR BATCH ----------
# On insère les documents par blocs de BATCH_SIZE pour éviter les erreurs mémoire

documents  = df["document"].tolist()
total      = len(documents)
inserted   = 0

print(f"Insertion de {total} documents dans ChromaDB...")

for i in range(0, total, BATCH_SIZE):

    batch_docs = documents[i : i + BATCH_SIZE]

    # Générer des IDs uniques pour chaque document
    batch_ids  = [str(uuid.uuid4()) for _ in batch_docs]

    # Calculer les embeddings du batch
    batch_embeddings = embedding_model.encode(batch_docs).tolist()

    # Insérer dans ChromaDB
    collection.add(
        documents=batch_docs,
        embeddings=batch_embeddings,
        ids=batch_ids
    )

    inserted += len(batch_docs)
    print(f"  Inséré : {inserted}/{total}", end="\r")

print(f"\n✅ Base vectorielle construite avec succès : {inserted} documents")
print(f"   Collection : '{COLLECTION_NAME}'")
print(f"   Chemin     : '{CHROMA_PATH}'")