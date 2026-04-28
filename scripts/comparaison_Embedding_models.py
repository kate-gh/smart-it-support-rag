import pandas as pd
import time
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Charger dataset
df = pd.read_csv("../data/chatbot_rag_final_v2.csv")


questions = df["question"].tolist()

models = {
    "MiniLM": "sentence-transformers/all-MiniLM-L6-v2",
    "MPNet": "sentence-transformers/all-mpnet-base-v2",
    "Small": "sentence-transformers/paraphrase-MiniLM-L3-v2",
    "BGE": "BAAI/bge-small-en"
}

results = []

for name, path in models.items():
    print(f"\nTesting {name}")

    model = SentenceTransformer(path)

    start = time.time()
    embeddings = model.encode(questions)
    total_time = time.time() - start

    correct = 0

    for i, q in enumerate(questions):
        sims = cosine_similarity([embeddings[i]], embeddings)[0]
        sims[i] = -1  # ignore itself

        best_match = sims.argmax()

        # si même catégorie → bon résultat
        if df.iloc[i]["category"] == df.iloc[best_match]["category"]:
            correct += 1

    accuracy = correct / len(questions)

    results.append({
        "model": name,
        "accuracy": accuracy,
        "time_sec": total_time
    })

# affichage
print("\n RESULTS")
for r in results:
    print(r)