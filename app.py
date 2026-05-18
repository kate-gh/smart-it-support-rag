import json, os, re
from collections import defaultdict
from datetime import datetime
from core.chat_controller import handle_chat
from core.kb_controller import handle_kb_add

from ocr_handler import extract_text_from_image, format_ocr_for_chat

from db import fetchall, fetchone, execute
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from jwt_utils import create_token, require_auth, require_admin
from users_store import get_user, list_users, create_user, update_user, delete_user
from tickets_store import (save_ticket, get_all_tickets,
                            get_tickets_stats, update_ticket_status, delete_ticket)
from pending_store import (save_pending, get_pending,
                            validate_pending, count_pending, delete_pending)
from conversation_store import save_conversation
from feedback_handler import handle_feedback
from action_tools import (tool_reset_password, tool_check_service,
                           tool_system_diagnostic, detect_service_from_text,
                           tool_get_cache_guide)
from it_agent import (
    groq_client, GROQ_MODEL, lang_model, intent_classifier,
    is_understandable, is_prompt_injection,
    translate_to_english, output_is_clean,
    save_to_pending, social_intent,
    tool_search_kb, tool_llm_fallback, generate_from_kb,
    m, detect_language,
)

# ── App setup ─────────────────────────────────────────────
app = Flask(__name__)

CORS(app,
     origins="*",
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=False)

# OPTIONS preflight global
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        from flask import Response
        res = Response()
        res.headers["Access-Control-Allow-Origin"]  = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return res, 200

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri="memory://",
)

MAX_RETRIES = 5

# ── Sessions ──────────────────────────────────────────────
def new_session():
    return {
        "history": [], "lang": "en", "question": None,
        "classification": None, "presented_ids": [],
        "failure_count": 0, "ticket_done": False,
        "awaiting_feedback": False, "last_fallback": None,
        "user_id": "anonymous", "is_logged": False,
        "feedback_state": None, "feedback_ambiguous_count": 0,
        "ticket_refus_count": 0, "llm_fallback_used": False,
        "last_question_type": None,
    }

sessions = defaultdict(new_session)

def reset_problem(state: dict):
    state.update({
        "question": None, "classification": None,
        "presented_ids": [], "failure_count": 0,
        "ticket_done": False, "awaiting_feedback": False,
        "last_fallback": None, "last_question_type": None,
        "feedback_state": None, "feedback_ambiguous_count": 0,
        "llm_fallback_used": False, "ticket_refus_count": 0,
    })

# ── Helpers ───────────────────────────────────────────────
CATEGORIES = [
    "Access Management", "Network & Connectivity",
    "Software & Applications", "Hardware & Peripherals",
    "Security", "Onboarding", "Data & Storage", "IT Support",
]

IT_KEYWORDS = [
    "computer","laptop","pc","screen","monitor","printer","keyboard","mouse",
    "usb","hdmi","battery","wifi","vpn","network","internet","dns","firewall",
    "software","outlook","teams","office","excel","chrome","windows","linux",
    "password","login","account","mfa","2fa","sharepoint","onedrive","virus",
    "malware","phishing","security","backup","ticket","incident","issue",
    "problem","broken","slow","freeze","restart","email","azure","cloud",
    "imprimante","réseau","connexion","mot de passe","compte","accès",
]
""" 
def is_it_related(text: str) -> bool:
    t = text.lower()
    if any(kw in t for kw in IT_KEYWORDS):
        return True
    if len(text.split()) <= 2:
        return False
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content":
                f'Is this an IT support question? "{text}" Answer ONLY "yes" or "no".'}],
            max_tokens=5, temperature=0,
        )
        return r.choices[0].message.content.strip().lower().startswith("yes")
    except Exception:
        return True
"""
def is_it_related(text: str) -> bool:
    t = text.lower().strip()

    # 1. mots-clés IT → OK direct
    if any(kw in t for kw in IT_KEYWORDS):
        return True

    # 2. charabia (ratio voyelles)
    letters = [c for c in t if c.isalpha()]
    if len(letters) >= 5:
        vowels = [c for c in letters if c in 'aeiouyàâéèêëîïôùûü']
        if len(vowels) / len(letters) < 0.2:
            return False

    # 3. texte trop court sans mot-clé → NON
    if len(t.split()) <= 2:
        return False

    # 4. fallback LLM (optionnel)
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": f'Is this an IT support question? "{text}" Answer only yes or no.'
            }],
            max_tokens=5,
            temperature=0,
        )
        return r.choices[0].message.content.strip().lower().startswith("yes")
    except Exception:
        # IMPORTANT : fallback SAFE
        return False

def classify_with_llm(text: str) -> dict:
    cats = ", ".join(f'"{c}"' for c in CATEGORIES)
    prompt = f"""You are an IT support classifier.
Categories: {cats}
Priority: high=blocking, medium=inconvenient, low=minor
Message: "{text}"
Respond ONLY with valid JSON: {{"category": "...", "priority": "..."}}"""
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Classify IT requests. JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=50, temperature=0,
        )
        raw = r.choices[0].message.content.strip()
        match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            cat  = data.get("category", "IT Support")
            prio = data.get("priority", "medium")
            if cat  not in CATEGORIES: cat  = "IT Support"
            if prio not in ("high", "medium", "low"): prio = "medium"
            return {"category": cat, "priority": prio}
    except Exception as e:
        print(f"  [CLASSIFY] Error: {e}")
    return {"category": "IT Support", "priority": "medium"}

def create_ticket(summary, category, priority, user_id="anonymous", source="kb"):
    ticket_id = f"INC{datetime.now().strftime('%Y%m%d%H%M%S')}"
    delay     = "2 heures" if priority == "high" else "24 heures"
    save_ticket(ticket_id=ticket_id, user_id=user_id,
                summary=summary, category=category,
                priority=priority, source=source)
    return {"ticket_id": ticket_id, "delay": delay,
            "category": category, "priority": priority}

LANG_COMMANDS = {
    "fr": ["en français","parle français","réponds en français","français"],
    "en": ["in english","speak english","answer in english","english"],
}
FR_KEY = {"bonjour","salut","bonsoir","coucou","allô","bjr","bsr","slt","cc","oui","non","merci"}
EN_KEY = {"hello","hi","hey","thanks","thank","bye","yes","no","please"}
FEEDBACK_YES = {"y","yes","o","oui","1","yep","ouais","ok","okay"}
FEEDBACK_NO  = {"n","no","non","nope","nan","0","nop"}

def detect_lang_command(text):
    t = text.lower().strip()
    for lang, patterns in LANG_COMMANDS.items():
        if any(p in t for p in patterns):
            return lang
    return None

def detect_language_safe(text, current_lang):
    t = text.lower().strip()
    if t in FR_KEY: return "fr"
    if t in EN_KEY: return "en"
    if len(text.split()) < 2: return current_lang
    detected = detect_language(text)
    return detected if detected in ("fr", "en") else current_lang

def parse_short_feedback(text):
    t = text.lower().strip().rstrip(".")
    if t in FEEDBACK_YES: return "yes"
    if t in FEEDBACK_NO:  return "no"
    return None

def detect_action(text):
    t = text.lower()
    if any(k in t for k in ["reset my password","reset password","forgot password","reset mdp"]):
        return "reset_password"
    if any(k in t for k in ["is teams down","teams not working","outlook down","service down"]):
        return "check_service"
    if any(k in t for k in ["my pc is slow","pc is slow","computer is slow","diagnostic"]):
        return "system_diagnostic"
    if any(k in t for k in ["clear cache","vider cache","nettoyer cache"]):
        return "clear_cache"
    return None

def handle_action(action, user_input, state, lang):
    is_connected = state.get("is_logged", False)
    if action == "reset_password" and not is_connected:
        msg = {"fr": "Veuillez vous connecter pour réinitialiser votre mot de passe.",
               "en": "Please log in first to reset your password."}[lang]
        state["history"].append({"user": user_input, "bot": msg})
        return {"response": msg, "type": "auth_required"}

    if action == "reset_password":
        result = tool_reset_password(username=state["user_id"], user_id=state["user_id"])
        msg = (f"{'Réinitialisation initiée' if lang == 'fr' else 'Password reset initiated'}. "
               f"{result['message']}") if result["success"] else f"Could not reset. {result['message']}"
        state["history"].append({"user": user_input, "bot": msg})
        reset_problem(state)
        return {"response": msg, "type": "action", "action": "reset_password"}

    if action == "check_service":
        service = detect_service_from_text(user_input) or "office365"
        result  = tool_check_service(service)
        msg     = result["message"]
        if result.get("status") in ("down", "timeout", "unreachable"):
            t = create_ticket(user_input, "Network & Connectivity", "high", state["user_id"], "agent_action")
            msg += f"\n\nTicket created: {t['ticket_id']}"
            state["history"].append({"user": user_input, "bot": msg})
            return {"response": msg, "type": "action", "ticket_id": t["ticket_id"]}
        state["history"].append({"user": user_input, "bot": msg})
        return {"response": msg, "type": "action"}

    if action == "system_diagnostic":
        result = tool_system_diagnostic()
        msg = (f"System Diagnostic\nCPU: {result['cpu']}\nRAM: {result['ram']}\n"
               f"Disk: {result['disk']}\nOS: {result['os']}") if result["success"] else result["message"]
        if result.get("warnings"):
            msg += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in result["warnings"])
        state["history"].append({"user": user_input, "bot": msg})
        return {"response": msg, "type": "action"}

    if action == "clear_cache":
        service = detect_service_from_text(user_input) or "browser"
        result  = tool_get_cache_guide(service)
        msg     = result.get("guide") or result.get("message")
        state["history"].append({"user": user_input, "bot": msg})
        return {"response": msg, "type": "action"}

    return None

def ticket_response(state, lang, question, cl):
    t = create_ticket(question, cl["category"], cl["priority"], user_id=state["user_id"])
    msg = f"{m('escalate', lang)}\n{m('ticket_ok', lang, id=t['ticket_id'], delay=t['delay'])}"
    state["history"].append({"user": question, "bot": msg})
    reset_problem(state)
    state["ticket_done"] = True
    return {"response": msg, "type": "ticket", "ticket_id": t["ticket_id"],
            "category": t["category"], "priority": t["priority"], "delay": t["delay"]}

# ── Routes publiques ──────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": GROQ_MODEL})

@app.route("/auth/login", methods=["POST"])
@limiter.limit("10 per minute")  # anti brute force
def login():
    d        = request.get_json() or {}
    username = (d.get("username") or "").strip()
    password = (d.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "missing credentials"}), 400

    user = get_user(username, password)
    if not user:
        return jsonify({"error": "invalid credentials"}), 401

    token = create_token(user["user_id"], user["username"], user["role"])

    return jsonify({
        "user_id" : user["user_id"],
        "username": user["username"],
        "role"    : user["role"],
        "token"   : token,
    })

@app.route("/chat", methods=["POST"])
@limiter.limit("30 per minute")
def chat():
    data       = request.get_json() or {}
    session_id = data.get("session_id", "default")
 
    state = sessions.setdefault(session_id, {
        "history": [], "lang": "fr", "question": None,
        "classification": None, "awaiting_feedback": False,
        "failure_count": 0,
    })
 
    # ── Traitement image OCR ─────────────────────────────────────────────────
    image_base64 = data.get("image_base64")
    image_type   = data.get("image_type", "image/jpeg")
    user_message = (data.get("message") or "").strip()
    lang         = state.get("lang", "en")
 
    if image_base64:
        print(f"  [CHAT] Image reçue, OCR en cours...")
        ocr_text = extract_text_from_image(image_base64, image_type)
 
        if ocr_text:
            # Enrichir le message avec le texte extrait
            data["message"] = format_ocr_for_chat(ocr_text, user_message, lang)
            print(f"  [CHAT] OCR injecté : {len(ocr_text)} chars")
        else:
            # OCR vide = image sans texte (logo, photo)
            no_text_msg = {
                "fr": (
                    f"{user_message}\n\n"
                    "[Capture d'écran reçue — aucun texte détecté. "
                    "Pouvez-vous décrire l'erreur visible ?]"
                ),
                "en": (
                    f"{user_message}\n\n"
                    "[Screenshot received — no text detected. "
                    "Can you describe the visible error?]"
                ),
            }
            data["message"] = no_text_msg.get(lang, no_text_msg["en"])
            print("  [CHAT] OCR vide, demande description manuelle")
 
    # ── Message vide sans image → erreur ────────────────────────────────────
    if not data.get("message"):
        return jsonify({"response": "", "type": "error"})
 
    result = handle_chat(
        data, state, intent_classifier, tool_search_kb, generate_from_kb,
        tool_llm_fallback, classify_with_llm, translate_to_english, m,
        output_is_clean, handle_feedback, save_to_pending, detect_language_safe,
        parse_short_feedback, detect_action, handle_action, is_understandable,
        is_prompt_injection, detect_lang_command, sessions, reset_problem,
        ticket_response, save_conversation, MAX_RETRIES, social_intent, is_it_related,
    )
 
    return jsonify(result)
# ── Routes secondaires ────────────────────────────────────

@app.route("/ticket", methods=["POST"])
@limiter.limit("5 per minute")
def manual_ticket():
    d = request.get_json() or {}
    if not d.get("summary"):
        return jsonify({"error": "summary required"}), 400
    t = create_ticket(d.get("summary"), d.get("category", "IT Support"),
                      d.get("priority", "medium"),
                      user_id=d.get("user_id", "anonymous"), source="manual")
    return jsonify(t)

@app.route("/feedback", methods=["POST"])
def feedback():
    d = request.get_json() or {}
    if d.get("helpful"):
        save_to_pending(
            question=d.get("question", ""), answer=d.get("answer", ""),
            category=d.get("category", "IT Support"), priority=d.get("priority", "medium"),
        )
    return jsonify({"status": "ok"})

@app.route("/kb/add", methods=["POST"])
@require_auth
def add_kb():
    data       = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")

    state   = sessions.get(session_id, {})
    history = state.get("history", [])

    result = handle_kb_add(
        data=data,
        state=state,
        history=history,
        is_it_related=is_it_related
    )

    # gérer erreur tuple (401)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]

    return jsonify(result)

@app.route("/reset", methods=["POST"])
def reset():
    sid = (request.get_json() or {}).get("session_id", "default")
    if sid in sessions:
        sessions[sid] = new_session()
    return jsonify({"status": "reset"})

# ── Routes Admin (toutes protégées par @require_admin) ────

@app.route("/admin/stats", methods=["GET"])
@require_admin
def admin_stats():
    try:
        stats   = get_tickets_stats()
        pending = count_pending()
        active  = len([s for s in sessions.values() if s.get("history")])
        return jsonify({
            "tickets_total"  : stats.get("total", 0),
            "tickets_open"   : stats.get("open", 0),
            "pending_kb"     : pending,
            "active_sessions": active,
            "by_category"    : stats.get("by_category", {}),
            "by_priority"    : stats.get("by_priority", {}),
        })
    except Exception as e:
        print(f"[STATS] {e}")
        return jsonify({"tickets_total": 0, "tickets_open": 0,
                        "pending_kb": 0, "active_sessions": 0,
                        "by_category": {}, "by_priority": {}})

@app.route("/admin/tickets", methods=["GET"])
@require_admin
def admin_tickets():
    try:
        return jsonify(get_all_tickets(limit=100))
    except Exception as e:
        return jsonify([])

@app.route("/admin/tickets/<ticket_id>/status", methods=["PUT"])
@require_admin
def update_ticket(ticket_id):
    d      = request.get_json() or {}
    status = d.get("status", "")
    if status not in ("open", "in_progress", "resolved", "closed"):
        return jsonify({"error": "invalid status"}), 400
    ok = update_ticket_status(ticket_id, status)
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/admin/tickets/<ticket_id>", methods=["DELETE"])
@require_admin
def admin_delete_ticket(ticket_id):
    ok = delete_ticket(ticket_id)
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/admin/pending", methods=["GET"])
@require_admin
def admin_pending():
    try:
        return jsonify(get_pending(only_unvalidated=True))
    except Exception as e:
        return jsonify([])

@app.route("/admin/pending/validate", methods=["POST"])
@require_admin
def admin_validate_pending():
    try:
        d        = request.get_json() or {}
        question = d.get("question", "")
        action   = d.get("action")
        if action not in ("approve", "reject"):
            return jsonify({"error": "invalid action"}), 400

        if action == "approve":
            rows = get_pending(only_unvalidated=True)
            item = next((r for r in rows
                         if r["question"].lower() == question.lower()), None)
            if item:
                validate_pending(question, "approve")
                _ingest_to_chroma(item["question"], item["answer"],
                                   item.get("category", "IT Support"),
                                   item.get("priority", "medium"))
        else:
            validate_pending(question, "reject")

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/admin/pending/<int:pid>", methods=["DELETE"])
@require_admin
def admin_delete_pending(pid):
    ok = delete_pending(pid)
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/admin/users", methods=["GET"])
@require_admin
def admin_users():
    try:
        return jsonify(list_users())
    except Exception as e:
        return jsonify([])

@app.route("/admin/users/create", methods=["POST"])
@require_admin
def admin_create_user():
    d        = request.get_json() or {}
    username = (d.get("username") or "").strip()
    password = (d.get("password") or "").strip()

    # Validation
    if not username or len(username) < 2:
        return jsonify({"status": "error", "message": "Username too short"}), 400
    if not password or len(password) < 4:
        return jsonify({"status": "error", "message": "Password too short (min 4 chars)"}), 400

    ok = create_user(
        username=username, password=password,
        role=d.get("role", "user"),
        full_name=d.get("full_name", ""),
        email=d.get("email", ""),
        department=d.get("department", ""),
        phone=d.get("phone", ""),
        location=d.get("location", ""),
    )
    if not ok:
        return jsonify({"status": "error", "message": "Username or email already exists"}), 409
    return jsonify({"status": "ok"})

@app.route("/admin/users/<user_id>", methods=["PUT"])
@require_admin
def admin_update_user(user_id):
    d = request.get_json() or {}
    # Empêcher de changer le role de l'admin principal
    if user_id == "1" and d.get("role") != "admin":
        return jsonify({"status": "error", "message": "Cannot change main admin role"}), 403
    ok = update_user(user_id, d)
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/admin/users/<user_id>", methods=["DELETE"])
@require_admin
def admin_delete_user(user_id):
    if user_id == "1":
        return jsonify({"status": "error", "message": "Cannot delete main admin"}), 403
    ok = delete_user(user_id)
    return jsonify({"status": "ok" if ok else "error"})

# ── Ingest Chroma ─────────────────────────────────────────

def clean_text(text):
    if not isinstance(text, str): return ""
    return re.sub(r"\s+", " ", text.strip().replace("\n", " "))

def _ingest_to_chroma(question, answer, category, priority):
    try:
        from it_agent import embedding_model, collection
        question = clean_text(question)
        answer   = clean_text(answer)
        if not question or not answer or len(question.split()) < 3:
            return
        lang        = detect_language(question)
        question_en = translate_to_english(question, lang)
        q_emb       = embedding_model.encode(question_en).tolist()

        existing = collection.query(query_embeddings=[q_emb], n_results=1,
                                    where={"chunk_type": {"$eq": "question"}})
        if existing["distances"] and existing["distances"][0]:
            if 1 - existing["distances"][0][0] > 0.92:
                return

        base_id   = f"user_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        base_meta = {"answer": answer[:500], "category": category or "IT Support",
                     "priority": priority or "medium", "source": "user_validated"}

        collection.add(ids=[f"{base_id}_a"], documents=[question_en],
                       embeddings=[q_emb],
                       metadatas=[{**base_meta, "chunk_type": "question"}])

        enriched = f"Issue: {question_en} Context: {category} Resolution: {answer[:200]}"
        emb_b    = embedding_model.encode(enriched).tolist()
        collection.add(ids=[f"{base_id}_b"], documents=[enriched],
                       embeddings=[emb_b],
                       metadatas=[{**base_meta, "chunk_type": "enriched"}])
        print(f"[CHROMA] Added: {base_id}")
    except Exception as e:
        print(f"[CHROMA ERROR] {e}")

@app.route("/user/conversations", methods=["GET"])
@require_auth
def user_conversations():
    """Liste des conversations groupées par session pour l'utilisateur connecté."""
    # require_auth doit injecter user_id dans request — adapte selon ton jwt_utils
    user_id = request.current_user["user_id"]

    rows = fetchall("""
        SELECT 
            session_id,
            MIN(question)    AS first_question,
            MAX(custom_title) AS custom_title,
            MAX(created_at)  AS last_activity,
            COUNT(*)         AS message_count,
            MAX(resolved)    AS resolved,
            GROUP_CONCAT(DISTINCT source SEPARATOR ',') AS sources
        FROM conversations
        WHERE user_id = %s
          AND question IS NOT NULL
          AND LENGTH(TRIM(question)) > 0
        GROUP BY session_id
        ORDER BY last_activity DESC
        LIMIT 30
    """, (user_id,))

    # Construire un titre propre depuis first_question
    result = []
    for r in rows:
        q = r.get("first_question") or ""
        title = r.get("custom_title")

        if not title:
            title = " ".join(q.split()[:7])

            if len(q.split()) > 7:
                title += "..."

        # Source principale (kb > llm_fallback > ticket)
        sources = r.get("sources", "") or ""
        if "kb" in sources:
            res_source = "kb"
        elif "llm" in sources:
            res_source = "llm"
        else:
            res_source = "other"

        result.append({
            "session_id"    : r["session_id"],
            "title"         : title,
            "last_activity" : str(r["last_activity"]),
            "message_count" : r["message_count"],
            "resolved"      : bool(r["resolved"]),
            "source"        : res_source,
        })

    return jsonify(result)


@app.route("/user/conversations/<session_id>", methods=["GET"])
@require_auth
def user_conversation_detail(session_id):
    """Détail d'une conversation — tous les messages."""
    user_id = request.current_user["user_id"]

    rows = fetchall("""
        SELECT question, answer, source, resolved, created_at
        FROM conversations
        WHERE session_id = %s
          AND user_id    = %s
        ORDER BY created_at ASC
    """, (session_id, user_id))

    return jsonify(rows)

@app.route("/user/conversations/<session_id>/rename", methods=["PUT"])
@require_auth
def rename_conversation(session_id):

    user_id = request.current_user["user_id"]

    data = request.get_json() or {}

    title = data.get("title","").strip()

    if not title:
        return jsonify({"error":"title required"}),400

    execute("""
        UPDATE conversations
        SET custom_title=%s
        WHERE session_id=%s
        AND user_id=%s
    """,(title,session_id,user_id))

    return jsonify({"status":"ok"})

@app.route("/user/conversations/<session_id>", methods=["DELETE"])
@require_auth
def delete_conversation(session_id):

    user_id=request.current_user["user_id"]

    execute("""

        DELETE FROM conversations
        WHERE session_id=%s
        AND user_id=%s

    """,(session_id,user_id))

    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)