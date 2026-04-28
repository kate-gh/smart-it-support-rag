# train_feedback_classifier_tf.py
import json
import argparse
import numpy as np
from collections import Counter
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
import tensorflow as tf
import warnings
warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════
LABELS = ["resolved", "failure", "partial", "mixed", "ticket", "ambiguous"]
L2I = {l: i for i, l in enumerate(LABELS)}
I2L = {i: l for i, l in enumerate(LABELS)}

MODEL_NAME = "microsoft/mdeberta-v3-base"
OUTPUT_DIR = "./feedback_model_tf"

# Gold standard
GOLD_DATA = [
    ("ça marche", "resolved"),
    ("toujours pas", "failure"),
    ("presque, l'étape 2 plante", "partial"),
    ("oui ça marche mais j'ai un problème VPN", "mixed"),
    ("créez un ticket s'il vous plaît", "ticket"),
    ("hmmm", "ambiguous"),
]
GOLD_WEIGHT = 5

# ── Chargement et préparation des données ──────────
def load_data(path):
    print(f"\n[DATA] Chargement : {path}")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    data = [d for d in raw if d.get("intent") in L2I and d.get("text", "").strip() and len(d["text"]) <= 300]

    counts = Counter(d["intent"] for d in data)
    print("  Distribution originale :")
    for l in LABELS:
        print(f"    {l:<15} : {counts.get(l,0):5d}")

    # Ajouter gold standard
    for text, intent in GOLD_DATA:
        for _ in range(GOLD_WEIGHT):
            data.append({"text": text, "intent": intent})

    print(f"  Total après gold : {len(data)}")

    texts = [d["text"] for d in data]
    labels = [L2I[d["intent"]] for d in data]

    X_train, X_temp, y_train, y_temp = train_test_split(texts, labels, test_size=0.15, stratify=labels, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42)

    print(f"  Split : train={len(X_train)} | val={len(X_val)} | test={len(X_test)}")

    return (X_train, y_train), (X_val, y_val), (X_test, y_test)

# ── Tokenizer & encodage ───────────────
def encode(texts, tokenizer, max_len=128):
    enc = tokenizer(texts, truncation=True, padding=True, max_length=max_len, return_tensors="tf")
    return enc

# ── Metrics personnalisées ─────────────
def compute_metrics(y_true, y_pred):
    preds = np.argmax(y_pred, axis=-1)
    report = classification_report(y_true, preds, target_names=LABELS, output_dict=True, zero_division=0)

    failure_f1 = report.get("failure", {}).get("f1-score",0)
    resolved_f1 = report.get("resolved", {}).get("f1-score",0)
    ticket_f1 = report.get("ticket", {}).get("f1-score",0)

    return {
        "accuracy": report["accuracy"],
        "f1_macro": report["macro avg"]["f1-score"],
        "f1_weighted": report["weighted avg"]["f1-score"],
        "f1_failure": round(failure_f1,4),
        "f1_resolved": round(resolved_f1,4),
        "f1_ticket": round(ticket_f1,4),
        "score_critique": round(0.35*failure_f1 + 0.3*resolved_f1 + 0.15*ticket_f1 + 0.2*report["macro avg"]["f1-score"],4)
    }

# ── Entraînement ─────────────
def train_tf(data_path, epochs=12, lr=2e-5):
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data(data_path)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_enc = encode(X_train, tokenizer)
    val_enc = encode(X_val, tokenizer)
    test_enc = encode(X_test, tokenizer)

    model = TFAutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=len(LABELS), id2label=I2L, label2id=L2I)

    optimizer = tf.keras.optimizers.Adam(learning_rate=lr)
    loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    model.compile(optimizer=optimizer, loss=loss, metrics=['accuracy'])

    print("\n[TRAIN] Début entraînement TensorFlow...")
    model.fit(
        train_enc['input_ids'], y_train,
        validation_data=(val_enc['input_ids'], y_val),
        epochs=epochs,
        batch_size=32,
    )

    # Évaluation
    print("\n[EVAL] Évaluation sur test set...")
    logits = model.predict(test_enc['input_ids']).logits
    metrics = compute_metrics(y_test, logits)
    print(metrics)

    # Matrice de confusion
    preds = np.argmax(logits, axis=-1)
    cm = confusion_matrix(y_test, preds)
    print("  MATRICE DE CONFUSION")
    print("  " + "  ".join(f"{l[:6]:>6}" for l in LABELS))
    for i,row in enumerate(cm):
        print(f"  {LABELS[i][:6]:<6} " + "  ".join(f"{v:6d}" for v in row))

    # Sauvegarde
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"\n[SAVE] Modèle sauvegardé → {OUTPUT_DIR}")

# ── MAIN ─────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="feedback_dataset_generated.json")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--lr", type=float, default=2e-5)
    args = parser.parse_args()

    train_tf(args.data, args.epochs, args.lr)