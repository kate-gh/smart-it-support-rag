"""
core/chat_controller.py
Contient handle_chat() — même logique que le /chat original dans app.py.
Reçoit toutes ses dépendances par injection pour rester découplé.
"""


def handle_chat(
    data,
    state,
    intent_classifier,
    tool_search_kb,
    generate_from_kb,
    tool_llm_fallback,
    classify_with_llm,
    translate_to_english,
    m,
    output_is_clean,
    handle_feedback,
    save_to_pending,
    detect_language_safe,
    parse_short_feedback,
    detect_action,
    handle_action,
    is_understandable,
    is_prompt_injection,
    detect_lang_command,
    sessions,
    reset_problem,
    ticket_response,
    save_conversation,
    MAX_RETRIES,
    social_intent,
    is_it_related,
) -> dict:
    """
    Traite un message utilisateur et retourne un dict (pas de jsonify ici).
    Toute la logique est identique à l'original app.py /chat route.
    """
    from it_agent import detect_language  # import local pour éviter les imports circulaires

    # ── Extraction des données ────────────────────────────────────────
    user_input  = (data.get("message") or "").strip()
    session_id  = data.get("session_id", "default")
    user_id     = data.get("user_id")
    is_logged   = data.get("is_logged", False)
    client_lang = data.get("lang")

    if not user_input:
        return {"response": "", "type": "error"}

    state["user_id"]   = user_id or session_id
    state["is_logged"] = is_logged

    if client_lang in ("fr", "en"):
        state["lang"] = client_lang
    lang = state["lang"]

    # ── Guardrails ────────────────────────────────────────────────────
    if not is_understandable(user_input):
        return {"response": m("unclear", lang), "type": "error"}
    if is_prompt_injection(user_input):
        return {"response": m("injection", lang), "type": "error"}

    if (not state.get("awaiting_feedback")
            and not state.get("question")
            and not state.get("last_question_type") == "confirmation"):

        # Mots courts = feedback ou salutation → ne pas bloquer
        is_short = len(user_input.split()) <= 2

        if not is_short and not is_it_related(user_input):
            msg = m("out_scope", lang)
            state["history"].append({"user": user_input, "bot": msg})
            return {"response": msg, "type": "out_scope"}

    # ── Commande de langue explicite ──────────────────────────────────
    lang_cmd = detect_lang_command(user_input)
    if lang_cmd:
        state["lang"] = lang_cmd
        lang = lang_cmd
        ack = {
            "fr": "Bien sûr ! Je répondrai maintenant en français. Quel est votre problème IT ?",
            "en": "Sure! I'll now respond in English. What is your IT issue?",
        }[lang_cmd]
        state["history"].append({"user": user_input, "bot": ack})
        return {"response": ack, "type": "social", "lang": lang_cmd}

    # ── Détection de langue ───────────────────────────────────────────
    detected = detect_language_safe(user_input, state["lang"])
    if len(user_input.split()) > 3:
        state["lang"] = detected
    lang = state["lang"]

    # ── Intent — un seul calcul ───────────────────────────────────────
    if state.get("last_question_type") == "confirmation":
        short = parse_short_feedback(user_input)
        if short == "yes":
            intent_result = {"intent": "resolved", "confidence": 1.0, "method": "rule"}
        elif short == "no":
            intent_result = {"intent": "failure",  "confidence": 1.0, "method": "rule"}
        else:
            intent_result = intent_classifier.classify(
                text=user_input,
                history=state["history"],
                current_problem=state["question"],
            )
    else:
        intent_result = intent_classifier.classify(
            text=user_input,
            history=state["history"],
            current_problem=state["question"],
        )

    intent   = intent_result["intent"]
    short_fb = parse_short_feedback(user_input)

    # Utiliser modèle si confiant ; fallback simple si incertain et question active
    if intent_result["confidence"] >= 0.75:
        intent = intent_result["intent"]
    elif short_fb and state.get("question"):
        intent = "resolved" if short_fb == "yes" else "failure"

    # ── Action directe (reset_password, check_service, diagnostic…) ───
    action = detect_action(user_input)
    if action:
        result = handle_action(action, user_input, state, lang)
        if result:
            return result

    # Failure sans question active → demander de préciser
    if intent == "failure" and not state.get("question"):
        return {"response": m("clarify", lang), "type": "social"}

    # ── Gestion du feedback en attente ───────────────────────────────
    if state.get("awaiting_feedback"):

        short_fb   = parse_short_feedback(user_input)
        new_intent = intent_classifier.classify(
            text=user_input,
            history=state["history"],
            current_problem=state.get("question"),
        )

        # 1. Feedback court explicite (yes / no)
        if short_fb in ("yes", "no"):
            forced_intent  = "resolved" if short_fb == "yes" else "failure"
            forced_result  = {"intent": forced_intent, "confidence": 1.0, "method": "rule"}
            fb_response    = handle_feedback(
                user_input        = user_input,
                state             = state,
                lang              = lang,
                intent_classifier = intent_classifier,
                intent_result     = forced_result,
                tool_search_kb    = tool_search_kb,
                generate_from_kb  = generate_from_kb,
                classify_fn       = classify_with_llm,
                ticket_fn         = ticket_response,
                translate_fn      = translate_to_english,
                save_pending_fn   = save_to_pending,
                output_clean_fn   = output_is_clean,
                m_fn              = m,
                tool_llm_fallback = tool_llm_fallback,
            )
            if fb_response is not None:
                return fb_response

        # 2. Nouvelle question détectée → reset et continuer normalement
        elif new_intent["intent"] in ("new_question", "new_problem"):
            print("[chat_controller] Nouvelle question détectée → reset")
            reset_problem(state)

        # 3. Laisser handle_feedback décider
        else:
            fb_response = handle_feedback(
                user_input        = user_input,
                state             = state,
                lang              = lang,
                intent_classifier = intent_classifier,
                intent_result     = intent_result,
                tool_search_kb    = tool_search_kb,
                generate_from_kb  = generate_from_kb,
                classify_fn       = classify_with_llm,
                ticket_fn         = ticket_response,
                translate_fn      = translate_to_english,
                save_pending_fn   = save_to_pending,
                output_clean_fn   = output_is_clean,
                m_fn              = m,
                tool_llm_fallback = tool_llm_fallback,
            )
            if fb_response is not None:
                return fb_response
            reset_problem(state)

    # ── Social ────────────────────────────────────────────────────────
    if intent == "social":
        lang          = detect_language_safe(user_input, state["lang"])
        state["lang"] = lang
        si  = social_intent(user_input, lang=lang)
        key = si if si else "greet"
        msg = m(key, lang)
        state["history"].append({"user": user_input, "bot": msg})
        return {"response": msg, "type": "social"}

    # ── Demande de ticket ─────────────────────────────────────────────
    if intent == "ticket_request":
        if not state.get("is_logged"):
            msg = {
                "fr": (
                    "🔒 Connectez-vous pour créer un ticket automatique.\n\n"
                    "Ou contactez directement l'équipe IT :\n"
                    "• Email : it-support@entreprise.com\n"
                    "• Tél   : +212 5XX-XXXXXX\n"
                    "• Bureau : Bâtiment A, Salle 101"
                ),
                "en": (
                    "🔒 Log in to create a ticket automatically.\n\n"
                    "Or contact the IT team directly:\n"
                    "• Email : it-support@company.com\n"
                    "• Phone : +212 5XX-XXXXXX\n"
                    "• Office: Building A, Room 101"
                ),
            }[lang]
            state["history"].append({"user": user_input, "bot": msg})
            return {"response": msg, "type": "auth_required"}

        cl = state["classification"] or classify_with_llm(user_input)
        q  = state["question"] or user_input
        return ticket_response(state, lang, q, cl)

    # ── Problème résolu ───────────────────────────────────────────────
    if intent == "resolved" and state["question"]:
        if state.get("last_fallback"):
            save_to_pending(**state["last_fallback"])

        msg = m("resolved_ack", lang)
        state["history"].append({"user": user_input, "bot": msg})
        reset_problem(state)
        return {"response": msg, "type": "social"}

    # ── Gestion des failures ──────────────────────────────────────────
    if intent == "failure" and state["question"]:
        state["failure_count"] += 1
        print(f"[DEBUG] failure_count = {state['failure_count']}")

        # Stop après MAX_RETRIES
        if state["failure_count"] >= MAX_RETRIES:
            if not state.get("is_logged"):
                msg = {
                    "fr": "⚠️ Nous n'avons plus de solutions. Veuillez contacter le support IT ou vous connecter.",
                    "en": "⚠️ No more solutions available. Please contact IT support or log in.",
                }[lang]
                state["history"].append({"user": user_input, "bot": msg})
                reset_problem(state)
                return {"response": msg, "type": "auth_required"}

            cl = state["classification"] or classify_with_llm(state["question"])
            return ticket_response(state, lang, state["question"], cl)

        # Phase KB (2 premières tentatives)
        hits = tool_search_kb(
            state["question"],
            exclude_ids=state["presented_ids"],
        )

        # Forcer LLM après 2 tentatives KB
        if state["failure_count"] > 2:
            hits = []

        if hits:
            state["presented_ids"].extend([h["id"] for h in hits])
            response = generate_from_kb(
                state["question"], hits, lang,
                history=state["history"], is_retry=True,
            )
            state["history"].append({"user": user_input, "bot": response})
            state["awaiting_feedback"] = True
            save_conversation(
                session_id = session_id,
                user_id    = state["user_id"],
                question   = state["question"],
                answer     = response,
                source     = "kb_retry",
                resolved   = False,
            )
            return {"response": response, "type": "kb"}

        # Phase LLM
        if state["failure_count"] <= 5:
            fallback = tool_llm_fallback(
                question    = state["question"],
                category    = state["classification"]["category"],
                priority    = state["classification"]["priority"],
                lang        = lang,
                attempt_num = state["failure_count"],
            )
            state["history"].append({"user": user_input, "bot": fallback})
            state["awaiting_feedback"] = True
            save_conversation(
                session_id = session_id,
                user_id    = state["user_id"],
                question   = state["question"],
                answer     = fallback,
                source     = "llm_retry",
                resolved   = False,
            )
            return {"response": fallback, "type": "llm_fallback"}

    # ── Intent ambigu ─────────────────────────────────────────────────
    if intent == "ambiguous":
        return {"response": m("clarify", lang), "type": "clarification"}

    # ── Nouvelle question IT ──────────────────────────────────────────
    classification = classify_with_llm(user_input)
    hits           = tool_search_kb(user_input)

    state["question"]          = user_input
    state["classification"]    = classification
    state["presented_ids"]     = [h["id"] for h in hits] if hits else []
    state["failure_count"]     = 0
    state["ticket_done"]       = False
    state["awaiting_feedback"] = False
    state["llm_fallback_used"] = False

    # Seuil de confiance minimal pour la KB
    hits = [h for h in hits if h.get("score", 0) > 0.45]

    if not hits:
        # Vérification supplémentaire avant LLM
        if not is_understandable(user_input) or len(user_input.split()) < 2:
            msg = m("unclear", lang)
            state["history"].append({"user": user_input, "bot": msg})
            return {"response": msg, "type": "error"}

        fallback = tool_llm_fallback(
            question = user_input,
            category = classification["category"],
            priority = classification["priority"],
            lang     = lang,
        )
        if len(fallback.split()) < 10 or not output_is_clean(fallback):
            fallback = m("out_scope", lang)

        state["history"].append({"user": user_input, "bot": fallback})
        state["awaiting_feedback"] = True
        state["llm_fallback_used"] = True
        state["last_fallback"]     = {
            "question": user_input,
            "answer"  : fallback,
            "category": classification["category"],
            "priority": classification["priority"],
        }
        save_conversation(
            session_id = session_id,
            user_id    = state["user_id"],
            question   = user_input,
            answer     = fallback,
            source     = "llm",
            resolved   = False,
        )
        return {
            "response"    : fallback,
            "type"        : "llm_fallback",
            "category"    : classification["category"],
            "priority"    : classification["priority"],
            "ask_feedback": True,
        }

    # KB trouvée → générer réponse
    response = generate_from_kb(user_input, hits, lang, history=state["history"])
    if not output_is_clean(response):
        response = m("out_scope", lang)

    state["history"].append({"user": user_input, "bot": response})
    state["awaiting_feedback"] = True

    save_conversation(
        session_id = session_id,
        user_id    = state["user_id"],
        question   = user_input,
        answer     = response,
        source     = "kb",
        resolved   = False,
    )
    return {
        "response" : response,
        "type"     : "kb",
        "category" : classification["category"],
        "priority" : classification["priority"],
    }