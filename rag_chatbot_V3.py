from rapidfuzz import fuzz
import chromadb
import re
import random
from sentence_transformers import SentenceTransformer
from llm_openrouter import generate_answer
import joblib
import fasttext
from intent_detector import detect_intent, AFFIRMATIVES, NEGATIVES

# ──────────────────────────────────────────
#  CHARGEMENT MODÈLES
# ──────────────────────────────────────────
print("Chargement language detector...")
lang_model = fasttext.load_model("lid.176.bin")

def detect_language(text):
    if not text.strip():
        return "en"
    prediction = lang_model.predict(text.replace("\n", " "))
    lang_code  = prediction[0][0].replace("__label__", "")
    return lang_code


# ──────────────────────────────────────────
#  FILTRE BRUIT CLAVIER
# ──────────────────────────────────────────
def is_understandable(text):
    t = text.strip().lower()

    # Simulation clavier aléatoire connue
    if fuzz.ratio(t, "asdfgh") > 70: return False
    if fuzz.ratio(t, "qwerty") > 70: return False
    if fuzz.ratio(t, "azerty") > 70: return False

    # Que des chiffres ou caractères spéciaux
    if re.match(r'^[\d\W]+$', t):
        return False

    # Trop de caractères répétés (aaaaa, zzzzz)
    if re.search(r'(.)\1{4,}', t):
        return False

    # Cluster de consonnes sans aucune voyelle → bruit (fghj, hyuj, qwsd...)
    words = t.split()
    for word in words:
        # un seul mot entièrement consonne de 4+ lettres
        if len(word) >= 4 and re.match(r'^[bcdfghjklmnpqrstvwxyz]+$', word):
            return False

    return True


# ──────────────────────────────────────────
#  NETTOYAGE CONTEXTE RAG
# ──────────────────────────────────────────
def clean_context(text):
    text = re.sub(r'\btel_num\b', '', text)
    text = re.sub(r'\bacc_num\b', '', text)
    text = re.sub(r'\bemail_\w+\b', '', text)
    text = re.sub(r'\bDear\s+\w+\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\butilisateur\b', "l'utilisateur", text, flags=re.IGNORECASE)
    text = re.sub(r'\bname\b', "l'utilisateur", text, flags=re.IGNORECASE)
    text = re.sub(r'(contact us at|reach us at|call us at|calling)\s*\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(contactez.nous|appeler).{0,10}\.', '', text, flags=re.IGNORECASE)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ──────────────────────────────────────────
#  CHARGEMENT ML MODELS + RAG
# ──────────────────────────────────────────
difficulty_model = joblib.load("difficulty_model.pkl")
priority_model   = joblib.load("priority_model.pkl")
auto_model       = joblib.load("auto_resolve_model.pkl")

print("Chargement modèles IA...")
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="./vector_db")
collection    = chroma_client.get_collection(name="it_support_knowledge")

print("Assistant IT prêt ✅")
print("Tape 'exit' pour quitter.\n")


# ──────────────────────────────────────────
#  RÉPONSES VARIÉES
# ──────────────────────────────────────────
GREETINGS_FR = [
    "Bonjour 👋 Comment puis-je vous aider ?",
    "Bonjour ! Quel est votre problème informatique ?",
    "Bonjour 😊 Je suis là pour vous aider, dites-moi tout."
]
GREETINGS_EN = [
    "Hello 👋 How can I help you?",
    "Hi there! What seems to be the issue?",
    "Hello 😊 I'm here to help, what's going on?"
]
THANKS_FR = [
    "Avec plaisir 👍 N'hésitez pas si vous avez un autre problème.",
    "De rien ! Bonne continuation.",
    "Content d'avoir pu vous aider 😊 À bientôt !"
]
THANKS_EN = [
    "You're welcome 👍 Let me know if you need anything else.",
    "Happy to help! Feel free to ask anytime.",
    "Glad I could assist 😊 Have a great day!"
]

# Contexte : bot venait de saluer → demander le problème
ASK_PROBLEM_FR = [
    "D'accord, décrivez-moi votre problème informatique 🖥️",
    "Très bien, quel est votre problème ?",
    "Je vous écoute, qu'est-ce qui ne fonctionne pas ?"
]
ASK_PROBLEM_EN = [
    "Sure, go ahead and describe your IT issue 🖥️",
    "Alright, what seems to be the problem?",
    "I'm listening, what's not working?"
]

# Contexte : solution donnée → pas résolu
NOT_RESOLVED_FR = [
    "D'accord, essayons autre chose. Pouvez-vous décrire exactement ce que vous voyez ?",
    "Pas de problème, décrivez-moi plus précisément la situation.",
    "Compris. Qu'est-ce qui se passe exactement sur votre écran ?"
]
NOT_RESOLVED_EN = [
    "No worries, let's try something else. Can you describe exactly what you see?",
    "Alright, tell me more precisely what's happening.",
    "Got it. What exactly do you see on your screen?"
]

# Contexte : bot venait de saluer → pas de problème
NO_HELP_FR = [
    "Pas de souci ! Passez une bonne journée 👋",
    "D'accord, n'hésitez pas à revenir si vous avez besoin !",
    "Très bien, bonne journée 😊"
]
NO_HELP_EN = [
    "No problem! Have a great day 👋",
    "Alright, feel free to come back if you need help!",
    "Sure, have a great day 😊"
]

# Sans contexte : oui reçu seul
OUI_SANS_CONTEXTE_FR = [
    "D'accord 😊 Avez-vous un problème informatique à me décrire ?",
    "Très bien ! De quoi avez-vous besoin ?",
]
OUI_SANS_CONTEXTE_EN = [
    "Sure 😊 Do you have an IT issue to describe?",
    "Great! What do you need help with?",
]

# Sans contexte : non reçu seul
NON_SANS_CONTEXTE_FR = [
    "D'accord, n'hésitez pas si vous avez besoin d'aide 👋",
    "Très bien, je suis là si besoin !",
]
NON_SANS_CONTEXTE_EN = [
    "Alright, feel free to ask if you need help 👋",
    "Got it, I'm here if you need anything!",
]

# Message incompréhensible / trop court
UNCLEAR_FR = [
    "Je n'ai pas bien compris 🤔 Pouvez-vous décrire votre problème informatique plus précisément ?",
    "Pouvez-vous reformuler ? Je veux m'assurer de bien comprendre votre problème.",
    "Je ne suis pas sûr de comprendre. Pouvez-vous expliquer ce qui ne fonctionne pas ?"
]
UNCLEAR_EN = [
    "I didn't quite understand 🤔 Could you describe your IT problem in more detail?",
    "Could you rephrase that? I want to make sure I understand your issue.",
    "I'm not sure I understand. Can you explain what's not working?"
]


# ──────────────────────────────────────────
#  ÉTAT DE LA CONVERSATION
# ──────────────────────────────────────────
last_bot_context     = None   # "asked_problem" | "gave_solution" | "waiting_problem" | None
conversation_history = []     # historique pour le prompt RAG
last_lang            = "fr"   # langue du dernier échange


# ──────────────────────────────────────────
#  BOUCLE PRINCIPALE
# ──────────────────────────────────────────
while True:

    question = input("👤 Vous : ").strip()

    if not question:
        continue

    if question.lower() == "exit":
        print("🤖 Assistant IT : À bientôt 👋")
        break

    q_normalized = question.lower().strip()

    # ══════════════════════════════════════
    #  INTENT DETECTION D'ABORD
    # ══════════════════════════════════════
    intent, lang_hint = detect_intent(question)
    print(f"[DEBUG] intent={intent} | lang_hint={lang_hint}")

    # Détection langue (lang_hint prioritaire, FastText en fallback)
    if lang_hint:
        lang = lang_hint
    else:
        lang = detect_language(question)
    if lang not in ["fr", "en"]:
        lang = "en"

    last_lang = lang

    # ══════════════════════════════════════
    #  GESTION OUI / NON (TOUJOURS INTERROMPUE)
    # ══════════════════════════════════════
    if q_normalized in AFFIRMATIVES:

        if last_bot_context == "asked_problem":
            bot_msg = random.choice(ASK_PROBLEM_FR if lang == "fr" else ASK_PROBLEM_EN)
            last_bot_context = "waiting_problem"

        elif last_bot_context == "gave_solution":
            bot_msg = random.choice(THANKS_FR if lang == "fr" else THANKS_EN)
            last_bot_context = None

        else:
            # Aucun contexte : "oui" sans raison → inviter à décrire
            bot_msg = random.choice(OUI_SANS_CONTEXTE_FR if lang == "fr" else OUI_SANS_CONTEXTE_EN)
            last_bot_context = "waiting_problem"

        print(f"\n🤖 Assistant IT : {bot_msg}")
        conversation_history.append({"user": question, "bot": bot_msg})
        print("-" * 60)
        continue

    if q_normalized in NEGATIVES:

        if last_bot_context == "asked_problem":
            bot_msg = random.choice(NO_HELP_FR if lang == "fr" else NO_HELP_EN)
            last_bot_context = None

        elif last_bot_context == "gave_solution":
            bot_msg = random.choice(NOT_RESOLVED_FR if lang == "fr" else NOT_RESOLVED_EN)
            last_bot_context = "waiting_problem"

        else:
            bot_msg = random.choice(NON_SANS_CONTEXTE_FR if lang == "fr" else NON_SANS_CONTEXTE_EN)
            last_bot_context = None

        print(f"\n🤖 Assistant IT : {bot_msg}")
        conversation_history.append({"user": question, "bot": bot_msg})
        print("-" * 60)
        continue

    # ══════════════════════════════════════
    #  FILTRE BRUIT CLAVIER
    #  Placé ICI : avant les intents sociaux pour bloquer "hjkl" etc.
    #  Les vrais mots sociaux ("hi","salut","merci") ont des voyelles → passent.
    # ══════════════════════════════════════
    if not is_understandable(question):
        bot_msg = random.choice(UNCLEAR_FR if lang == "fr" else UNCLEAR_EN)
        print(f"\n🤖 Assistant IT : {bot_msg}")
        print("-" * 60)
        continue

    # ══════════════════════════════════════
    #  RÉPONSES SOCIALES (greeting / thanks / goodbye)
    # ══════════════════════════════════════
    if intent == "greeting":
        bot_msg = random.choice(GREETINGS_FR if lang == "fr" else GREETINGS_EN)
        print(f"\n🤖 Assistant IT : {bot_msg}")
        conversation_history.append({"user": question, "bot": bot_msg})
        last_bot_context = "asked_problem"
        print("-" * 60)
        continue

    if intent == "thanks":
        bot_msg = random.choice(THANKS_FR if lang == "fr" else THANKS_EN)
        print(f"\n🤖 Assistant IT : {bot_msg}")
        conversation_history.append({"user": question, "bot": bot_msg})
        last_bot_context = None
        print("-" * 60)
        continue

    if intent == "goodbye":
        bot_msg = "Au revoir 👋 Bonne journée !" if lang == "fr" else "Goodbye 👋 Have a great day!"
        print(f"\n🤖 Assistant IT : {bot_msg}")
        conversation_history.append({"user": question, "bot": bot_msg})
        last_bot_context = None
        print("-" * 60)
        continue

    # ══════════════════════════════════════
    #  MESSAGE TROP COURT ET AMBIGU
    # ══════════════════════════════════════
    words = question.split()
    if intent == "general question" and len(words) <= 2:
        bot_msg = random.choice(UNCLEAR_FR if lang == "fr" else UNCLEAR_EN)
        print(f"\n🤖 Assistant IT : {bot_msg}")
        print("-" * 60)
        continue

    # ══════════════════════════════════════
    #  PIPELINE RAG + ML
    # ══════════════════════════════════════

    # Prédictions ML
    pred_difficulty = difficulty_model.predict([question])[0]
    pred_priority   = priority_model.predict([question])[0]
    pred_auto       = auto_model.predict([question])[0]

    print(f"\n🧠 ML → Difficulty: {pred_difficulty} | Priority: {pred_priority} | Auto-resolve: {pred_auto}")

    # Embedding + recherche vectorielle
    query_embedding = embedding_model.encode(question).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=3)
    documents = results.get("documents", [[]])[0]

    if not documents:
        bot_msg = (
            "Aucun incident similaire trouvé dans la base de connaissances. "
            "Pouvez-vous décrire votre problème différemment ?"
            if lang == "fr" else
            "No similar incident found in the knowledge base. "
            "Could you describe your problem differently?"
        )
        print(f"\n🤖 Assistant IT : {bot_msg}")
        print("-" * 60)
        continue

    context = clean_context("\n".join(documents))
    print(f"\n[DEBUG CONTEXT]\n{context}\n")

    # Historique des 3 derniers échanges
    history_text = ""
    if conversation_history:
        recent = conversation_history[-3:]
        history_text = "Conversation history:\n"
        for turn in recent:
            history_text += f"User: {turn['user']}\nAssistant: {turn['bot']}\n"
        history_text += "\n"

    # Instruction langue
    language_instruction = (
        "You MUST answer in French. Write troubleshooting steps in clear professional French."
        if lang == "fr" else
        "You MUST answer in English. Write troubleshooting steps in clear professional English."
    )

    # Prompt RAG
    prompt = f"""
{language_instruction}

You are a friendly and professional IT support assistant.
Your tone is warm, concise and helpful — not robotic.

{history_text}

User problem:
{question}

Knowledge base:
{context}

ML Analysis:
Difficulty: {pred_difficulty}
Priority: {pred_priority}
Auto Resolve: {pred_auto}

TASK:
Give exactly 3 numbered troubleshooting steps based ONLY on the knowledge base.
End with one short natural sentence asking if the problem is resolved.

FORMAT:
1. action
2. action
3. action
[one short natural follow-up sentence]

STRICT RULES:
- Use ONLY knowledge base solutions.
- Steps must be short, practical and directly actionable.
- NEVER mention phone numbers, contact details, or suggest calling anyone.
- NEVER say "contact us" or "reach out to support".
- NEVER ask for more information before giving steps — give steps directly.
- Warm and professional tone.
- Stop after the follow-up sentence.

Answer:
"""

    answer = generate_answer(prompt)

    print(f"\n🤖 Assistant IT :\n{answer}")
    conversation_history.append({"user": question, "bot": answer})
    last_bot_context = "gave_solution"

    print("-" * 60)