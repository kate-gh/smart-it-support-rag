from kafka import KafkaConsumer
from sentence_transformers import SentenceTransformer
import chromadb, json, os
from datetime import datetime

os.environ["SENTENCE_TRANSFORMERS_HOME"] = "C:/models/sentence_transformers"

model  = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./vector_db")

try:
    collection = client.get_collection("it_support_knowledge")
    print(f"Collection chargée : {collection.count()} vecteurs")
except Exception as e:
    print(f"Collection introuvable : {e}")
    print("Lance d'abord build_vectordb.py !")
    exit(1)

consumer = KafkaConsumer(
    "kb_updates",
    bootstrap_servers  = "localhost:9092",
    value_deserializer = lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset  = "earliest",
    group_id           = "kb_group"
)

print("Consumer Kafka lancé...")

BAD_QUESTIONS = {"no", "non", "yes", "oui", "nope", "it didn't", "didn't work"}

for msg in consumer:
    data     = msg.value
    question = data.get("question", "").strip()
    answer   = data.get("answer",   "").strip()
    category = data.get("category", "IT Support")
    priority = data.get("priority", "medium")

    print(f"\n[KAFKA] Reçu : '{question[:60]}'")

    # ── Validations ────────────────────────────────────
    if not question or not answer:
        print("[KAFKA] Skip — données manquantes")
        continue

    if len(question.split()) < 3:
        print(f"[KAFKA] Skip — trop court : '{question}'")
        continue

    if question.lower() in BAD_QUESTIONS:
        print(f"[KAFKA] Skip — pas une vraie question")
        continue

    # ── Duplicate check ────────────────────────────────
    try:
        q_emb    = model.encode(question).tolist()
        existing = collection.query(
            query_embeddings = [q_emb],
            n_results        = 1,
            where            = {"chunk_type": {"$eq": "question"}}
        )
        if existing["distances"] and existing["distances"][0]:
            score = 1 - existing["distances"][0][0]
            if score > 0.92:
                print(f"[KAFKA] Doublon (score={score:.2f}) → skip")
                continue
    except Exception as e:
        print(f"[KAFKA] Duplicate check error: {e}")

    # ── Insertion 2 vecteurs ───────────────────────────
    base_id   = f"kafka_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    base_meta = {
        "answer"  : answer[:500],
        "category": category,
        "priority": priority,
        "source"  : "user_validated",
    }

    # Vecteur A — question
    collection.add(
        ids        = [f"{base_id}_a"],
        embeddings = [q_emb],
        documents  = [question],
        metadatas  = [{**base_meta, "chunk_type": "question"}],
    )

    # Vecteur B — enrichi
    enriched = f"Issue: {question} Context: {category} Resolution: {answer[:200]}"
    emb_b    = model.encode(enriched).tolist()
    collection.add(
        ids        = [f"{base_id}_b"],
        embeddings = [emb_b],
        documents  = [enriched],
        metadatas  = [{**base_meta, "chunk_type": "enriched"}],
    )

    total = collection.count()
    print(f"[KAFKA] Ajouté : {base_id} | Total KB : {total} vecteurs")