# test_retrieval.py
import chromadb
from sentence_transformers import SentenceTransformer

model      = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
client     = chromadb.PersistentClient(path="./vector_db")
collection = client.get_collection("it_support_knowledge")

print(f"Collection : {collection.count()} vecteurs\n")

TESTS = [
    # (question, categorie_attendue)
    ("my vpn keeps disconnecting",           "Network & Connectivity"),
    ("je peux pas ouvrir outlook ce matin",  "Software & Applications"),
    ("forgot my password how to reset",      "Access Management"),
    ("printer says offline but its on",      "Hardware & Peripherals"),
    ("suspicious email with attachment",     "Security"),
    ("laptop super slow since update",       "IT Support"),
    ("new employee needs laptop setup",      "Onboarding"),
    ("onedrive storage is full",             "Data & Storage"),
    # Questions inconnues — test LLM fallback
    ("my teams background is blurry",        "Software & Applications"),
    ("screen flickers randomly",             "Hardware & Peripherals"),
]

passed = 0
for question, expected_cat in TESTS:
    embedding = model.encode(question).tolist()
    results   = collection.query(
        query_embeddings = [embedding],
        n_results        = 1,
        where            = {"chunk_type": {"$eq": "question"}},
        include          = ["documents", "metadatas", "distances"]
    )

    if not results["ids"][0]:
        print(f" NO RESULT  | {question}")
        continue

    meta     = results["metadatas"][0][0]
    score    = 1 - results["distances"][0][0]
    got_cat  = meta.get("category", "?")
    matched  = got_cat == expected_cat

    status = "✅" if score > 0.45 else "⚠️ "
    cat_ok = "🎯" if matched else "❌"

    print(f"{status} score={score:.2f} {cat_ok} | Q: {question[:45]:<45}")
    print(f"   Match : {results['documents'][0][0][:60]}")
    print(f"   Answer: {meta['answer'][:80]}...")
    print(f"   Cat attendue: {expected_cat} | Cat obtenue: {got_cat}")
    print()

    if score > 0.45:
        passed += 1

print(f"{'='*50}")
print(f"Score retrieval : {passed}/{len(TESTS)} questions bien matchées")