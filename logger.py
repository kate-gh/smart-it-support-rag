"""

Enregistre chaque ticket traité par le chatbot dans un CSV.
Ce CSV sera importé dans Power BI pour le dashboard analytique.

Utilisation dans rag_chatbot_V4.py :
    from logger import log_ticket
    log_ticket(question, lang, intent, difficulty, priority, auto_resolve, resolved=True/False)
"""

import csv
import os
from datetime import datetime

LOG_FILE = "tickets_log.csv"

HEADERS = [
    "timestamp",
    "date",
    "heure",
    "message",
    "langue",
    "intent",
    "difficulte",
    "priorite",
    "auto_resolve",
    "resolu"
]


def init_log():
    """Crée le fichier CSV avec les headers s'il n'existe pas encore."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
        print(f"[Logger] Fichier créé : {LOG_FILE}")


def log_ticket(message, langue, intent, difficulte, priorite, auto_resolve, resolu=None):
    """
    Enregistre un ticket dans le CSV.

    Paramètres:
        message      (str)  : question de l'utilisateur
        langue       (str)  : 'fr' ou 'en'
        intent       (str)  : intent détecté
        difficulte   (str)  : prédiction du modèle difficulty_model
        priorite     (str)  : prédiction du modèle priority_model
        auto_resolve (str)  : prédiction du modèle auto_resolve_model
        resolu       (bool) : True si l'utilisateur a dit oui (résolu), False si non
    """
    init_log()

    now = datetime.now()

    row = {
        "timestamp":    now.strftime("%Y-%m-%d %H:%M:%S"),
        "date":         now.strftime("%Y-%m-%d"),
        "heure":        now.strftime("%H:%M"),
        "message":      message[:200],  # tronquer pour éviter les lignes trop longues
        "langue":       langue,
        "intent":       intent,
        "difficulte":   difficulte,
        "priorite":     priorite,
        "auto_resolve": auto_resolve,
        "resolu":       resolu if resolu is not None else "en_attente"
    }

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow(row)