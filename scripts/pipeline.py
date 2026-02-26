"""
Pipeline de fusion — IT Helpdesk NLP Dataset
Fusionne les datasets publics en un seul CSV prêt pour le chatbot.
"""

import os
import re
import pandas as pd

# ─── CHEMINS ────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR    = os.path.join(BASE_DIR, "data", "raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "it_helpdesk_final.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── SCHÉMA FINAL ────────────────────────────────────────────────────────────
SCHEMA = [
    "ticket_id", "source_dataset", "text_ticket",
    "category", "subcategory", "priority",
    "symptom", "complexity", "auto_resolvable",
    "suggested_response", "recommended_solution",
    "predicted_resolution_hours", "confidence_score",
]

# ─── NORMALISATION PRIORITÉ ───────────────────────────────────────────────────
PRIORITY_MAP = {
    "1": "Basse",    "low": "Basse",      "faible": "Basse",
    "2": "Moyenne",  "medium": "Moyenne", "normal": "Moyenne",
    "3": "Haute",    "high": "Haute",
    "4": "Critique", "critical": "Critique", "urgent": "Critique",
}

def normalize_priority(p):
    if not isinstance(p, str):
        return "Moyenne"
    for k, v in PRIORITY_MAP.items():
        if k in p.lower():
            return v
    return "Moyenne"


# ─── NETTOYAGE TEXTE ──────────────────────────────────────────────────────────
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+", "", text)       # supprimer URLs
    text = re.sub(r"@\w+", "", text)           # supprimer @mentions
    text = re.sub(r"#\w+", "", text)           # supprimer #hashtags
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─── CLASSIFICATION PAR MOTS-CLÉS ─────────────────────────────────────────────
KEYWORDS = {
    "Réseau":     ["réseau", "network", "internet", "wifi", "vpn", "connexion", "dns", "ethernet"],
    "Matériel":   ["écran", "clavier", "souris", "imprimante", "batterie", "laptop", "ram", "disque"],
    "Logiciels":  ["logiciel", "excel", "word", "teams", "outlook", "install", "crash", "bug", "erreur"],
    "Sécurité":   ["virus", "phishing", "mot de passe", "password", "verrouillé", "antivirus", "hack"],
    "Comptes":    ["compte", "accès", "droits", "permission", "login", "active directory", "utilisateur"],
    "Système":    ["windows", "lent", "bsod", "update", "mise à jour", "démarrage", "redémarrage"],
    "Messagerie": ["email", "mail", "boite", "quota", "spam", "pièce jointe", "outlook"],
    "Téléphonie": ["téléphone", "appel", "sonnerie", "cisco", "voip", "sip", "renvoi"],
    "Cloud":      ["cloud", "onedrive", "sharepoint", "salesforce", "o365", "azure", "sync"],
}

def classify(text):
    if not isinstance(text, str):
        return "Autre"
    t = text.lower()
    scores = {cat: sum(1 for kw in kws if kw in t) for cat, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Autre"


# ─── ENRICHISSEMENT NLP ───────────────────────────────────────────────────────
RES_TIMES = {
    ("Réseau",     "Faible"): 2,  ("Réseau",     "Moyenne"): 4,  ("Réseau",     "Haute"): 8,
    ("Matériel",   "Faible"): 4,  ("Matériel",   "Moyenne"): 24, ("Matériel",   "Haute"): 72,
    ("Logiciels",  "Faible"): 1,  ("Logiciels",  "Moyenne"): 4,  ("Logiciels",  "Haute"): 8,
    ("Sécurité",   "Faible"): 2,  ("Sécurité",   "Moyenne"): 4,  ("Sécurité",   "Haute"): 24,
    ("Comptes",    "Faible"): 1,  ("Comptes",    "Moyenne"): 2,  ("Comptes",    "Haute"): 8,
    ("Système",    "Faible"): 2,  ("Système",    "Moyenne"): 8,  ("Système",    "Haute"): 24,
    ("Messagerie", "Faible"): 1,  ("Messagerie", "Moyenne"): 2,  ("Messagerie", "Haute"): 4,
    ("Téléphonie", "Faible"): 1,  ("Téléphonie", "Moyenne"): 2,  ("Téléphonie", "Haute"): 8,
    ("Cloud",      "Faible"): 2,  ("Cloud",      "Moyenne"): 4,  ("Cloud",      "Haute"): 24,
}

def get_complexity(text, priority):
    words = len(str(text).split())
    ps = {"Critique": 2, "Haute": 1, "Moyenne": 0, "Basse": -1}.get(priority, 0)
    if words > 50 or ps >= 2:
        return "Haute"
    elif words > 20 or ps >= 1:
        return "Moyenne"
    else:
        return "Faible"

def get_auto(category, complexity):
    if complexity == "Haute":
        return "Non"
    if category in {"Messagerie", "Comptes", "Logiciels"} and complexity == "Faible":
        return "Oui"
    if category in {"Matériel", "Cloud"}:
        return "Non"
    return "Partielle"

def enrich(df):
    df["complexity"] = df.apply(
        lambda r: get_complexity(r["text_ticket"], r["priority"]), axis=1)
    df["auto_resolvable"] = df.apply(
        lambda r: get_auto(r["category"], r["complexity"]), axis=1)
    df["predicted_resolution_hours"] = df.apply(
        lambda r: RES_TIMES.get((r["category"], r["complexity"]), 4), axis=1)
    df["confidence_score"] = df["auto_resolvable"].map(
        {"Oui": 0.90, "Partielle": 0.75, "Non": 0.65})
    return df


# ─── CHARGEURS DE DATASETS ────────────────────────────────────────────────────

def load_it_service_desk():
    path = os.path.join(RAW_DIR, "it_service_desk.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, on_bad_lines="skip", encoding="utf-8", encoding_errors="replace")
    print(f"   Colonnes trouvées : {list(df.columns)}")

    # Chercher automatiquement la colonne texte
    text_col = next((c for c in df.columns if any(
        k in c.lower() for k in ["description", "text", "ticket", "summary", "body"])), None)
    cat_col  = next((c for c in df.columns if "categor" in c.lower()), None)
    prio_col = next((c for c in df.columns if "prior" in c.lower()), None)
    res_col  = next((c for c in df.columns if any(
        k in c.lower() for k in ["resolution", "solution", "resolve"])), None)

    rename = {}
    if text_col: rename[text_col] = "text_ticket"
    if cat_col:  rename[cat_col]  = "category"
    if prio_col: rename[prio_col] = "priority"
    if res_col:  rename[res_col]  = "recommended_solution"

    df = df.rename(columns=rename)
    df["source_dataset"] = "it_service_desk"
    return df


def load_incident_log():
    path = os.path.join(RAW_DIR, "incident_event_log.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, on_bad_lines="skip", encoding="utf-8", encoding_errors="replace")
    print(f"   Colonnes trouvées : {list(df.columns)}")

    rename = {}
    for c in df.columns:
        cl = c.lower()
        if "short_description" in cl or "description" in cl:
            rename[c] = "text_ticket"
        elif cl == "category":
            rename[c] = "category"
        elif cl == "subcategory":
            rename[c] = "subcategory"
        elif cl == "priority":
            rename[c] = "priority"

    df = df.rename(columns=rename)

    # Calculer le temps réel de résolution
    if "resolved_at" in df.columns and "opened_at" in df.columns:
        df["opened_at"]   = pd.to_datetime(df["opened_at"],   errors="coerce")
        df["resolved_at"] = pd.to_datetime(df["resolved_at"], errors="coerce")
        df["predicted_resolution_hours"] = (
            (df["resolved_at"] - df["opened_at"]).dt.total_seconds() / 3600
        ).round(1)

    df["source_dataset"] = "incident_event_log"
    return df


def load_customer_support():
    # Accepte les deux noms possibles
    for name in ["customer_support_tickets.csv", "support_tickets.csv"]:
        path = os.path.join(RAW_DIR, name)
        if os.path.exists(path):
            break
    else:
        return None

    df = pd.read_csv(path, on_bad_lines="skip", encoding="utf-8", encoding_errors="replace")
    print(f"   Colonnes trouvées : {list(df.columns)}")

    text_col = next((c for c in df.columns if any(
        k in c.lower() for k in ["description", "text", "body", "ticket", "issue", "subject"])), None)
    cat_col  = next((c for c in df.columns if "categor" in c.lower() or "type" in c.lower()), None)
    prio_col = next((c for c in df.columns if "prior" in c.lower()), None)
    res_col  = next((c for c in df.columns if any(
        k in c.lower() for k in ["resolution", "response", "solution"])), None)

    rename = {}
    if text_col: rename[text_col] = "text_ticket"
    if cat_col:  rename[cat_col]  = "category"
    if prio_col: rename[prio_col] = "priority"
    if res_col:  rename[res_col]  = "suggested_response"

    df = df.rename(columns=rename)
    df["source_dataset"] = "customer_support"
    return df


def load_twitter():
    path = os.path.join(RAW_DIR, "twcs.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, on_bad_lines="skip", encoding="utf-8", encoding_errors="replace")
    print(f"   Colonnes trouvées : {list(df.columns)}")

    # Garder uniquement les messages entrants (questions clients)
    if "inbound" in df.columns:
        df = df[df["inbound"] == True].copy()

    df = df.rename(columns={"text": "text_ticket"})
    if "response" in df.columns:
        df["suggested_response"] = df["response"]

    df["source_dataset"] = "twitter_support"
    return df


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def process(name, df):
    """Nettoie et enrichit un dataset."""

    # Ajouter les colonnes manquantes
    for col in SCHEMA:
        if col not in df.columns:
            df[col] = None

    # Nettoyage
    df["text_ticket"] = df["text_ticket"].apply(clean_text)
    df["priority"]    = df["priority"].apply(normalize_priority)

    # Filtrer les tickets trop courts
    before = len(df)
    df = df[df["text_ticket"].apply(lambda x: len(str(x).split()) >= 4)]
    df = df.drop_duplicates(subset=["text_ticket"])
    print(f"   ✅ {len(df)} tickets valides  ({before - len(df)} supprimés)")

    # Classifier les tickets sans catégorie
    mask = df["category"].isna() | (df["category"].astype(str).str.strip() == "")
    df.loc[mask, "category"] = df.loc[mask, "text_ticket"].apply(classify)

    # Enrichir
    df = enrich(df)

    return df[SCHEMA]


def main():
    print("\n" + "=" * 55)
    print("  PIPELINE IT HELPDESK NLP — DÉMARRAGE")
    print("=" * 55)

    loaders = [
        ("IT Service Desk",    load_it_service_desk),
        ("Incident Event Log", load_incident_log),
        ("Customer Support",   load_customer_support),
        ("Twitter Support",    load_twitter),
    ]

    all_dfs = []

    for name, loader in loaders:
        print(f"\n📂 Chargement : {name}")
        df = loader()

        if df is None:
            print("   ⚠️  Fichier non trouvé dans data/raw/ — ignoré")
            continue

        if "text_ticket" not in df.columns or df["text_ticket"].isna().all():
            print("   ⚠️  Colonne texte introuvable — ignoré")
            continue

        df = process(name, df)
        all_dfs.append(df)

    if not all_dfs:
        print("\n❌ Aucun fichier chargé.")
        print(f"   Vérifie que tes CSV sont dans : {RAW_DIR}")
        return

    # Fusion
    print("\n🔀 Fusion de tous les datasets...")
    final = pd.concat(all_dfs, ignore_index=True)
    final = final.drop_duplicates(subset=["text_ticket"])
    final["ticket_id"] = [f"TKT-{i:05d}" for i in range(1, len(final) + 1)]

    # Export
    final.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    print("\n" + "=" * 55)
    print(f"  ✅ TERMINÉ — {len(final)} tickets fusionnés")
    print(f"  📁 Fichier : {OUTPUT_CSV}")
    print(f"\n  Répartition par catégorie :")
    for cat, count in final["category"].value_counts().items():
        print(f"     {cat:<20} {count}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()