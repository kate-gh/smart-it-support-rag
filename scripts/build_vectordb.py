import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import uuid

#DATASET_PATH    = "data/chatbot_rag_final.csv"
DATASET_PATH = "data/chatbot_rag_final_v2.csv"  
CHROMA_PATH     = "./vector_db"
COLLECTION_NAME = "it_support_knowledge"
BATCH_SIZE      = 64   # encode plusieurs embeddings en une fois = plus rapide


def clean(text) -> str:
    if not isinstance(text, str):
        return ""
    return " ".join(text.replace("\n", " ").split()).strip()


def build_enriched_document(question: str, answer: str, category: str) -> str:
    """
    Document enrichi = question + mots-clés de la réponse.
    Sert de 2e vecteur pour capturer les cas où l'utilisateur
    décrit son problème avec les mots de la solution.
    """
    return f"Issue: {question} Context: {category} Resolution keywords: {answer[:200]}"


print("Chargement dataset...")
df = pd.read_csv(DATASET_PATH)
print(f"Lignes : {len(df)}")

print("Chargement modèle d'embedding...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=CHROMA_PATH)

# Supprimer et recréer la collection (reset propre)
try:
    client.delete_collection(COLLECTION_NAME)
    print("Collection existante supprimée.")
except Exception:
    pass

collection = client.create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}  # distance cosine = meilleure pour NLP
)

# ─────────────────────────────────────────────────────────
# INSERTION EN BATCH
# Chaque ligne produit 2 vecteurs :
#   [A] question seule       → capture les formulations directes
#   [B] document enrichi     → capture les descriptions par symptômes
# La RÉPONSE complète est toujours en metadata, jamais orpheline.
# ─────────────────────────────────────────────────────────

docs_a, docs_b       = [], []
metas_a, metas_b     = [], []
ids_a, ids_b         = [], []

for _, row in df.iterrows():
    q    = clean(row["question"])
    a    = clean(row["answer"])
    cat  = clean(row["category"])
    prio = clean(row["priority"])
    src  = clean(str(row.get("source", "")))
    tag  = clean(str(row.get("intent_tag", "")))

    if not q or not a:
        continue

    # Metadata commune — stocke la réponse complète ici
    base_meta = {
        "answer"    : a[:500],   # ChromaDB limite les metadata strings
        "category"  : cat,
        "priority"  : prio,
        "source"    : src,
        "intent_tag": tag,
    }

    # Vecteur A : question seule
    docs_a.append(q)
    metas_a.append({**base_meta, "chunk_type": "question"})
    ids_a.append(str(uuid.uuid4()))

    # Vecteur B : document enrichi (question + contexte réponse)
    enriched = build_enriched_document(q, a, cat)
    docs_b.append(enriched)
    metas_b.append({**base_meta, "chunk_type": "enriched"})
    ids_b.append(str(uuid.uuid4()))

# Encoder en batch (beaucoup plus rapide que encode() ligne par ligne)
print(f"\nEncoding {len(docs_a)} questions...")
emb_a = model.encode(docs_a, batch_size=BATCH_SIZE, show_progress_bar=True)

print(f"Encoding {len(docs_b)} documents enrichis...")
emb_b = model.encode(docs_b, batch_size=BATCH_SIZE, show_progress_bar=True)

# Insérer en batch dans ChromaDB
print("\nInsertion dans ChromaDB...")

CHROMA_BATCH = 500   # ChromaDB recommande <= 1000 par appel
""" 
def insert_batches(docs, embeddings, metadatas, ids):
    for start in range(0, len(docs), CHROMA_BATCH):
        end = start + CHROMA_BATCH
        collection.add(
            documents=embeddings[start:end].tolist(),   # on stocke l'embedding
            embeddings=embeddings[start:end].tolist(),
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )
    print(f"  {len(docs)} documents insérés.")
"""
# Note : on passe documents= avec le texte original pour pouvoir
# l'inspecter plus tard, et embeddings= avec le vecteur calculé.
for start in range(0, len(docs_a), CHROMA_BATCH):
    end = start + CHROMA_BATCH
    collection.add(
        documents=docs_a[start:end],
        embeddings=emb_a[start:end].tolist(),
        metadatas=metas_a[start:end],
        ids=ids_a[start:end],
    )
print(f"  {len(docs_a)} vecteurs A (questions) insérés.")

for start in range(0, len(docs_b), CHROMA_BATCH):
    end = start + CHROMA_BATCH
    collection.add(
        documents=docs_b[start:end],
        embeddings=emb_b[start:end].tolist(),
        metadatas=metas_b[start:end],
        ids=ids_b[start:end],
    )
print(f"  {len(docs_b)} vecteurs B (enrichis) insérés.")

total = collection.count()
print(f"\nVector DB prête — {total} vecteurs au total ({total//2} paires Q/R)")
print(f"Chemin : {CHROMA_PATH}")


# ─────────────────────────────────────────────────────────
# TEST RAPIDE — vérifie que le retrieval retourne des paires cohérentes
# ─────────────────────────────────────────────────────────
print("\n--- TEST RETRIEVAL ---")
test_query = "my password is expired how do I reset it"
q_vec = model.encode(test_query).tolist()

results = collection.query(
    query_embeddings=[q_vec],
    n_results=3,
    where={"chunk_type": "question"},  # cherche uniquement dans les questions
)

for i, (doc, meta) in enumerate(zip(
    results["documents"][0],
    results["metadatas"][0]
)):
    print(f"\n[{i+1}] Question matchée : {doc[:80]}")
    print(f"     Réponse associée  : {meta['answer'][:120]}...")
    print(f"     Catégorie         : {meta['category']} | Priorité : {meta['priority']}")