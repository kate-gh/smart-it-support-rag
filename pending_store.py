# pending_store.py — remplace pending_kb.json
from db import execute
from datetime import datetime

def save_pending(question: str, answer: str, category: str,
                 priority: str, user_id: str, user_score: int) -> None:

    # éviter doublon
    existing = execute(
        "SELECT id FROM pending_kb WHERE question=%s", (question,), fetch=True
    )
    if existing:
        return

    execute(
        """INSERT INTO pending_kb
           (question, answer, category, priority, user_id, user_score, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (question, answer, category, priority, user_id, user_score, "pending"),
    )

def get_pending(only_unvalidated: bool = True) -> list:
    if only_unvalidated:
        return execute(
            "SELECT * FROM pending_kb WHERE status = 'pending' ORDER BY created_at DESC",
            fetch=True,
        )
    return execute("SELECT * FROM pending_kb ORDER BY created_at DESC", fetch=True)


def validate_pending(question: str, action: str) -> bool:
    if action == "approve":
        execute(
            "UPDATE pending_kb SET status='approved' WHERE question=%s",
            (question,),
        )
    elif action == "reject":
        execute(
            "UPDATE pending_kb SET status='rejected' WHERE question=%s",
            (question,),
        )
    return True



def delete_pending(id: int) -> bool:
    try:
        execute("DELETE FROM pending_kb WHERE id=%s", (id,))
        return True
    except Exception as e:
        print("[DB] delete_pending error:", e)
        return False

def count_pending() -> int:
    rows = execute(
        "SELECT COUNT(*) AS n FROM pending_kb WHERE status = 'pending'",
        fetch=True
    )
    return rows[0]["n"] if rows else 0