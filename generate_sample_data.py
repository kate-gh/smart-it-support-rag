"""
generate_sample_data.py
-----------------------
Génère des données réalistes pour tester Power BI
avant d'avoir suffisamment de vraies conversations.
Lance une seule fois, puis utilise les vraies données.
"""

import csv
import random
from datetime import datetime, timedelta

LOG_FILE = "tickets_log.csv"

HEADERS = [
    "timestamp", "date", "heure", "message",
    "langue", "intent", "difficulte", "priorite", "auto_resolve", "resolu"
]

MESSAGES_FR = [
    "Mon imprimante ne fonctionne plus",
    "Impossible de me connecter au VPN",
    "Mon écran est noir au démarrage",
    "Outlook ne répond plus",
    "Je n'arrive pas à accéder à Internet",
    "Mon ordinateur est très lent",
    "Erreur 404 sur l'application interne",
    "Mot de passe oublié",
    "Le réseau wifi est instable",
    "Fichiers supprimés par erreur"
]

MESSAGES_EN = [
    "Printer not responding",
    "Cannot connect to VPN",
    "Blue screen error on startup",
    "Outlook keeps crashing",
    "No internet connection",
    "Laptop running very slow",
    "Cannot access the shared drive",
    "Password reset required",
    "WiFi disconnecting randomly",
    "Email attachment not opening"
]

PRIORITES    = ["high", "medium", "low"]
DIFFICULTES  = ["easy", "medium", "hard"]
AUTO_RESOLVE = ["True", "False"]
RESOLUS      = ["True", "False", "en_attente"]

# Générer 200 entrées sur les 30 derniers jours
rows = []
base_date = datetime.now() - timedelta(days=30)

for i in range(200):
    lang     = random.choice(["fr", "en"])
    message  = random.choice(MESSAGES_FR if lang == "fr" else MESSAGES_EN)
    priority = random.choices(PRIORITES, weights=[30, 50, 20])[0]
    diff     = random.choices(DIFFICULTES, weights=[40, 40, 20])[0]
    auto     = random.choices(AUTO_RESOLVE, weights=[60, 40])[0]
    resolu   = random.choices(RESOLUS, weights=[50, 30, 20])[0]

    # Date aléatoire dans les 30 derniers jours
    delta = timedelta(
        days=random.randint(0, 29),
        hours=random.randint(8, 18),
        minutes=random.randint(0, 59)
    )
    dt = base_date + delta

    rows.append({
        "timestamp":    dt.strftime("%Y-%m-%d %H:%M:%S"),
        "date":         dt.strftime("%Y-%m-%d"),
        "heure":        dt.strftime("%H:%M"),
        "message":      message,
        "langue":       lang,
        "intent":       "IT incident",
        "difficulte":   diff,
        "priorite":     priority,
        "auto_resolve": auto,
        "resolu":       resolu
    })

# Trier par date
rows.sort(key=lambda x: x["timestamp"])

with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)

print(f"200 tickets générés dans {LOG_FILE}")
print("Tu peux maintenant l'importer dans Power BI.")