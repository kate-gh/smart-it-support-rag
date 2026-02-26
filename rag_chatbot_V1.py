import chromadb
from sentence_transformers import SentenceTransformer

# Charger modèle embedding local
print("Chargement modèle IA...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Charger base vectorielle RAG
chroma_client = chromadb.PersistentClient(path="./vector_db")

collection = chroma_client.get_collection(
    name="it_support_knowledge"
)

print("Chatbot RAG prêt")
print("Tape 'exit' pour quitter.\n")

# Boucle chatbot
while True:

    question = input("Vous : ")

    if question.lower() == "exit":
        break

    # ---- embedding question ----
    query_embedding = model.encode(question).tolist()

    # ---- recherche similarité ----
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    documents = results["documents"][0]

    # Génération réponse simple
    print("\nChatbot :")
    print("Voici les solutions possibles :\n")

    for i, doc in enumerate(documents):
        print(f"Solution {i+1}:")
        print(doc)
        print("-" * 50)