import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

# 
#dataset
df = pd.read_csv("dataset_clean_final.csv")

# Charger modèle embedding local (DL)
print("Chargement du modèle embedding local...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

#b vectorielle ChromaDB
#chroma_client = chromadb.Client()
chroma_client = chromadb.PersistentClient(path="./vector_db")

collection = chroma_client.create_collection(
    name="it_support_knowledge"
)

print("Indexation en cours...")

#Fonction embedding locale
def get_embedding(text):
    return embedding_model.encode(text).tolist()

#Ajouter incidents dans la base RAG

for i, row in df.iterrows():

    document = f"""
    Issue: {row['Customer_Issue']}
    Category: {row['Category']}
    Environment: {row['Environment']}
    Solution: {row['Suggested_Solution']}
    """

    embedding = get_embedding(document)

    collection.add(
        documents=[document],
        embeddings=[embedding],
        ids=[str(i)]
    )

print("Base RAG créée avec succès !")