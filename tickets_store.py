# tickets_store.py — remplace l'ancien
from db import execute
from datetime import datetime

def save_ticket(ticket_id, user_id, summary, category, priority, source="kb"):
    execute(
        """INSERT INTO tickets
           (ticket_id, user_id, summary, category, priority, source)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (ticket_id, user_id, summary, category, priority, source),
    )

def get_all_tickets(limit: int = 100) -> list:
    return execute(
        "SELECT * FROM tickets ORDER BY created_at DESC LIMIT %s",
        (limit,), fetch=True,
    )

def get_tickets_stats() -> dict:
    total    = execute("SELECT COUNT(*) AS n FROM tickets",          fetch=True)[0]["n"]
    open_cnt = execute("SELECT COUNT(*) AS n FROM tickets WHERE status='open'", fetch=True)[0]["n"]
    by_cat   = execute(
        "SELECT category, COUNT(*) AS cnt FROM tickets GROUP BY category ORDER BY cnt DESC",
        fetch=True,
    )
    by_prio  = execute(
        "SELECT priority, COUNT(*) AS cnt FROM tickets GROUP BY priority",
        fetch=True,
    )
    return {
        "total"      : total,
        "open"       : open_cnt,
        "by_category": {r["category"]: r["cnt"] for r in by_cat},
        "by_priority": {r["priority"]: r["cnt"] for r in by_prio},
    }

def update_ticket_status(ticket_id: str, status: str) -> bool:
    try:
        execute(
            "UPDATE tickets SET status=%s WHERE ticket_id=%s",
            (status, ticket_id),
        )
        return True
    except Exception as e:
        print("[DB] update_ticket_status error:", e)
        return False


def delete_ticket(ticket_id: str) -> bool:
    try:
        execute("DELETE FROM tickets WHERE ticket_id=%s", (ticket_id,))
        return True
    except Exception as e:
        print("[DB] delete_ticket error:", e)
        return False