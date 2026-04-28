import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

_pool = pooling.MySQLConnectionPool(
    pool_name      = "it_agent_pool",
    pool_size      = 5,
    host           = os.environ.get("MYSQL_HOST",     "localhost"),
    user           = os.environ.get("MYSQL_USER",     "root"),
    password       = os.environ.get("MYSQL_PASSWORD", ""),
    database       = os.environ.get("MYSQL_DATABASE", "it_agent_db"),
    charset        = "utf8mb4",
    autocommit     = True,
)

def get_conn():
    return _pool.get_connection()

def fetchall(query: str, params: tuple = ()):
    return execute(query, params, fetch=True)


def fetchone(query: str, params: tuple = ()):
    rows = execute(query, params, fetch=True)
    return rows[0] if rows else None

def execute(query: str, params: tuple = (), fetch: bool = False):
    conn = get_conn()
    cur  = conn.cursor(dictionary=True)
    cur.execute(query, params)
    result = cur.fetchall() if fetch else None
    cur.close()
    conn.close()
    return result