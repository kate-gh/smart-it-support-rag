import re
from enum import Enum

_bert = None

def get_bert():
    global _bert
    if _bert is None:
        from bert_feedback import BertFeedbackClassifier
        _bert = BertFeedbackClassifier("./feedback_model_pt")
    return _bert

class FeedbackState(Enum):
    NONE        = "none"
    PENDING     = "pending"
    PARTIAL_OK  = "partial_ok"
    CONFIRM_ESC = "confirm_esc"

MAX_ATTEMPTS = 5  # KB + LLM avant escalade

# ── Regex ──────────────────────────────────────────────────────────
REGEX_PATTERNS = {
    "yes": [
        r"\b(yes|oui|yep|ouais|ok|okay|parfait|super|great|cool|nickel)\b",
        r"\b(ça marche|it works|it'?s? (working|fixed)|c'est (bon|réparé|résolu))\b",
        r"\b(problem solved|problème résolu|tout fonctionne|all good|fixed)\b",
    ],
    "no": [
        r"^\s*(no|non|nope|nan|nop)\s*$",   # ← AJOUT CRITIQUE
        r"^\s*(no|non)[\s,\.!]*",
        r"\b(toujours pas|still not|still broken|same (issue|problem|error))\b",
        r"\b(didn'?t (work|fix|help)|n'a pas (marché|fonctionné)|toujours pareil)\b",
        r"\b(rien (n'a )?changé|nothing changed|le bug (persiste|continue))\b",
        r"\b(même résultat|same result|pas de changement|no change)\b",
    ],
    "partial": [
        r"\b(presque|almost|partiellement|partially)\b",
        r"\b(ça marche (presque|un peu)|kind of (works|working)|sort of works)\b",
        r"(l'?étape \d|step \d).{0,40}(pas|not|doesn'?t|ne fonctionne)",
        r"\b(worked but|a marché mais|sauf que|except that)\b",
    ],
    "mixed": [
        r"(oui|yes|ça marche|it works|fixed|résolu|merci|thanks).{0,80}(mais|but|however|aussi|also|yet|still).{0,80}(problème|problem|vpn|wifi|mail|outlook|imprimante|printer|écran|screen|clavier|keyboard|internet|network|réseau|access|accès|issue|error|erreur|slow|lent|crash)",
        r"(merci|thanks).{0,60}(mais|but|however|still|yet).{0,80}(problème|issue|error|internet|access|network)",
        r"(works|fonctionne|marche).{0,40}(but|mais|however|still|yet).{0,80}(can'?t|cannot|ne peux pas|impossible|still|toujours)",
    ],
}

_COMPILED = {
    k: [re.compile(p, re.IGNORECASE | re.DOTALL) for p in pats]
    for k, pats in REGEX_PATTERNS.items()
}
""" 
def _parse_by_regex(text: str) -> str | None:
    for p in _COMPILED["mixed"]:
        if p.search(text):
            return "mixed"
    for p in _COMPILED["partial"]:
        if p.search(text):
            return "partial"
    for p in _COMPILED["yes"]:
        if p.search(text):
            return "no" if any(
                neg.search(text) for neg in [
                    re.compile(r"\b(pas|not|mais pas|but not|ne.*pas)\b", re.I)
                ]
            ) else "yes"
    for p in _COMPILED["no"]:
        if p.search(text):
            return "no"
    return None
"""
def _parse_by_regex(text: str) -> str | None:
    # Mixed en premier — TOUJOURS avant yes
    for p in _COMPILED["mixed"]:
        if p.search(text):
            return "mixed"
    
    for p in _COMPILED["partial"]:
        if p.search(text):
            return "partial"
    
    for p in _COMPILED["yes"]:
        if p.search(text):
            # ── Vérification critique : "it works BUT..." ──
            has_but = re.search(
                r"\b(but|mais|however|still|yet|sauf|except|though)\b",
                text, re.IGNORECASE
            )
            has_problem = re.search(
                r"\b(can'?t|cannot|not|still|toujours|problem|issue|error|"
                r"internet|access|network|réseau|accès)\b",
                text, re.IGNORECASE
            )
            # Si "it works" + "but" + problème → mixed, pas yes
            if has_but and has_problem:
                return "mixed"
            
            # Négation simple → no
            has_neg = re.search(
                r"\b(pas|not|mais pas|but not|ne.*pas)\b",
                text, re.IGNORECASE
            )
            return "no" if has_neg else "yes"
    
    for p in _COMPILED["no"]:
        if p.search(text):
            return "no"
    
    return None

# ── Mapping intent → feedback ──────────────────────────────────────
INTENT_TO_FEEDBACK = {
    "resolved"           : "yes",
    "failure"            : "no",
    "add_detail"         : "add_detail",
    "reformulate"        : "reformulate",
    "new_problem"        : "new_problem",
    "new_question"       : "new_problem",
    "ticket_request"     : "ticket_direct",
    "social"             : None,
    "needs_clarification": None,
}

# ── Messages ───────────────────────────────────────────────────────
_MSGS = {
    "ask_partial": {
        "fr": "Je vois que certaines étapes ont fonctionné. Quelle étape a posé problème et quel message d'erreur avez-vous eu ?",
        "en": "I see some steps worked. Which step failed and what error message did you get?",
    },
    "ask_mixed_new": {
        "fr": "Super que ce problème soit résolu ! Vous mentionnez aussi un autre souci — je vous aide avec ça maintenant ?",
        "en": "Great that issue is resolved! You also mentioned another problem — shall I help with that now?",
    },
    "confirm_ticket": {
        "fr": "Les solutions disponibles n'ont pas pu résoudre votre problème. Voulez-vous que je crée un ticket pour qu'un technicien IT vous contacte ? (oui/non)",
        "en": "The available solutions couldn't resolve your issue. Would you like me to create a ticket so an IT technician contacts you? (yes/no)",
    },
    "fallback_ask": {
        "fr": "La solution proposée a-t-elle résolu votre problème ? (oui / non / partiellement)",
        "en": "Did the proposed solution resolve your issue? (yes / no / partially)",
    },
    "trying_llm": {
        "fr": "La base de connaissances est épuisée. Je vais essayer de vous aider avec mes connaissances IT générales...\n",
        "en": "Knowledge base exhausted. Let me try to help based on general IT best practices...\n",
    },
    "consult_team": {
        "fr": (
            "Nous avons essayé toutes les solutions disponibles sans succès.\n"
            "Je vous recommande de contacter directement l'équipe IT :\n"
            "• Par email : it-support@entreprise.com\n"
            "• Par téléphone : +212 5XX-XXXXXX\n"
            "• En personne : Bureau IT, Bâtiment A, Salle 101\n"
            "Voulez-vous que je crée un ticket en priorité ? (oui/non)"
        ),
        "en": (
            "We have tried all available solutions without success.\n"
            "I recommend contacting the IT team directly:\n"
            "• Email: it-support@company.com\n"
            "• Phone: +212 5XX-XXXXXX\n"
            "• In person: IT Office, Building A, Room 101\n"
            "Would you like me to create a priority ticket? (yes/no)"
        ),
    },
    "no_more_solutions": {
        "fr": "Je n'ai plus de solutions disponibles dans ma base. Un ticket sera nécessaire si le problème persiste.",
        "en": "I have no more solutions available. A ticket will be needed if the issue persists.",
    },
}

def _msg(key: str, lang: str) -> str:
    return _MSGS[key].get(lang, _MSGS[key]["en"])


# ── Helpers ────────────────────────────────────────────────────────
def _reset(state: dict):
    state.update({
        "question"               : None,
        "classification"         : None,
        "presented_ids"          : [],
        "failure_count"          : 0,
        "ticket_done"            : False,
        "last_fallback"          : None,
        "awaiting_feedback"      : False,
        "feedback_state"         : None,
        "feedback_ambiguous_count": 0,
        "ticket_refus_count"     : 0,
        "llm_fallback_used"      : False,
    })

def _attempt_count(state: dict) -> int:
    """Nombre total de tentatives = failure_count + 1 (tentative initiale)."""
    return state.get("failure_count", 0) + 1

def _get_next_solution(
    state, lang, user_input,
    tool_search_kb, generate_from_kb,
    translate_fn, output_clean_fn, m_fn,
    tool_llm_fallback, is_retry=True
) -> dict | None:
    """
    Cherche la prochaine solution :
    1. KB avec exclusion des IDs déjà présentés
    2. Si KB vide → LLM fallback (une seule fois)
    3. Si tout épuisé → None
    """
    # Tentative KB
    hits = tool_search_kb(
        translate_fn(state.get("question", user_input), lang),
        exclude_ids=state.get("presented_ids", []),
    )

    if hits:
        state["presented_ids"].extend([h["id"] for h in hits])
        resp = generate_from_kb(
            state["question"], hits, lang,
            history=state.get("history", []),
            is_retry=is_retry,
        )
        if not output_clean_fn(resp):
            resp = m_fn("out_scope", lang)
        state.setdefault("history", []).append({"user": user_input, "bot": resp})
        state["awaiting_feedback"] = True
        cl = state.get("classification") or {}
        return {
            "response" : resp,
            "type"     : "kb",
            "category" : cl.get("category"),
            "priority" : cl.get("priority"),
        }

    if tool_llm_fallback:
        cl           = state.get("classification") or {}
        attempt_num  = state.get("failure_count", 1)
        intro        = _msg("trying_llm", lang)

        fallback = tool_llm_fallback(
            question    = state.get("question", user_input),
            category    = cl.get("category", "IT Support"),
            priority    = cl.get("priority", "medium"),
            lang        = lang,
            attempt_num = attempt_num,   # ← NOUVEAU : indique quelle tentative
        )
        if not output_clean_fn(fallback):
            fallback = m_fn("out_scope", lang)

        full_resp = f"{intro}{fallback}"
        state.setdefault("history", []).append({"user": user_input, "bot": full_resp})
        state["awaiting_feedback"] = True
        return {
            "response"    : full_resp,
            "type"        : "llm_fallback",
            "category"    : cl.get("category"),
            "priority"    : cl.get("priority"),
            "ask_feedback": True,
        }

    return None


# ── Mots-clés IT ───────────────────────────────────────────────────
_IT_KEYWORDS = {
    "screen","écran","black","noir","printer","imprimante","vpn","wifi",
    "password","mot de passe","laptop","pc","computer","ordinateur",
    "keyboard","clavier","mouse","souris","outlook","teams","office",
    "slow","lent","crash","error","erreur","frozen","planté","network",
    "réseau","internet","disk","disque","usb","monitor","headset",
    "webcam","bluetooth","battery","charger","sharepoint","onedrive",
    "malware","virus","phishing","account","compte","access","accès",
}

def _is_new_it_question(text: str) -> bool:
    """
    True si le texte est une nouvelle question IT.
    Critères stricts pour éviter faux positifs :
    - Au moins 3 mots
    - Contient un mot-clé IT
    - Aucun pattern feedback détecté par regex
    """
    if len(text.split()) < 3:
        return False
    if not any(kw in text.lower() for kw in _IT_KEYWORDS):
        return False
    # Si regex détecte un feedback → c'est du feedback, pas une question
    if _parse_by_regex(text) is not None:
        return False
    return True

# ── Gestionnaire principal ─────────────────────────────────────────
def handle_feedback(
    user_input      : str,
    state           : dict,
    lang            : str,
    intent_classifier,
    intent_result   : dict,
    tool_search_kb,
    generate_from_kb,
    classify_fn,
    ticket_fn,
    translate_fn,
    save_pending_fn,
    output_clean_fn,
    m_fn,
    tool_llm_fallback = None,
) -> dict | None:


    if not state.get("awaiting_feedback"):
        return None

    # ══════════════════════════════════════════════════════
    # ÉTAPE 0 — PRIORITÉ ABSOLUE : feedback court explicite
    # Mots de feedback courts → jamais interpréter comme question
    # ══════════════════════════════════════════════════════
    fb_short = _parse_by_regex(user_input)

    # Négation directe non captée par regex → forcer "no"
    if fb_short is None and re.search(
        r"^\s*(no[,\.\s]|non[,\.\s]|it didn'?t|ça n'a pas|nope|didn'?t work|"
        r"still (not|broken)|toujours (pas|pareil)|same (issue|problem))",
        user_input, re.IGNORECASE
    ):
        fb_short = "no"

    # Si feedback court clair ET message court → traiter directement
    if fb_short is not None and len(user_input.split()) <= 8:
        fb = fb_short
        # ── Sauter au traitement feedback (goto simulé)
        state["feedback_ambiguous_count"] = 0
        # continuer vers le bas avec fb défini
        
    else:
        # ══════════════════════════════════════════════════
        # ÉTAPE 1 — Nouvelle question IT longue ?
        # Seulement si message suffisamment long ET contient mot-clé IT
        # ══════════════════════════════════════════════════
        if _is_new_it_question(user_input):
            intent = (intent_result or {}).get("intent", "")
            if intent not in ("resolved", "failure", "social"):
                print(f"[FEEDBACK] New IT question → reset: '{user_input[:50]}'")
                _reset(state)
                return None

        # ══════════════════════════════════════════════════
        # ÉTAPE 2 — Regex complet
        # ══════════════════════════════════════════════════
        fb = _parse_by_regex(user_input)

        # ══════════════════════════════════════════════════
        # ÉTAPE 3 — BERT (ton modèle existant)
        # ══════════════════════════════════════════════════
        if fb is None:
            #bert_result = _bert.predict(user_input, state.get("question"))
            bert_result = get_bert().predict(user_input, state.get("question"))
            fb          = bert_result["feedback"]

            # ══════════════════════════════════════════════
            # ÉTAPE 4 — LLM si BERT incertain
            # ══════════════════════════════════════════════
            if fb is None or bert_result["use_llm_backup"]:
                intent = (intent_result or {}).get("intent", "unknown")
                fb_llm = INTENT_TO_FEEDBACK.get(intent)
                if fb_llm is not None:
                    fb = fb_llm
                if intent in ("new_problem", "new_question"):
                    _reset(state)
                    return None

        # ══════════════════════════════════════════════════
        # ÉTAPE 5 — Ambiguïté totale
        # ══════════════════════════════════════════════════
        if fb is None:
            state["feedback_ambiguous_count"] = state.get("feedback_ambiguous_count", 0) + 1
            if state["feedback_ambiguous_count"] >= 2:
                state["feedback_ambiguous_count"] = 0
                msg = _msg("fallback_ask", lang)
                state.setdefault("history", []).append({"user": user_input, "bot": msg})
                return {"response": msg, "type": "social"}
            state["awaiting_feedback"]        = False
            state["feedback_ambiguous_count"] = 0
            return None

        state["feedback_ambiguous_count"] = 0

    if state.get("feedback_state") == FeedbackState.CONFIRM_ESC.value:

        # et non une réponse oui/non au ticket
        if fb not in ("yes", "no", "ticket_direct") and intent_result:
            intent = intent_result.get("intent", "")
            if intent in ("new_problem", "new_question") or (
                fb is None and len(user_input.split()) > 3
            ):
                # Reset complet et laisse le flux normal traiter la nouvelle question
                _reset(state)
                return None   # app.py reprend avec le nouveau problème

        if fb in ("yes", "ticket_direct"):
            cl = state.get("classification") or classify_fn(state["question"])
            state["awaiting_feedback"] = False
            state["feedback_state"]    = None
            state["ticket_refus_count"]= 0
            return ticket_fn(state, lang, state["question"], cl)

        else:
            # Refus ticket — logique existante...
            refus = state.get("ticket_refus_count", 0) + 1
            state["ticket_refus_count"] = refus
            state["feedback_state"]     = None
            state["awaiting_feedback"]  = False

            if refus >= 2:
                cl = state.get("classification") or classify_fn(state.get("question",""))
                state["ticket_refus_count"] = 0
                return ticket_fn(state, lang, state.get("question",""), cl)

            sol = _get_next_solution(
                state, lang, user_input,
                tool_search_kb, generate_from_kb,
                translate_fn, output_clean_fn, m_fn,
                tool_llm_fallback, is_retry=True,
            )
            if sol:
                return sol

            msg = _msg("no_more_solutions", lang)
            state.setdefault("history", []).append({"user": user_input, "bot": msg})
            state["awaiting_feedback"] = False
            return {"response": msg, "type": "social"}

    # ══════════════════════════════════════════════════════════════
    # TICKET DEMANDÉ DIRECTEMENT
    # ══════════════════════════════════════════════════════════════
    if fb == "ticket_direct":
        cl = state.get("classification") or classify_fn(state.get("question", user_input))
        state["awaiting_feedback"] = False
        return ticket_fn(state, lang, state.get("question", user_input), cl)

    # ══════════════════════════════════════════════════════════════
    # RÉSOLU
    # ══════════════════════════════════════════════════════════════
    if fb == "yes":
        if state.get("last_fallback"):
            save_pending_fn(**state["last_fallback"])
        msg = m_fn("resolved_ack", lang)
        state.setdefault("history", []).append({"user": user_input, "bot": msg})
        _reset(state)
        return {"response": msg, "type": "social"}

    # ══════════════════════════════════════════════════════════════
    # ÉCHEC — logique des 5 tentatives
    # ══════════════════════════════════════════════════════════════

    if fb == "no":
        state["awaiting_feedback"] = False
        state["failure_count"]     = state.get("failure_count", 0) + 1
        attempts                   = _attempt_count(state)

        print(f"  [FEEDBACK] Échec — tentative {attempts}/{MAX_ATTEMPTS}")

        # Seulement à MAX_ATTEMPTS → message consult équipe
        if attempts >= MAX_ATTEMPTS:
            msg = _msg("consult_team", lang)
            state.setdefault("history", []).append({"user": user_input, "bot": msg})
            state["feedback_state"]    = FeedbackState.CONFIRM_ESC.value
            state["awaiting_feedback"] = True
            return {"response": msg, "type": "social"}

        # Chercher prochaine solution KB
        query = state["question"] if state.get("question") else user_input

        hits = tool_search_kb(
            translate_fn(query, lang),
            exclude_ids = state.get("presented_ids", []),
        )


        if hits:
            state["presented_ids"].extend([h["id"] for h in hits])
            resp = generate_from_kb(
                state["question"], hits, lang,
                history=state.get("history", []),
                is_retry=True,
            )
            if not output_clean_fn(resp):
                resp = m_fn("out_scope", lang)
            state.setdefault("history", []).append({"user": user_input, "bot": resp})
            state["awaiting_feedback"] = True
            cl = state.get("classification") or {}
            return {
                "response": resp,
                "type": "kb",
                "category": cl.get("category"),
                "priority": cl.get("priority"),
            }

        # KB vide → LLM fallback UNE SEULE FOIS, puis continuer à compter
        if not state.get("llm_fallback_used") and tool_llm_fallback:
            cl       = state.get("classification") or {}
            intro    = _msg("trying_llm", lang)   # ← utilise lang correctement
            fallback = tool_llm_fallback(
                question = state.get("question", user_input),
                category = cl.get("category", "IT Support"),
                priority = cl.get("priority", "medium"),
                lang     = lang,             # ← lang passé ici
            )
            if not output_clean_fn(fallback):
                fallback = m_fn("out_scope", lang)
            full_resp = f"{intro}{fallback}"
            state["llm_fallback_used"] = True
            state.setdefault("history", []).append({"user": user_input, "bot": full_resp})
            state["awaiting_feedback"] = True
            return {
                "response"   : full_resp,
                "type"       : "llm_fallback",
                "category"   : cl.get("category"),
                "priority"   : cl.get("priority"),
                "ask_feedback": True,
            }

        # LLM déjà utilisé ET KB vide → propose ticket mais attend MAX_ATTEMPTS
        # Ne pas escalader avant la limite — proposer d'attendre ou ticket
        msg = _msg("confirm_ticket", lang)
        state.setdefault("history", []).append({"user": user_input, "bot": msg})
        state["feedback_state"]    = FeedbackState.CONFIRM_ESC.value
        state["awaiting_feedback"] = True
        return {"response": msg, "type": "social"}

    # ══════════════════════════════════════════════════════════════
    # PARTIEL
    # ══════════════════════════════════════════════════════════════
    if fb == "partial":
        state["awaiting_feedback"] = False
        msg = _msg("ask_partial", lang)
        state.setdefault("history", []).append({"user": user_input, "bot": msg})
        state["question"]      = f"{state.get('question', '')} — {user_input}"
        state["presented_ids"] = []
        state["awaiting_feedback"] = True
        return {"response": msg, "type": "social"}

    # ══════════════════════════════════════════════════════════════
    # RÉSOLU + NOUVEAU PROBLÈME
    # ══════════════════════════════════════════════════════════════
    if fb == "mixed":
        if state.get("last_fallback"):
            save_pending_fn(**state["last_fallback"])
        msg = _msg("ask_mixed_new", lang)
        state.setdefault("history", []).append({"user": user_input, "bot": msg})
        _reset(state)
        return {"response": msg, "type": "social", "expect_new_problem": True}

    # ══════════════════════════════════════════════════════════════
    # ADD DETAIL
    # ══════════════════════════════════════════════════════════════
    if fb == "add_detail":
        state["question"]      = f"{state.get('question', '')} — {user_input}"
        state["awaiting_feedback"] = False
        sol = _get_next_solution(
            state, lang, user_input,
            tool_search_kb, generate_from_kb,
            translate_fn, output_clean_fn, m_fn,
            tool_llm_fallback, is_retry=False,
        )
        if sol:
            return sol
        return None

    # ══════════════════════════════════════════════════════════════
    # REFORMULATION
    # ══════════════════════════════════════════════════════════════
    if fb == "reformulate":
        state["question"]          = user_input
        state["presented_ids"]     = []
        state["failure_count"]     = 0
        state["llm_fallback_used"] = False
        state["awaiting_feedback"] = False
        return None

    return None

