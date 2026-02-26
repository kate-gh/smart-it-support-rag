import chromadb
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma_client = chromadb.Client()
collection = chroma_client.get_collection("it_support_knowledge")

question = "My VPN is not connecting"

query_embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input=question
).data[0].embedding

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3
)

print(results["documents"][0])