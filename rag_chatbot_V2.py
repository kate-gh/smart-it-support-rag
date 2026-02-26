import chromadb
from sentence_transformers import SentenceTransformer
from llm_openrouter import generate_answer

print("Chargement modèles IA...")

# embedding model
embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# charger base vectorielle
chroma_client = chromadb.PersistentClient(path="./vector_db")

collection = chroma_client.get_collection(
    name="it_support_knowledge"
)

print("Assistant IT prêt")
print("Tape 'exit' pour quitter.\n")

while True:

    question = input("👤 Vous : ")

    if question.lower() == "exit":
        break

    # embedding question
    query_embedding = embedding_model.encode(question).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    context = "\n".join(results["documents"][0])

    print("\nDEBUG CONTEXT:\n", context)

    # PROMPT RAG
    prompt = f"""
You are an expert IT support assistant.

User problem:
{question}

Knowledge base:
{context}

Give a clear troubleshooting answer with:
1. Step 1
2. Step 2
3. Step 3

Only give practical actions.
"""

    answer = generate_answer(prompt)

    print("\n🤖 Assistant IT :")
    print(answer)
    print("-" * 60)