from db import execute

def save_conversation(session_id: str, user_id: str,
                      question: str, answer: str,
                      source: str, resolved: bool = False):
    try:
        execute("""
            INSERT INTO conversations
            (session_id, user_id, question, answer, source, resolved)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (session_id, user_id, question[:1000],
              answer[:2000], source, int(resolved)))
    except Exception as e:
        print(f"[CONV] Error: {e}")

def get_user_history(user_id: str, limit: int = 10):
    return execute("""
        SELECT question, answer, source, resolved, created_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (user_id, limit), fetch=True) or []

def get_resolution_stats():
    return execute("""
        SELECT 
            source,
            COUNT(*) as total,
            SUM(resolved) as resolved_count,
            ROUND(AVG(resolved) * 100, 1) as resolution_rate
        FROM conversations
        GROUP BY source
        ORDER BY total DESC
    """, fetch=True) or []