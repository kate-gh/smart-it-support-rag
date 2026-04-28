# users_store.py
import hashlib
from db import execute, fetchall, fetchone

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(username: str, password: str) -> dict | None:
    rows = fetchall(
        """SELECT user_id, username, role, full_name, email, department,
                  phone, location, is_active
           FROM users
           WHERE username=%s AND password_hash=%s AND is_active=1""",
        (username, _hash(password)),
    )
    if not rows:
        return None
    # Mettre à jour last_login
    execute(
        "UPDATE users SET last_login=NOW() WHERE username=%s",
        (username,),
    )
    return rows[0]

def list_users() -> list:
    return fetchall(
        """SELECT user_id, username, role, full_name, email,
                  department, phone, location, is_active,
                  last_login, created_at
           FROM users ORDER BY id""",
    )

def create_user(username: str, password: str, role: str = "user",
                full_name: str = "", email: str = "",
                department: str = "", phone: str = "",
                location: str = "") -> bool:
    # Validation
    if not username or len(username) < 2:
        return False
    if not password or len(password) < 4:
        return False
    if role not in ("user", "admin"):
        role = "user"

    try:
        # Vérifier doublon username
        existing = fetchone(
            "SELECT id FROM users WHERE username=%s", (username,)
        )
        if existing:
            return False

        # Vérifier doublon email si fourni
        if email:
            existing_email = fetchone(
                "SELECT id FROM users WHERE email=%s", (email,)
            )
            if existing_email:
                return False

        rows = fetchall(
            "SELECT MAX(CAST(user_id AS UNSIGNED)) AS mx FROM users",
        )
        next_id = str((rows[0]["mx"] or 0) + 1) if rows else "10"

        execute(
            """INSERT INTO users
               (user_id, username, password_hash, role,
                full_name, email, department, phone, location, is_active)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1)""",
            (next_id, username, _hash(password), role,
             full_name or "", email or "",
             department or "", phone or "", location or ""),
        )
        return True
    except Exception as e:
        print(f"  [DB] create_user error: {e}")
        return False

def update_user(user_id: str, data: dict) -> bool:
    try:
        fields = []
        values = []

        # Champs texte simples
        for col in ["username", "role", "full_name", "email",
                    "department", "phone", "location"]:
            if col in data and data[col] is not None:
                # Validation role
                if col == "role" and data[col] not in ("user", "admin"):
                    continue
                fields.append(f"{col}=%s")
                values.append(data[col])

        # is_active (boolean)
        if "is_active" in data:
            fields.append("is_active=%s")
            values.append(1 if data["is_active"] else 0)

        # Nouveau mot de passe (optionnel)
        if data.get("password") and len(data["password"]) >= 4:
            fields.append("password_hash=%s")
            values.append(_hash(data["password"]))

        if not fields:
            return True

        values.append(user_id)
        execute(
            f"UPDATE users SET {', '.join(fields)} WHERE user_id=%s",
            tuple(values),
        )
        return True
    except Exception as e:
        print(f"[DB] update_user error: {e}")
        return False

def delete_user(user_id: str) -> bool:
    try:
        # Empêcher suppression du compte admin principal
        u = fetchone(
            "SELECT username FROM users WHERE user_id=%s", (user_id,)
        )
        if u and u["username"] == "admin":
            return False
        execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        return True
    except Exception as e:
        print(f"[DB] delete_user error: {e}")
        return False
