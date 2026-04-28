import json
import os
import re
from datetime import datetime
from pathlib import Path

import chromadb
import fasttext
import joblib
from networkx import hits
import numpy as np
from dotenv import load_dotenv
from groq import Groq
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

# chargé UNE SEULE FOIS
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
import os
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "C:/models/sentence_transformers"

# Le modèle sera téléchargé UNE SEULE FOIS puis réutilisé
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

load_dotenv()

# CONFIGURATION
groq_client      = Groq(api_key=os.environ.get("GROQ_API_KEY"))
GROQ_MODEL       = "llama-3.3-70b-versatile"
COSINE_THRESHOLD = 0.6
MAX_RETRIES      = 5
PENDING_FILE     = "data/pending_kb.json"


# INTENT CLASSIFIER SÉMANTIQUE

INTENT_EXAMPLES = {

    "failure": [
        # Anglais
        "it's still not working",
        "I already tried that",
        "nothing changed",
        "same problem",
        "that didn't help",
        "I tried everything you said",
        "still broken",
        "no luck",
        "still the same issue",
        "I gave it a shot but nothing",
        "tried it, didn't work",
        "the problem persists",
        "still happening",
        "didn't fix it",
        "same error",
        "it did not resolve the issue",
        "this did not resolve my problem",
        "that didn't resolve anything",
        "still not resolved",
        "the issue is not resolved",
        "not resolved yet",
        "hasn't been resolved",
        "issue remains unresolved",
        "it hasn't fixed anything",
        # Français
        "ça marche toujours pas",
        "j'ai déjà essayé ça",
        "rien n'a changé",
        "même problème",
        "ça n'a pas aidé",
        "j'ai tout essayé",
        "toujours pareil",
        "ça persiste",
        "ça ne fonctionne toujours pas",
        "j'ai essayé mais sans succès",
        "le problème continue",
        "toujours la même erreur",
        "ça n'a pas marché",
        "pas de changement",
        "ça n'a pas résolu le problème",
        "toujours pas résolu",
        "le problème n'est pas résolu",
        "ça ne résout rien",
    ],

    "ticket_request": [
        "I need a technician",
        "can someone come fix this",
        "please create a ticket",
        "I want to escalate this",
        "I need human support",
        "open a support ticket",
        "I need someone to look at this",
        "this needs to be escalated",
        "I want to speak to IT support",
        "please send someone",
        "create an incident",
        "j'ai besoin d'un technicien",
        "pouvez-vous créer un ticket",
        "je veux escalader ce problème",
        "j'ai besoin d'aide humaine",
        "quelqu'un peut venir voir",
        "ouvrez un ticket s'il vous plaît",
        "je veux parler à quelqu'un",
        "envoyez un technicien",
        "créez un incident",
        "escalader",
    ],

    "resolved": [
        "it's working now",
        "problem solved",
        "that fixed it",
        "thank you it works",
        "issue resolved",
        "it's working",
        "all good now",
        "perfect it works",
        "yes that worked",
        "it worked",
        "everything is fine now",
        "it's been fixed",
        "ça fonctionne maintenant",
        "problème résolu",
        "ça a marché",
        "merci ça fonctionne",
        "c'est résolu",
        "tout fonctionne",
        "parfait ça marche",
        "oui ça a fonctionné",
        "super ça marche",
        "c'est réparé",
    ],

    "needs_clarification": [
        "it doesn't work",
        "help me",
        "there's a problem",
        "something is wrong",
        "I have an issue",
        "not working",
        "broken",
        "help",
        "it's not working",
        "ça marche pas",
        "aidez-moi",
        "j'ai un problème",
        "quelque chose ne va pas",
        "c'est cassé",
        "aide",
        "problème",
        "ça ne marche pas",
    ],

    "social": [
        "hello", "hi there", "good morning", "hey",
        "thank you so much", "thanks a lot", "thanks",
        "goodbye", "bye", "see you", "have a good day",
        "you're welcome", "how are you",
        "bonjour", "salut", "bonsoir", "bonne journée",
        "merci beaucoup", "merci bien", "au revoir",
        "à bientôt", "comment allez-vous", "comment ça va",
        "coucou", "salu", "bjr",
    ],
}

SIMILARITY_THRESHOLD   = 0.70
LLM_FALLBACK_THRESHOLD = 0.60

#note de disambiguation ajoutée au prompt LLM
DISAMBIGUATION_NOTE = """
CRITICAL disambiguation rules:
- "it did not resolve" / "not resolved" / "didn't resolve" / "still not resolved"
  = "failure" (the problem is NOT fixed)
- "it's working" / "that fixed it" / "resolved" / "problem solved"
  = "resolved" (the problem IS fixed)
When in doubt between failure and resolved: if there is any negation (not, didn't, hasn't, never), choose "failure".
"""


class IntentClassifier:

    def __init__(self, model: SentenceTransformer, groq_client=None, groq_model: str = ""):
        self.model       = model
        self.groq_client = groq_client
        self.groq_model  = groq_model
        self._vecs       = {}
        self._build_index()

    def _build_index(self):
        print("  [IntentClassifier] Construction de l'index...")
        for intent, examples in INTENT_EXAMPLES.items():
            vecs = self.model.encode(examples, show_progress_bar=False)
            self._vecs[intent] = {
                "mean": vecs.mean(axis=0),
                "all" : vecs,
            }
        print(f"  [IntentClassifier] Index prêt — {len(self._vecs)} intents")

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _by_embedding(self, text: str) -> dict:
        vec  = self.model.encode([text], show_progress_bar=False)[0]
        best_intent, best_score = "new_question", 0.0
        for intent, data in self._vecs.items():
            mean_score = self._cosine(vec, data["mean"])
            max_score  = max(self._cosine(vec, v) for v in data["all"])
            score      = 0.6 * mean_score + 0.4 * max_score
            if score > best_score:
                best_score, best_intent = score, intent
        return {"intent": best_intent, "confidence": round(best_score, 3), "method": "embedding"}

    def _by_llm(self, text: str, history: list, current_problem: str = None) -> dict:
        if not self.groq_client:
            return {"intent": "new_question", "confidence": 0.5, "method": "llm_unavailable"}

        ctx = "\n".join(
            f"User: {t.get('user','')}\nAgent: {t.get('bot','')[:80]}..."
            for t in history[-2:]
        ) or "No previous context."

        problem_str = f"Current problem being discussed: {current_problem}" if current_problem else ""

        #DISAMBIGUATION_NOTE 
        prompt = f"""{DISAMBIGUATION_NOTE}

{problem_str}
Conversation context:
{ctx}

User message: "{text}"

Classify EXACTLY ONE intent:
- "failure"             : solution didn't work / problem persists / NOT resolved
- "ticket_request"      : wants a ticket or human technician
- "resolved"            : problem IS confirmed fixed and working
- "needs_clarification" : too vague, no specific IT problem mentioned
- "social"              : greeting, thanks, goodbye
- "new_question"        : new specific IT problem

Respond ONLY with valid JSON:
{{"intent": "...", "confidence": 0.0-1.0}}"""

        try:
            r = self.groq_client.chat.completions.create(
                model    = self.groq_model,
                messages = [
                    {"role": "system", "content": "Classify user intents precisely. Respond only with valid JSON."},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens  = 40,
                temperature = 0,
            )
            raw   = r.choices[0].message.content.strip()
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    "intent"    : data.get("intent", "new_question"),
                    "confidence": float(data.get("confidence", 0.7)),
                    "method"    : "llm",
                }
        except Exception as e:
            print(f"  [IntentClassifier] LLM error: {e}")
        return {"intent": "new_question", "confidence": 0.5, "method": "llm_error"}

    def classify(self, text: str, history: list = None, current_problem: str = None) -> dict:
        if history is None:
            history = []
        result = self._by_embedding(text)
        if result["confidence"] < LLM_FALLBACK_THRESHOLD and self.groq_client:
            print(f"  [IntentClassifier] Confiance faible ({result['confidence']:.2f}) → LLM")
            result = self._by_llm(text, history, current_problem)
        print(f"  [IntentClassifier] '{text[:55]}' → {result['intent']} "
              f"(conf={result['confidence']:.2f}, via {result['method']})")
        return result


# CHARGEMENT MODÈLES
print("Chargement des modèles...")

lang_model      = fasttext.load_model("lid.176.bin")
#embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
chroma_client   = chromadb.PersistentClient(path="./vector_db")
#collection      = chroma_client.get_collection(name="it_support_knowledge")
def get_collection():
    """
    Toujours récupère la collection fraîche depuis le disque.
    Évite le problème de cache mémoire quand Kafka ajoute de nouveaux vecteurs.
    """
    return chroma_client.get_collection(name="it_support_knowledge")

# Garde collection pour la compatibilité (utilisé dans _ingest_to_chroma)
collection = get_collection()

def safe_load(path):
    try:    return joblib.load(path)
    except: return None

priority_model    = safe_load("priority_model.pkl")
intent_classifier = IntentClassifier(embedding_model, groq_client, GROQ_MODEL)

print("✓ Agent IT prêt — tape 'exit' pour quitter\n")


# GUARDRAILS INPUT

def is_understandable(text: str) -> bool:
    t = text.strip().lower()

    # Trop court
    if len(t) < 2:
        return False

    # Seulement chiffres / symboles
    if re.match(r'^[\d\W]+$', t):
        return False

    # Répétition excessive (aaaaaa)
    if re.search(r'(.)\1{4,}', t):
        return False

    # Spam clavier
    for pattern in ["asdfgh", "qwerty", "azerty"]:
        if fuzz.ratio(t, pattern) > 70:
            return False

    # Séquences longues de consonnes
    if re.search(r'[bcdfghjklmnpqrstvwxyz]{5,}', t):
        return False

    # Ratio voyelles / lettres
    letters = [c for c in t if c.isalpha()]
    if len(letters) >= 4:
        vowels = [c for c in letters if c in 'aeiouyàâéèêëîïôùûü']
        ratio = len(vowels) / len(letters)
        if ratio < 0.15:
            return False

    return True


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(everything|all|what)",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+(if\s+you\s+are|a\s+)",
    r"jailbreak", r"do\s+anything\s+now", r"dan\s+mode",
    r"system\s*:\s*", r"<\s*system\s*>", r"new\s+role\s*:",
    r"oublie\s+(tout|toutes|tes\s+instructions)",
    r"ignore\s+tes\s+instructions", r"tu\s+es\s+maintenant",
]
def is_prompt_injection(text: str) -> bool:
    return any(re.search(p, text.lower()) for p in INJECTION_PATTERNS)


IT_KEYWORDS = [
    "computer","laptop","pc","screen","monitor","printer","keyboard","mouse",
    "usb","hdmi","battery","charger","hardware","ordinateur","écran","imprimante",
    "clavier","souris","matériel","disque","disk","wifi","vpn","network","internet",
    "connection","ip","dns","réseau","connexion","firewall","bandwidth","proxy",
    "ethernet","software","install","update","crash","error","bug","outlook","teams",
    "office","excel","word","browser","chrome","logiciel","installer","erreur",
    "application","app","windows","mac","linux","os","système","system","password",
    "login","account","access","locked","mfa","2fa","mdp","authentication","permission",
    "sharepoint","onedrive","mot de passe","compte","accès","verrouillé","virus",
    "malware","phishing","ransomware","sécurité","security","backup","sauvegarde",
    "encryption","bitlocker","ticket","incident","issue","problem","broken",
    "not working","down","slow","freeze","restart","reboot","storage","stockage",
    "problème","lent","planté","redémarrer","email","azure","cloud","server",
    "database","api","serveur","base de données","sap","jira","salesforce","zoom",
]

def is_it_by_keywords(text: str) -> bool:
    return any(kw in text.lower() for kw in IT_KEYWORDS)

def is_it_by_llm(text: str) -> bool:
    try:
        r = groq_client.chat.completions.create(
            model    = GROQ_MODEL,
            messages = [{"role": "user", "content":
                f'Is this an IT support question? "{text}" Answer ONLY "yes" or "no".'}],
            max_tokens=5, temperature=0,
        )
        return r.choices[0].message.content.strip().lower().startswith("yes")
    except Exception:
        return True

def check_scope(text: str) -> bool:
    if len(text.split()) <= 3:   return True
    if is_it_by_keywords(text):  return True
    return is_it_by_llm(text)


def detect_language(text: str) -> str:
    if not text.strip(): return "en"
    pred = lang_model.predict(text.replace("\n", " "))
    lang = pred[0][0].replace("__label__", "")
    return lang if lang in ("fr", "en") else "en"


def translate_to_english(text: str, lang: str) -> str:
    
    if lang == "en":
        return text   # already in English
    try:
        response = groq_client.chat.completions.create(
            model    = GROQ_MODEL,
            messages = [{"role": "user", "content":
                f'Translate this IT support message to English. '
                f'Return ONLY the translation, nothing else.\n'
                f'Message: "{text}"'
            }],
            max_tokens  = 100,
            temperature = 0,
        )
        translated = response.choices[0].message.content.strip()
        print(f"  [TRADUCTION] '{text[:40]}' → '{translated[:40]}'")
        return translated
    except Exception:
        return text   # en cas d'erreur utilise le texte original


# GUARDRAIL OUTPUT

OUT_OF_SCOPE_SIGNALS = [
    "as a language model", "en tant que modèle de langage",
    "i cannot help with", "je ne peux pas vous aider avec",
    "stock price", "cours de bourse", "weather", "météo",
    "recette", "recipe", "political", "politique",
]
def output_is_clean(response: str) -> bool:
    return not any(s in response.lower() for s in OUT_OF_SCOPE_SIGNALS)


# UTILITAIRES

def social_intent(text: str, lang: str = "en"):
    t = text.lower().strip()
    fr_greets = ["bonjour","salut","salu","bonsoir","coucou","allo","bjr","bsr"]
    en_greets = ["hello","hi","hey","good morning","good evening","howdy","greetings"]
    if any(t.startswith(w) for w in fr_greets + en_greets):
        return "greet"
    if any(w in t for w in ["thank","merci","thanks","thx","ty"]):
        return "thanks"
    if any(w in t for w in ["bye","goodbye","au revoir","à bientôt","a bientot","ciao"]):
        return "bye"
    return None


KNOWN_SERVICES = [
    "vpn","email","outlook","teams","sharepoint","onedrive",
    "sap","jira","salesforce","azure","office","wifi","internet",
]
def extract_service(text: str):
    t = text.lower()
    for s in KNOWN_SERVICES:
        if s in t: return s
    return None


# OUTIL 1 — classify_ticket avec fuzzy matching
CLASSIFY_RULES = [
    {
        "category": "Access Management", "priority": "high",
        "exact"   : ["password","mdp","locked","mfa","2fa","access","accès",
                     "login","compte","account","authentication","permission",
                     "verrouillé","mot de passe"],
        "fuzzy"   : ["pasword","passord","psasword"],
    },
    {
        "category": "Network & Connectivity", "priority": "high",
        "exact"   : ["vpn","network","wifi","internet","réseau","connexion",
                     "ip","dns","ethernet","proxy","firewall","bandwidth"],
        "fuzzy"   : ["interent","inernet","conection","reseaux","connextion"],
    },
    {
        "category": "Software & Applications", "priority": "medium",
        "exact"   : ["outlook","email","teams","office","word","excel","powerpoint",
                     "software","logiciel","application","app","browser","chrome",
                     "windows","linux","mac","install","update","crash","freeze",
                     "bug","error","erreur"],
        "fuzzy"   : ["outloook","offce","installl","windwos","widnows","sofware"],
    },
    {
        "category": "Hardware & Peripherals", "priority": "medium",
        "exact"   : ["printer","screen","keyboard","imprimante","écran","clavier",
                     "mouse","souris","laptop","ordinateur","pc","computer","monitor",
                     "usb","hdmi","battery","disk","disque","hardware","matériel",
                     "headset","webcam","scanner","trackpad"],
        "fuzzy"   : ["ipremente","impremente","impremante","iprimante","primante",
                     "priner","priinter","imprimannt","sourie","sourirs",
                     "keybord","keyborad","ordinatuer","oridnateur","laptpo",
                     "moniter","montior"],
    },
    {
        "category": "Security", "priority": "high",
        "exact"   : ["virus","phishing","security","sécurité","ransomware","malware",
                     "hack","breach","suspicious","encryption","bitlocker","spam","scam"],
        "fuzzy"   : ["ransomwre","securty","securite","fisching","viris"],
    },
    {
        "category": "Onboarding", "priority": "high",
        "exact"   : ["onboarding","new employee","nouveau","setup","premier jour",
                     "first day","new account","nouvel"],
        "fuzzy"   : ["onbording","onboardng","onbordng"],
    },
    {
        "category": "Data & Storage", "priority": "medium",
        "exact"   : ["onedrive","sharepoint","drive","stockage","storage","backup",
                     "sauvegarde","fichier","file","dossier","folder"],
        "fuzzy"   : ["sharepint","onedriv","backupp","stoarge"],
    },
]
FUZZY_THRESHOLD = 82


def tool_classify(text: str) -> dict:
    t     = text.lower()
    words = t.split()

    # Niveau 1 — correspondance exacte
    for rule in CLASSIFY_RULES:
        if any(kw in t for kw in rule["exact"]):
            prio = priority_model.predict([text])[0] if priority_model else rule["priority"]
            print(f"  [OUTIL 1] classify_ticket → {rule['category']} / {prio}")
            return {"category": rule["category"], "priority": prio}

    # Niveau 2 — fuzzy matching sur chaque mot
    best_cat, best_prio, best_score = None, "medium", 0
    for word in words:
        if len(word) < 4: continue
        for rule in CLASSIFY_RULES:
            for fw in rule["fuzzy"] + [kw for kw in rule["exact"] if len(kw) >= 5]:
                score = fuzz.ratio(word, fw)
                if score >= FUZZY_THRESHOLD and score > best_score:
                    best_score = score
                    best_cat   = rule["category"]
                    best_prio  = rule["priority"]

    if best_cat:
        prio = priority_model.predict([text])[0] if priority_model else best_prio
        print(f"  [OUTIL 1] classify_ticket → {best_cat} / {prio}  (fuzzy={best_score})")
        return {"category": best_cat, "priority": prio}

    prio = priority_model.predict([text])[0] if priority_model else "medium"
    print(f"  [OUTIL 1] classify_ticket → IT Support / {prio}")
    return {"category": "IT Support", "priority": prio}


# OUTIL 2 — check_system_status
def tool_check_status(service: str) -> dict:
    status = "operational"   # en production → appel API monitoring
    print(f"  [OUTIL 2] check_system_status({service}) → {status}")
    return {"service": service, "status": status}


# OUTIL 3 — ask_clarification
def tool_clarify(lang: str) -> str:
    print("  [OUTIL 3] ask_clarification")
    if lang == "fr":
        return (
            "Pourriez-vous préciser votre problème ?\n"
            "Par exemple : quel logiciel ou appareil, "
            "quel message d'erreur, depuis quand ?"
        )
    return (
        "Could you describe your issue in more detail?\n"
        "For example: which software or device, "
        "what error message, and since when?"
    )


# OUTIL 4 — search_kb (RAG ChromaDB)
""" 
def tool_search_kb(query: str, exclude_ids: list = None) -> list:
    q_vec   = embedding_model.encode(query).tolist()
    results = collection.query(query_embeddings=[q_vec], n_results=6)
    hits = []
    for doc, meta, dist, doc_id in zip(
        results["documents"][0], results["metadatas"][0],
        results["distances"][0], results["ids"][0],
    ):
        if dist >= COSINE_THRESHOLD:              continue
        if exclude_ids and doc_id in exclude_ids: continue
        hits.append({
            "id"      : doc_id,
            "answer"  : meta.get("answer", "")[:800],
            "category": meta.get("category", "IT Support"),
            "priority": meta.get("priority", "medium"),
            "score"   : round(1 - dist, 2),
        })
    hits.sort(key=lambda x: x["score"], reverse=True)
    result = hits[:3]
    print(f"  [OUTIL 4] search_kb → {len(result)} résultat(s)")
    return result
"""
def extract_answer_from_doc(doc: str):
    """
    Extrait la partie 'Solution' depuis le texte complet
    """
    try:
        if "Solution :" in doc:
            return doc.split("Solution :", 1)[1].strip()
        return doc
    except:
        return doc

def tool_search_kb(query: str, exclude_ids: list = None, category: str = None):
    exclude_ids = exclude_ids or []

    try:
        fresh_client    = chromadb.PersistentClient(path="./vector_db")
        live_collection = fresh_client.get_collection(name="it_support_knowledge")

        query_en        = translate_to_english(query, detect_language(query))
        query_embedding = embedding_model.encode(query_en).tolist()

        where_filter = None
        if category and category != "IT Support":
            where_filter = {"category": {"$eq": category}}

        results = live_collection.query(
            query_embeddings=[query_embedding],
            n_results=10,  # 🔥 IMPORTANT (plus de candidats pour reranking)
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            print("🔎 KB SEARCH (0 hits)")
            return []

        candidates = []

        for i in range(len(results["ids"][0])):
            doc_id   = results["ids"][0][i]
            meta     = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            score    = 1 - distance

            if doc_id in exclude_ids:
                continue

            answer = meta.get("answer", "")
            question_doc = results["documents"][0][i]

            if not answer:
                continue

            candidates.append({
                "id": doc_id,
                "question": question_doc,
                "answer": answer,
                "category": meta.get("category", "IT Support"),
                "priority": meta.get("priority", "medium"),
                "score": score,  # embedding score
            })

        if not candidates:
            return []

        # 🔥 RERANKING (LA PARTIE IMPORTANTE)
        pairs = [(query_en, c["question"]) for c in candidates]
        rerank_scores = reranker.predict(pairs)

        for i, c in enumerate(candidates):
            c["rerank_score"] = float(rerank_scores[i])

        # 🔥 TRI FINAL PAR RERANK
        candidates = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

        # 🔥 enlever doublons réponses
        seen = set()
        final_hits = []
        for c in candidates:
            if c["answer"] in seen:
                continue
            seen.add(c["answer"])
            final_hits.append(c)

        # 🔥 seuil intelligent
        if final_hits:
            top_score = final_hits[0]["rerank_score"]
            if top_score < 0.3:
                print(f"⚠️ Low confidence rerank ({top_score:.2f}) → LLM")
                return []

        print(f"🔎 KB SEARCH ({len(final_hits)}) — rerank top: {final_hits[0]['rerank_score']:.2f}")

        return final_hits[:3]

    except Exception as e:
        print(f"❌ search error: {e}")
        return []

# OUTIL 5 — llm_fallback (génération de procédure IT en 3 étapes)

def tool_llm_fallback(question: str, category: str, priority: str,
                      lang: str, attempt_num: int = 1) -> str:

    # Plus la tentative est avancée, plus l'approche est différente
    approach_notes_en = {
        1: "",
        2: "The previous basic solution didn't work. Try a more advanced approach.",
        3: "Previous solutions failed. Focus on software/driver/config causes.",
        4: "All common solutions failed. Suggest diagnostic commands or system checks.",
        5: "Last attempt. Suggest the most thorough reset/reinstall procedure.",
    }

    approach_notes_fr = {
        1: "",
        2: "La solution précédente n'a pas fonctionné. Propose une approche plus avancée.",
        3: "Les solutions courantes ont échoué. Concentre-toi sur les pilotes ou la configuration.",
        4: "Suggère des commandes de diagnostic ou une vérification système.",
        5: "Dernière tentative. Suggère une réinstallation complète ou un reset système.",
    }

    # Choix langue
    if lang == "fr":
        approach = approach_notes_fr.get(attempt_num, approach_notes_fr[5])
        system_msg = "Tu es un spécialiste du support informatique. Réponds UNIQUEMENT en français."
        lang_instr = f"Réponds UNIQUEMENT en français.\n{approach}"

        #  contact IT seulement à la dernière tentative
        if attempt_num >= 5:
            end_phrase = "Si le problème persiste, contactez le support IT."
        else:
            end_phrase = ""

    else:
        approach = approach_notes_en.get(attempt_num, approach_notes_en[5])
        system_msg = "You are an IT helpdesk specialist. Answer ONLY in English."
        lang_instr = f"Answer ONLY in English.\n{approach}"

        #  contact IT seulement à la dernière tentative
        if attempt_num >= 5:
            end_phrase = "If the issue persists, please contact the IT helpdesk."
        else:
            end_phrase = ""

    #  PROMPT
    prompt = (
        f"{lang_instr}\n\n"
        f"Problem: {question}\n"
        f"Category: {category} | Priority: {priority}\n\n"
        "Give exactly 3 numbered steps. No markdown."
    )

    # ajouter seulement si dernière tentative
    if end_phrase:
        prompt += f'\nEnd with: "{end_phrase}"'

    # appel LLM
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


def save_to_pending(question: str, answer: str, category: str, priority: str) -> None:
    from pending_store import save_pending
    save_pending(
        question  = question,
        answer    = answer,
        category  = category,
        priority  = priority,
        source    = "llm_fallback",
    )
    print(f"  [DB] Sauvegardé dans pending_kb MySQL")

# OUTIL 6 — create_ticket

def tool_create_ticket(summary: str, category: str, priority: str) -> dict:
    ticket_id = f"INC{datetime.now().strftime('%Y%m%d%H%M%S')}"
    delay     = "2 heures" if priority == "high" else "24 heures"
    print(f"  [OUTIL 6] create_ticket → {ticket_id} ({category} / {priority})")
    return {"ticket_id": ticket_id, "delay": delay}

def generate_from_kb(question: str, hits: list, lang: str,
                     history: list = None, is_retry: bool = False) -> str:

    context = "\n\n---\n\n".join(
        f"Solution {i} (relevance {h['score']:.0%}, category: {h['category']}):\n{h['answer']}"
        for i, h in enumerate(hits, 1)
    )

    history_str = ""
    if history:
        lines = [
            f"User: {t.get('user','')}\nAgent: {t.get('bot','')[:100]}..."
            for t in history[-3:]
        ]
        history_str = "\nConversation history:\n" + "\n".join(lines) + "\n"

    # ── Tout le prompt dans la langue cible ──────────────
    if lang == "fr":
        system_msg  = "Tu es un assistant support informatique. Réponds UNIQUEMENT en français."
        retry_note  = (
            "\nIMPORTANT : L'utilisateur a déjà essayé la solution précédente. "
            "Propose des étapes DIFFÉRENTES à partir des solutions ci-dessous."
            if is_retry else ""
        )
        prompt = f"""Réponds UNIQUEMENT en français.{retry_note}{history_str}

Tu es un assistant support informatique.
Utilise UNIQUEMENT les solutions ci-dessous. N'invente aucune étape.
Ne mentionne pas de tickets, numéros de téléphone ou emails.

Problème de l'utilisateur : {question}

Solutions de la base de connaissances :
{context}

RÈGLES :
- Entre 1 et 4 étapes numérotées selon la complexité du problème.
- Une phrase claire et actionnable par étape.
- Termine par une courte question demandant si ça a aidé.
- Sans markdown, sans gras.

1. [étape]
2. [étape]
3. [étape]

[question de suivi]"""

    else:
        system_msg  = "You are an IT helpdesk assistant. Answer ONLY in English."
        retry_note  = (
            "\nIMPORTANT: The user already tried the previous solution. "
            "Present DIFFERENT steps from the solutions below."
            if is_retry else ""
        )
        prompt = f"""Answer ONLY in English.{retry_note}{history_str}

You are an IT helpdesk assistant.
Use ONLY the solutions below. DO NOT invent steps.
DO NOT mention tickets, phone numbers, or emails.

User problem: {question}

Solutions from knowledge base:
{context}

RULES:
- Between 1 and 4 numbered steps depending on complexity.
- One clear, actionable sentence per step.
- End with one short question asking if it helped.
- No markdown, no bold.

1. [step]
2. [step]
3. [step]

[follow-up question]"""

    response = groq_client.chat.completions.create(
        model    = GROQ_MODEL,
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=300, temperature=0.1,
    )
    return response.choices[0].message.content.strip()

# MESSAGES BILINGUES

MSG = {
    "greet"           : {"en": "Hello! What IT issue can I help you with today?",
                         "fr": "Bonjour ! Quel est votre problème informatique ?"},
    "thanks"          : {"en": "You're welcome! Let me know if you need anything else.",
                         "fr": "Avec plaisir ! N'hésitez pas si vous avez un autre problème."},
    "bye"             : {"en": "Goodbye! Have a great day.",
                         "fr": "Au revoir ! Bonne journée."},
    "unclear"         : {"en": "I didn't understand. Could you rephrase your IT issue?",
                         "fr": "Je n'ai pas compris. Pouvez-vous reformuler votre problème ?"},
    "injection"       : {"en": "I detected an attempt to manipulate the system. I can only assist with IT support.",
                         "fr": "J'ai détecté une tentative de manipulation. Je ne peux aider qu'avec des problèmes IT."},
    "out_scope"       : {"en": ("I'm an IT support assistant. I can only help with IT problems: "
                                "passwords, VPN, software, printers, network, access, security.\n"
                                "What IT issue can I help you with?"),
                         "fr": ("Je suis un assistant IT. Je peux uniquement aider avec des problèmes "
                                "informatiques : mots de passe, VPN, logiciels, imprimantes, réseau, accès, sécurité.\n"
                                "Quel est votre problème IT ?")},
    "no_kb_trying_llm": {"en": "No solution found in the knowledge base. Let me try to help based on IT best practices...\n",
                         "fr": "Aucune solution trouvée dans la base. Je vais essayer de vous aider avec mes connaissances IT...\n"},
    "feedback": {
                        "en": "Did this solution resolve your issue? (yes/no)",
                        "fr": "Est-ce que cette solution a résolu votre problème ? (oui/non)"
                    },
    "clarify": {
                "en": "Could you please clarify your issue? (e.g., what exactly is not working, any error message, when did it start?)",
                "fr": "Pouvez-vous préciser votre problème ? (par exemple : qu'est-ce qui ne fonctionne pas, message d'erreur, depuis quand ?)"
            },
                        
    "saved"           : {"en": "Answer saved to improve the knowledge base. Thank you!",
                         "fr": "Réponse sauvegardée pour enrichir la base de connaissances. Merci !"},
    "ticket_ok"       : {"en": "Ticket {id} created. IT team will contact you within {delay}.",
                         "fr": "Ticket {id} créé. L'équipe IT vous contactera dans {delay}."},
    "escalate"        : {"en": "The available solutions did not resolve your issue. Escalating to IT team...",
                         "fr": "Les solutions disponibles n'ont pas résolu le problème. Escalade vers l'équipe IT..."},
    "retry"           : {"en": "Let me try with different solutions:",
                         "fr": "Voici d'autres solutions :"},
    "checking"        : {"en": "Analyzing your request...\n",
                         "fr": "Analyse de votre demande...\n"},
    "status_ok"       : {"en": "{service} is operational — no known outages. Let me find a solution for you.",
                         "fr": "{service} fonctionne normalement. Je cherche une solution pour vous."},
    "status_bad"      : {"en": "{service} may be experiencing issues. Creating a priority ticket...",
                         "fr": "{service} semble avoir des problèmes. Création d'un ticket prioritaire..."},
    "resolved_ack"    : {"en": "Great! Glad the issue is resolved. Feel free to ask if anything else comes up.",
                         "fr": "Super ! Ravi que le problème soit résolu. N'hésitez pas si autre chose survient."},
}

def m(key: str, lang: str, **kw) -> str:
    l   = lang if lang in ("fr", "en") else "en"
    msg = MSG[key][l]
    return msg.format(**kw) if kw else msg


# ÉTAT CONVERSATIONNEL

class State:
    def __init__(self):
        self.conversation_history = []
        self.reset()

    def reset(self):
        self.question       = None
        self.presented_ids  = []
        self.failure_count  = 0
        self.classification = None
        self.ticket_done    = False


# BOUCLE PRINCIPALE

if __name__ == "__main__":

    state = State()
    lang  = "en"

    print("=" * 60)
    print("   IT Self-Service Agent")
    print("   Tape 'exit' pour quitter")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("Vous : ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\nAgent : {m('bye', lang)}")
            break

        if not user_input: continue
        if user_input.lower() == "exit":
            print(f"Agent : {m('bye', lang)}")
            break

        # GUARDRAIL 1 — bruit
        if not is_understandable(user_input):
            print(f"Agent : {m('unclear', lang)}\n" + "-"*60)
            continue

        # GUARDRAIL 2 — injection
        if is_prompt_injection(user_input):
            print(f"Agent : {m('injection', lang)}\n" + "-"*60)
            continue

        # Langue
        detected = detect_language(user_input)
        if detected in ("fr", "en"):
            lang = detected

        # Intent sémantique
        intent_result = intent_classifier.classify(
            text            = user_input,
            history         = state.conversation_history,
            current_problem = state.question,
        )
        intent = intent_result["intent"]

        # ── Social ────────────────────────────────────────
        if intent == "social":
            si  = social_intent(user_input, lang=lang)
            key = si if si else "greet"
            msg = m(key, lang)
            print(f"Agent : {msg}\n" + "-"*60)
            state.conversation_history.append({"user": user_input, "bot": msg})
            if key == "bye": break
            continue

        if intent == "ticket_request" and not state.ticket_done:
            cl     = state.classification or tool_classify(user_input)
            q      = state.question or user_input
            ticket = tool_create_ticket(q, cl["category"], cl["priority"])
            state.ticket_done = True
            msg    = m("ticket_ok", lang, id=ticket["ticket_id"], delay=ticket["delay"])
            print(f"Agent : {msg}\n" + "-"*60)
            state.conversation_history.append({"user": user_input, "bot": msg})
            state.reset()
            continue

        if intent == "resolved":
            msg = m("resolved_ack", lang)
            print(f"Agent : {msg}\n" + "-"*60)
            state.conversation_history.append({"user": user_input, "bot": msg})
            state.reset()
            continue

        if intent == "failure" and state.question:
            state.failure_count += 1

            if state.failure_count >= MAX_RETRIES:
                cl     = state.classification or tool_classify(state.question)
                ticket = tool_create_ticket(state.question, cl["category"], cl["priority"])
                state.ticket_done = True
                bot_msg = f"{m('escalate', lang)} {m('ticket_ok', lang, id=ticket['ticket_id'], delay=ticket['delay'])}"
                print(f"Agent : {m('escalate', lang)}")
                print(f"Agent : {m('ticket_ok', lang, id=ticket['ticket_id'], delay=ticket['delay'])}\n" + "-"*60)
                state.conversation_history.append({"user": user_input, "bot": bot_msg})
                state.reset()
                continue

            print(f"Agent : {m('retry', lang)}\n")
            hits = tool_search_kb(
                translate_to_english(state.question, lang),
                exclude_ids=state.presented_ids
            )

            if not hits:
                cl     = state.classification or tool_classify(state.question)
                ticket = tool_create_ticket(state.question, cl["category"], cl["priority"])
                state.ticket_done = True
                bot_msg = f"{m('escalate', lang)} {m('ticket_ok', lang, id=ticket['ticket_id'], delay=ticket['delay'])}"
                print(f"Agent : {m('escalate', lang)}")
                print(f"Agent : {m('ticket_ok', lang, id=ticket['ticket_id'], delay=ticket['delay'])}\n" + "-"*60)
                state.conversation_history.append({"user": user_input, "bot": bot_msg})
                state.reset()
                continue

            state.presented_ids.extend([h["id"] for h in hits])
            response = generate_from_kb(
                state.question, hits, lang,
                history=state.conversation_history, is_retry=True,
            )
            if not output_is_clean(response):
                response = m("out_scope", lang)
            print(f"Agent :\n{response}\n" + "-"*60)
            state.conversation_history.append({"user": user_input, "bot": response})
            continue

        # GUARDRAIL 3 — hors-scope
        if not check_scope(user_input):
            msg = m("out_scope", lang)
            print(f"Agent : {msg}\n" + "-"*60)
            state.conversation_history.append({"user": user_input, "bot": msg})
            continue

        # Vague
        if intent == "needs_clarification":
            msg = tool_clarify(lang)
            print(f"Agent : {msg}\n" + "-"*60)
            state.conversation_history.append({"user": user_input, "bot": msg})
            if not state.question:
                state.question = user_input
            continue

        # Nouvelle question IT 
        print(f"Agent : {m('checking', lang)}")
        classification = tool_classify(user_input)

        service = extract_service(user_input)
        if service:
            status = tool_check_status(service)
            if status["status"] != "operational":
                ticket = tool_create_ticket(user_input, classification["category"], classification["priority"])
                msg_s  = m("status_bad", lang, service=service.upper())
                msg_t  = m("ticket_ok",  lang, id=ticket["ticket_id"], delay=ticket["delay"])
                print(f"Agent : {msg_s}")
                print(f"Agent : {msg_t}\n" + "-"*60)
                state.conversation_history.append({"user": user_input, "bot": f"{msg_s} {msg_t}"})
                state.reset()
                continue
            else:
                print(f"Agent : {m('status_ok', lang, service=service.upper())}\n")

        # Avant de chercher dans la KB — traduire si nécessaire
        query_for_kb = translate_to_english(user_input, lang)
        hits = tool_search_kb(query_for_kb)

        state.question       = user_input
        state.classification = classification
        state.presented_ids  = [h["id"] for h in hits] if hits else []
        state.failure_count  = 0
        state.ticket_done    = False

        # KB vide → LLM fallback
        if not hits:
            print(f"Agent : {m('no_kb_trying_llm', lang)}")
            fallback_answer = tool_llm_fallback(
                question = user_input,
                category = classification["category"],
                priority = classification["priority"],
                lang     = lang,
            )
            if not output_is_clean(fallback_answer):
                fallback_answer = m("out_scope", lang)
            print(f"Agent :\n{fallback_answer}\n" + "-"*60)
            state.conversation_history.append({"user": user_input, "bot": fallback_answer})

            feedback = input(f"{m('feedback', lang)}").strip().lower()
            if feedback in ("o", "y", "oui", "yes", "1"):
                save_to_pending(user_input, fallback_answer, classification["category"], classification["priority"])
                print(f"Agent : {m('saved', lang)}\n" + "-"*60)
            else:
                ticket = tool_create_ticket(user_input, classification["category"], classification["priority"])
                msg_t  = m("ticket_ok", lang, id=ticket["ticket_id"], delay=ticket["delay"])
                print(f"Agent : {msg_t}\n" + "-"*60)
                state.conversation_history.append({"user": user_input, "bot": msg_t})
            continue

        # KB trouvée → générer
        response = generate_from_kb(
            user_input, hits, lang,
            history=state.conversation_history,
        )
        if not output_is_clean(response):
            response = m("out_scope", lang)
        print(f"Agent :\n{response}\n" + "-"*60)
        state.conversation_history.append({"user": user_input, "bot": response})