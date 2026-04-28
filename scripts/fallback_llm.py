import json
import os
from datetime import datetime
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
GROQ_MODEL  = "llama-3.3-70b-versatile"

PENDING_FILE = "data/pending_kb.json"   # fichier de stockage des nouvelles entrées


# ─────────────────────────────────────────────────────────
# 1. GÉNÉRATION PAR LE LLM (quand KB vide)
# ─────────────────────────────────────────────────────────

def generate_fallback_answer(question: str, category: str,
                              priority: str, lang: str) -> str:
    """
    Le LLM génère une réponse IT basée sur ses connaissances générales.
    Utilisé UNIQUEMENT quand la KB ne contient aucun résultat.
    """
    lang_instr = "Réponds en français." if lang == "fr" else "Answer in English."

    prompt = f"""{lang_instr}

You are an expert IT helpdesk specialist with 10+ years of experience.
A user has an IT problem and no solution was found in the knowledge base.
Generate a reliable step-by-step solution based on standard IT best practices.

User problem: {question}
Category: {category}
Priority: {priority}

Rules:
- EXACTLY 3 numbered steps, clear and actionable.
- Based only on standard IT procedures (do not invent proprietary tools).
- End with: "If the issue persists, please contact the IT helpdesk."
- One sentence per step maximum.

Format:
1. [step]
2. [step]
3. [step]

If the issue persists, please contact the IT helpdesk."""

    response = groq_client.chat.completions.create(
        model       = GROQ_MODEL,
        messages    = [{"role": "user", "content": prompt}],
        max_tokens  = 300,
        temperature = 0.2,   # bas = réponses fiables et standard
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────
# 2. STOCKAGE POUR ENRICHISSEMENT KB (feedback loop)
# ─────────────────────────────────────────────────────────

def load_pending() -> list:
    """Charge le fichier pending_kb.json."""
    if not Path(PENDING_FILE).exists():
        return []
    with open(PENDING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_to_pending(question: str, answer: str,
                    category: str, priority: str) -> None:
    """
    Sauvegarde une nouvelle paire Q/R dans pending_kb.json.
    Ces entrées seront validées manuellement avant d'aller dans ChromaDB.
    """
    os.makedirs("data", exist_ok=True)

    pending = load_pending()

    # Vérifier si la question existe déjà (éviter les doublons)
    existing_questions = [p["question"].lower() for p in pending]
    if question.lower() in existing_questions:
        return

    new_entry = {
        "question"  : question,
        "answer"    : answer,
        "category"  : category,
        "priority"  : priority,
        "source"    : "llm_fallback",
        "validated" : False,              # ← à passer True après vérification humaine
        "timestamp" : datetime.now().isoformat(),
    }

    pending.append(new_entry)

    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    print(f"  [PENDING] Nouvelle entrée ajoutée → {PENDING_FILE}")


# ─────────────────────────────────────────────────────────
# 3. VALIDATION ET AJOUT À CHROMADB
# Script séparé à lancer manuellement pour valider les entrées
# ─────────────────────────────────────────────────────────

def validate_and_add_to_kb():
    """
    Lance ce script manuellement (ex: chaque semaine) pour :
      1. Afficher les entrées en attente de validation
      2. Valider ou rejeter chaque entrée
      3. Ajouter les entrées validées dans ChromaDB

    Usage : python fallback_llm.py
    """
    import chromadb
    from sentence_transformers import SentenceTransformer

    pending = load_pending()
    not_validated = [p for p in pending if not p["validated"]]

    if not not_validated:
        print("Aucune entrée en attente de validation.")
        return

    print(f"\n{len(not_validated)} entrées en attente de validation\n")
    print("=" * 60)

    # Charger ChromaDB
    chroma_client   = chromadb.PersistentClient(path="./vector_db")
    collection      = chroma_client.get_collection(name="it_support_knowledge")
    embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    validated_count = 0
    rejected_count  = 0

    for i, entry in enumerate(not_validated):
        print(f"\n[{i+1}/{len(not_validated)}]")
        print(f"  Question  : {entry['question']}")
        print(f"  Catégorie : {entry['category']} / {entry['priority']}")
        print(f"  Réponse   :\n    {entry['answer'][:200]}...")
        print(f"  Générée le: {entry['timestamp']}")

        choice = input("\n  Valider ? (o = oui / n = non / q = quitter) : ").strip().lower()

        if choice == "q":
            break
        elif choice == "o":
            # Ajouter à ChromaDB
            doc_id    = f"validated_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
            embedding = embedding_model.encode(entry["question"]).tolist()

            collection.add(
                ids        = [doc_id],
                embeddings = [embedding],
                documents  = [entry["question"]],
                metadatas  = [{
                    "answer"    : entry["answer"],
                    "category"  : entry["category"],
                    "priority"  : entry["priority"],
                    "source"    : "validated_llm_fallback",
                    "chunk_type": "question",
                }]
            )

            # Marquer comme validé dans pending_kb.json
            for p in pending:
                if p["question"] == entry["question"]:
                    p["validated"] = True

            print(f"  Ajouté à ChromaDB ({doc_id})")
            validated_count += 1
        else:
            print(f"  ✗ Rejeté")
            rejected_count += 1

    # Sauvegarder les mises à jour
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Résultat : {validated_count} validées / {rejected_count} rejetées")
    print(f"ChromaDB enrichi avec {validated_count} nouvelles entrées.")


# ─────────────────────────────────────────────────────────
# INTÉGRATION DANS it_agent.py
# Remplace le bloc "if not hits" dans ton agent par ceci :
# ─────────────────────────────────────────────────────────

INTEGRATION_EXAMPLE = """
# Dans it_agent.py — remplace le bloc "if not hits:" par :

from fallback_llm import generate_fallback_answer, save_to_pending

if not hits:
    print(f"🤖 Agent : [KB vide — génération par LLM...]\\n")

    # LLM génère une réponse basée sur ses connaissances IT
    fallback = generate_fallback_answer(
        question = user_input,
        category = classification["category"],
        priority = classification["priority"],
        lang     = lang,
    )

    print(f"🤖 Agent :\\n{fallback}\\n" + "-"*60)

    # Demander à l'utilisateur si la réponse a été utile
    feedback_prompt = (
        "Cette réponse vous a-t-elle aidé ? (o/n) : "
        if lang == "fr" else
        "Was this answer helpful? (y/n): "
    )
    feedback = input(f"👤 {feedback_prompt}").strip().lower()

    if feedback in ("o", "y", "oui", "yes"):
        # Stocker pour enrichissement futur de la KB
        save_to_pending(
            question = user_input,
            answer   = fallback,
            category = classification["category"],
            priority = classification["priority"],
        )
        confirm = (
            "✅ Réponse sauvegardée pour enrichir la base de connaissances."
            if lang == "fr" else
            "✅ Answer saved to enrich the knowledge base."
        )
        print(f"🤖 Agent : {confirm}\\n" + "-"*60)

    # Mémoriser pour la gestion des retries
    state.question       = user_input
    state.classification = classification
    state.presented_ids  = []
    state.failure_count  = 0
    state.ticket_done    = False
    continue
"""


# ─────────────────────────────────────────────────────────
# LANCEMENT DIRECT : mode validation
# python fallback_llm.py → interface de validation des entrées
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Mode validation des entrées KB en attente\n")
    validate_and_add_to_kb()