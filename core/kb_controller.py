from kafka_producer import publish_kb_update


def handle_kb_add(data: dict, state: dict, history: list, is_it_related) -> dict:
    """
    Valide et route un Q/R vers Kafka (score ≥ 3) ou pending_kb (score < 3).
    Retourne un dict (pas de jsonify ici).
    """
    user_id    = data.get("user_id")
    user_score = int(data.get("user_score", 3))

    if not user_id:
        # L'appelant doit gérer le code HTTP 401
        return ({"error": "unauthorized"}, 401)

    # ── Patterns de feedback à ignorer ───────────────────────────────
    FEEDBACK_PATTERNS = {
        "no", "non", "yes", "oui", "nope", "nan",
        "it didn't work", "it didn't", "ça n'a pas marché",
        "toujours pas", "still not working", "same issue",
        "didn't work", "not working", "not fixed",
    }

    question = None
    answer   = None

    # Parcourir l'historique à l'envers pour trouver la dernière vraie paire Q/R
    for i in range(len(history) - 1, -1, -1):
        turn     = history[i]
        user_msg = turn.get("user", "").strip().lower()
        bot_msg  = turn.get("bot", "")

        is_feedback = (
            user_msg in FEEDBACK_PATTERNS
            or len(user_msg.split()) < 3
            or any(user_msg.startswith(p) for p in ["no ", "non ", "yes ", "oui "])
        )
        bot_is_solution = len(bot_msg.split()) > 15

        if not is_feedback and bot_is_solution:
            question = turn.get("user", "").strip()
            answer   = bot_msg
            break

    # Fallback sur state["question"] si rien trouvé dans l'historique
    if not question:
        question = state.get("question")

    if not answer and not question:
        return {"status": "ignored", "reason": "no valid Q/A found in history"}

    print(f"[KB/ADD] question='{question}' | answer={bool(answer)} | score={user_score}")

    # ── Validations ───────────────────────────────────────────────────
    if not question or not answer:
        return {"status": "ignored", "reason": "missing data"}

    if len(question.split()) < 3:
        return {"status": "ignored", "reason": "question too short"}

    BAD_QUESTIONS = {
        "no", "non", "it didn't", "didn't work", "nope", "yes", "oui",
        "it didn't work", "ça n'a pas marché", "toujours pas",
        "still not working", "same issue",
    }
    if question.lower().strip() in BAD_QUESTIONS:
        return {"status": "ignored", "reason": "not a real question"}

    if not is_it_related(question):
        return {"status": "ignored", "reason": "not IT related"}

    category = state.get("classification", {}).get("category", "IT Support")
    priority = state.get("classification", {}).get("priority", "medium")

    # ── Score ≥ 3 → Kafka → Chroma ───────────────────────────────────
    if user_score >= 3:
        publish_kb_update(question, answer, category, priority)
        return {
            "status"       : "approved",
            "score"        : user_score,
            "message"      : "Added to knowledge base",
            "question_used": question[:80],
        }

    # ── Score < 3 → pending (review admin) ───────────────────────────
    from db import execute
    execute(
        """
        INSERT INTO pending_kb
            (question, answer, category, priority, user_id, user_score, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """,
        (question, answer, category, priority, user_id, user_score),
    )
    return {"status": "pending", "score": user_score}