from transformers import pipeline
import re
from rapidfuzz import fuzz

classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

labels = [
    "IT incident",
    "greeting",
    "thanks",
    "goodbye",
    "general question"
]

# ──────────────────────────────────────────
#  VOCABULAIRES PAR LANGUE
# ──────────────────────────────────────────
GREETINGS_FR = ["bonjour", "salut", "bonsoir", "coucou", "allo"]
GREETINGS_EN = ["hello", "hi", "hey", "howdy"]

THANKS_FR = ["merci", "merci beaucoup", "super merci"]
THANKS_EN = ["thanks", "thank you", "thx", "ty"]

GOODBYES_FR = ["au revoir", "a bientot", "bonne journee", "ciao", "bye"]
GOODBYES_EN = ["bye", "goodbye", "see you", "later", "take care"]

GREETINGS = GREETINGS_FR + GREETINGS_EN
THANKS    = THANKS_FR    + THANKS_EN
GOODBYES  = GOODBYES_FR  + GOODBYES_EN

# ──────────────────────────────────────────
#  OUI / NON — GÉRÉS DANS LE CHATBOT PRINCIPAL
# ──────────────────────────────────────────
AFFIRMATIVES = {
    "oui", "yes", "ok", "okay", "yep", "yup",
    "ouais", "bien sur", "bien sûr", "absolument",
    "exactement", "daccord", "d'accord", "parfait",
    "yep", "yup", "sure", "of course"
}

NEGATIVES = {
    "non", "no", "nope", "nan", "pas encore",
    "toujours pas", "tjr pas", "not yet", "jamais"
}

# ──────────────────────────────────────────
#  BLACKLIST MOTS IT
# ──────────────────────────────────────────
IT_BLACKLIST = {
    "imprimante", "printer", "reseau", "réseau", "network",
    "vpn", "wifi", "ecran", "écran", "clavier", "souris",
    "ordinateur", "pc", "laptop", "serveur", "server",
    "mail", "email", "outlook", "windows", "linux",
    "internet", "connexion", "connection", "mot", "passe",
    "password", "lent", "lente", "long", "crash", "bug",
    "erreur", "error", "fonctionne", "marche", "bloque",
    "bloqué", "freeze", "frozen", "virus", "logiciel",
    "software", "application", "app", "fichier", "file",
    "disque", "disk", "memoire", "mémoire", "memory",
    "timeout", "plantage", "restart"
}

MAX_SOCIAL_WORDS = 4


# ──────────────────────────────────────────
#  NORMALISATION
# ──────────────────────────────────────────
def normalize(text):
    text = text.lower().strip()
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)   # aaaa → aa
    text = re.sub(r"[^\w\sÀ-ÿ]", "", text)
    return text


# ──────────────────────────────────────────
#  MEILLEUR MATCH FUZZY — ROBUSTE AUX TYPOS
# ──────────────────────────────────────────
def best_fuzzy_intent(word):
    """
    Compare `word` aux vocabulaires sociaux.
    Utilise partial_ratio SEULEMENT si la longueur est proche
    pour éviter les faux positifs ("you" → "goodbye").
    """
    candidates = []
    all_vocabs = [("greeting", GREETINGS), ("thanks", THANKS), ("goodbye", GOODBYES)]

    for intent, vocab in all_vocabs:
        for v in vocab:
            r = fuzz.ratio(word, v)
            # partial_ratio uniquement si longueurs proches (±2 caractères)
            if abs(len(word) - len(v)) <= 2:
                score = max(r, fuzz.partial_ratio(word, v))
            else:
                score = r
            candidates.append((intent, score))

    best_intent, best_score = max(candidates, key=lambda x: x[1])

    if best_score >= 78:
        return best_intent
    return None


# ──────────────────────────────────────────
#  DÉTECTION LANGUE VIA VOCABULAIRE
# ──────────────────────────────────────────
def detect_lang_from_vocab(word):
    fr_vocabs = GREETINGS_FR + THANKS_FR + GOODBYES_FR
    en_vocabs = GREETINGS_EN + THANKS_EN + GOODBYES_EN

    for v in fr_vocabs:
        if abs(len(word) - len(v)) <= 2:
            if max(fuzz.ratio(word, v), fuzz.partial_ratio(word, v)) >= 78:
                return "fr"
        else:
            if fuzz.ratio(word, v) >= 78:
                return "fr"

    for v in en_vocabs:
        if abs(len(word) - len(v)) <= 2:
            if max(fuzz.ratio(word, v), fuzz.partial_ratio(word, v)) >= 78:
                return "en"
        else:
            if fuzz.ratio(word, v) >= 78:
                return "en"

    return None


# ──────────────────────────────────────────
#  RULE ENGINE — MESSAGES COURTS SOCIAUX
# ──────────────────────────────────────────
def rule_based_intent(text):
    t = normalize(text)
    words = t.split()

    # Phrase trop longue pour être un social intent
    if len(words) > MAX_SOCIAL_WORDS:
        return None, None

    # Contient un mot IT → c'est un incident
    for w in words:
        if w in IT_BLACKLIST:
            return None, None

    # oui/non → géré dans le chatbot principal
    if t in AFFIRMATIVES or t in NEGATIVES:
        return None, None

    # Test fuzzy sur chaque mot
    for w in words:
        intent = best_fuzzy_intent(w)
        if intent:
            lang = detect_lang_from_vocab(w)
            return intent, lang

    return None, None


# ──────────────────────────────────────────
#  DÉTECTEUR D'INTENT PRINCIPAL
# ──────────────────────────────────────────
def detect_intent(text):

    # ÉTAPE 1 — Rule engine (prioritaire pour les mots sociaux)
    rule_intent, lang_hint = rule_based_intent(text)
    if rule_intent:
        return rule_intent, lang_hint

    words = normalize(text).split()

    # ÉTAPE 2 — Message ultra-court inconnu
    if len(words) == 1 and len(words[0]) <= 2:
        return "general question", None

    # ÉTAPE 3 — Classificateur ML
    result = classifier(text, labels)
    label  = result["labels"][0]
    score  = result["scores"][0]

    # ÉTAPE 4 — Correction : social intent sur phrase longue → incident
    if label in ["greeting", "thanks", "goodbye"] and len(words) > MAX_SOCIAL_WORDS:
        return "IT incident", None

    # ÉTAPE 5 — Fallback si confiance faible
    if label == "IT incident" and score < 0.40:
        return "general question", None

    # ÉTAPE 6 — Phrase longue ambiguë → probablement un incident
    if label == "general question" and len(words) > 3:
        return "IT incident", None

    return label, None