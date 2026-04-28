import json
import time
import random
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL  = "llama-3.1-8b-instant"

OUTPUT_FILE = "feedback_dataset_generated.json"


INTENTS = {

    "resolved": {
        "description": "The user clearly confirms the IT problem is now fixed and working",
        "constraints": [
            "Must express clear confirmation that it works NOW",
            "Can include relief, thanks, happiness",
            "No negation anywhere in the sentence",
            "Can be very short (1-3 words) or longer",
        ],
        "examples": [
            "ça marche", "yes it works", "parfait merci", "nickel",
            "we're good", "fixed!", "ça tourne enfin", "super ça fonctionne",
            "it's working now thanks", "c'est bon", "all good",
            "oui ça a marché", "resolved, thank you", "it worked!",
            "génial tout fonctionne", "yes finally works",
        ],
        "contexts": [
            "after VPN fix", "after password reset", "after printer fix",
            "after software reinstall", "after network config",
            "after email setup", "after Windows update",
        ],
    },

    "failure": {
        "description": "The user says the proposed solution did NOT work and the problem still exists",
        "constraints": [
            "Must clearly indicate the solution failed",
            "Can include negation: not, didn't, still, toujours, pas, jamais",
            "Can be frustrated, neutral, or polite",
            "Subtle negations are valid: 'I wouldn't say it's fixed'",
            "Problem persisting without explicit 'not' is also failure: 'same issue'",
        ],
        "examples": [
            "toujours pas", "still broken", "rien n'a changé",
            "same problem", "le bug persiste", "même résultat",
            "didn't fix it", "ça n'a pas marché", "tried it, no luck",
            "I wouldn't say it's fixed", "not exactly working",
            "ça bug encore", "it's acting up again", "still the same",
            "pas de changement", "toujours la même erreur",
            "nothing changed after doing that", "still not resolved",
        ],
        "contexts": [
            "VPN still not connecting", "password still rejected",
            "printer still offline", "software still crashing",
            "network still down", "email still not sending",
            "screen still black", "computer still slow",
        ],
    },

    "partial": {
        "description": "Some steps worked but not all — the problem is only partially resolved",
        "constraints": [
            "Must indicate MIXED result — some success, some failure",
            "Often references specific steps: step 1, étape 2",
            "Words like: almost, presque, partiellement, kind of, sort of",
            "NOT fully resolved, NOT completely failed",
        ],
        "examples": [
            "presque, l'étape 2 plante", "almost works but step 3 fails",
            "ça marche presque", "kind of working but not fully",
            "step 1 worked but step 2 doesn't", "partiellement résolu",
            "almost there, last step fails", "ça marche un peu",
            "j'ai fait les 2 premières étapes mais la 3ème bloque",
            "it helped a bit but still not fully working",
            "worked for a while then stopped", "almost fixed",
        ],
        "contexts": [
            "VPN connects but drops", "password reset but can't login",
            "printer found but won't print", "email sends but not receives",
            "software opens but crashes on use", "network connects but no internet",
        ],
    },

    "mixed": {
        "description": "User confirms current problem is resolved BUT mentions a new different IT problem in the same message",
        "constraints": [
            "MUST have both: confirmation of resolution AND a new problem",
            "New problem must be clearly different from the original",
            "Connectors: mais/but/however/also/aussi/en plus/additionally",
            "The new problem should be a real IT issue (VPN, printer, email, etc.)",
        ],
        "examples": [
            "oui ça marche mais maintenant j'ai un problème avec le VPN",
            "yes fixed but now outlook crashes",
            "merci mais j'ai aussi un souci avec l'imprimante",
            "it works now but my screen is flickering",
            "résolu merci, mais Teams ne s'ouvre plus",
            "ça fonctionne mais maintenant le wifi est lent",
            "fixed thanks, however now my keyboard is acting weird",
            "c'est bon mais j'ai un nouveau problème avec Excel",
        ],
        "contexts": [
            "resolved VPN, new printer issue",
            "resolved password, new email issue",
            "resolved software crash, new network issue",
            "resolved printer, new screen issue",
        ],
    },

    "ticket": {
        "description": "User explicitly requests a human technician, escalation, or support ticket creation",
        "constraints": [
            "Must show explicit desire for human intervention",
            "Keywords: ticket, technicien, escalate, human, someone, personne",
            "Can be polite or frustrated",
            "Can be a question or a statement",
        ],
        "examples": [
            "créez un ticket s'il vous plaît", "I need a technician",
            "please escalate", "j'ai besoin d'un technicien",
            "can someone come fix this", "open a support ticket",
            "je veux parler à quelqu'un", "please send someone",
            "I want to escalate this", "pouvez-vous créer un incident",
            "I need human support", "envoyez un technicien",
            "escalader ce problème", "I want to speak to IT",
        ],
        "contexts": [
            "frustrated after multiple failures",
            "urgent hardware issue",
            "security incident requiring human",
            "complex network problem",
            "first request for escalation",
        ],
    },

    "ambiguous": {
        "description": "Message is too vague, short, or unclear to determine if the solution worked or not",
        "constraints": [
            "Cannot clearly classify as yes/no/partial",
            "Very short reactions, interjections, filler words",
            "Uncertain language: maybe, peut-être, je sais pas",
            "Emotional reactions without clear IT meaning",
            "NOT a clear confirmation or denial",
        ],
        "examples": [
            "hmmm", "bof", "meh", "je sais pas", "mouais",
            "pas forcément", "...", "ok", "je vois",
            "interesting", "on verra", "maybe", "peut-être",
            "ça dépend", "not sure", "I guess", "kind of",
            "difficile à dire", "hard to tell", "we'll see",
        ],
        "contexts": [
            "user unsure about result",
            "user distracted or busy",
            "user testing something",
            "vague reaction to solution",
        ],
    },
}

# ══════════════════════════════════════════════════════════════════
# VARIATIONS DE STYLE
# ══════════════════════════════════════════════════════════════════

STYLES = [
    "very short (1-3 words), casual",
    "short sentence (4-7 words), informal",
    "medium sentence (8-15 words), neutral professional",
    "with typos or abbreviations (common in chat)",
    "mixed French and English in same sentence",
    "very formal and polite",
    "frustrated and impatient tone",
    "with emoji or punctuation emphasis like !!! or ...",
    "using IT slang or technical vocabulary",
    "with filler words: bon, ben, alors, well, so",
    "question form instead of statement",
    "with time reference: still, encore, toujours, maintenant",
]

LANGUAGES = [
    "French only",
    "English only",
    "French only",
    "English only",
    "French only",
    "English only",
    "mix of French and English words",
]

# ══════════════════════════════════════════════════════════════════
# PROMPT ENGINEERING
# ══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a dataset generation expert for NLP intent classification.
Your task is to generate realistic, diverse IT support chat messages.

CRITICAL RULES:
1. Generate ONLY the messages, one per line, no numbering, no quotes, no explanation
2. Each message must be authentic — like a real user typing in a chat
3. Maximum diversity: vary length, tone, vocabulary, language
4. Never repeat the same message twice
5. Messages must UNAMBIGUOUSLY belong to their intended class
6. Do NOT add any preamble, explanation, or metadata"""

def build_prompt(intent: str, config: dict, n: int, style: str, language: str, batch_num: int) -> str:

    examples_str = "\n".join(f"  - {e}" for e in config["examples"])
    constraints_str = "\n".join(f"  • {c}" for c in config["constraints"])
    contexts_str = "\n".join(f"  - {c}" for c in config["contexts"])

    return f"""Generate exactly {n} unique IT support chat messages for the intent: "{intent}"

INTENT DEFINITION:
{config["description"]}

MANDATORY CONSTRAINTS:
{constraints_str}

STYLE FOR THIS BATCH:
- Language: {language}
- Tone/Format: {style}
- Batch variation seed: {batch_num} (ensure uniqueness from other batches)

REALISTIC CONTEXTS (vary across messages):
{contexts_str}

REFERENCE EXAMPLES (do NOT copy, use as style guide only):
{examples_str}

IMPORTANT:
- Messages must be immediately classifiable as "{intent}" with high confidence
- Include natural variations: typos, abbreviations, emoji sometimes
- Avoid messages that could belong to another intent class
- Each message on its own line
- No numbering, no bullets, no quotes

Generate {n} messages now:"""


# ══════════════════════════════════════════════════════════════════
# GÉNÉRATEUR
# ══════════════════════════════════════════════════════════════════

def generate_batch(intent: str, config: dict, n: int, style: str,
                   language: str, batch_num: int, retries: int = 3) -> list:

    prompt = build_prompt(intent, config, n, style, language, batch_num)

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model    = MODEL,
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens  = 800,
                temperature = 0.85,  # haute pour la diversité
                top_p       = 0.95,
            )

            raw   = response.choices[0].message.content.strip()
            lines = [
                l.strip().strip("-•*").strip('"').strip("'").strip()
                for l in raw.split("\n")
                if l.strip() and len(l.strip()) >= 2
            ]

            # Filtrer les lignes trop longues (probablement des explications)
            lines = [l for l in lines if len(l) <= 200]

            # Filtrer les lignes qui ressemblent à des headers
            lines = [l for l in lines if not l.lower().startswith(("here", "voici", "note", "batch", "messages"))]

            if len(lines) >= n * 0.6:  # accepter si au moins 60% du quota
                return lines[:n]

        except Exception as e:
            print(f"    [ERREUR] Tentative {attempt+1}/{retries}: {e}")
            time.sleep(2)

    return []


def validate_entry(text: str, intent: str) -> bool:
    """Validation basique pour écarter les entrées aberrantes."""
    if not text or len(text) < 2:
        return False
    if len(text) > 300:
        return False
    # Écarter si ça ressemble à du code ou JSON
    if text.startswith(("{", "[", "<", "```")):
        return False
    # Écarter les phrases qui contiennent des patterns de génération
    bad_patterns = ["generate", "intent:", "example:", "batch", "messages:"]
    if any(p in text.lower() for p in bad_patterns):
        return False
    return True


def generate_dataset(
    total_per_intent : int = 500,
    batch_size       : int = 20,
    output_file      : str = OUTPUT_FILE,
) -> list:

    all_data   = []
    seen_texts = set()

    print("=" * 65)
    print(f"  GÉNÉRATION DATASET — {total_per_intent * len(INTENTS)} exemples cibles")
    print("=" * 65)

    for intent, config in INTENTS.items():
        print(f"\n[{intent.upper()}] Cible : {total_per_intent} exemples")
        collected  = []
        batch_num  = 0
        duplicates = 0

        while len(collected) < total_per_intent:
            remaining = total_per_intent - len(collected)
            n         = min(batch_size, remaining + 5)  # +5 pour compenser les filtrés

            style    = random.choice(STYLES)
            language = random.choice(LANGUAGES)

            examples = generate_batch(intent, config, n, style, language, batch_num)
            batch_num += 1

            new_count = 0
            for text in examples:
                text_clean = text.strip()
                if not validate_entry(text_clean, intent):
                    continue
                key = text_clean.lower()
                if key in seen_texts:
                    duplicates += 1
                    continue
                seen_texts.add(key)
                collected.append({
                    "text"  : text_clean,
                    "intent": intent,
                    "source": "llm_generated",
                    "style" : style,
                    "lang"  : language,
                })
                new_count += 1

            pct = len(collected) / total_per_intent * 100
            print(f"  batch {batch_num:02d} | +{new_count:2d} | total={len(collected):4d}/{total_per_intent} ({pct:.0f}%) | dupes={duplicates}")

            # Pause pour éviter le rate limit Groq
            time.sleep(0.5)

            # Sécurité : éviter boucle infinie
            if batch_num > total_per_intent // batch_size * 3:
                print(f"  [STOP] Trop de batches, arrêt à {len(collected)} exemples")
                break

        all_data.extend(collected)
        print(f"  → {len(collected)} exemples collectés pour '{intent}'")

    # ── Mélanger et sauvegarder ───────────────────────────────────
    random.shuffle(all_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*65}")
    print(f"  DATASET FINAL : {len(all_data)} exemples → {output_file}")

    from collections import Counter
    counts = Counter(d["intent"] for d in all_data)
    for intent, count in sorted(counts.items()):
        print(f"  {intent:<15} : {count:4d} exemples")

    return all_data


def print_samples(data: list, n_per_intent: int = 5):
    """Afficher des échantillons pour vérification qualité."""
    from collections import defaultdict
    by_intent = defaultdict(list)
    for d in data:
        by_intent[d["intent"]].append(d["text"])

    print(f"\n{'='*65}")
    print("  ÉCHANTILLONS DE QUALITÉ")
    print(f"{'='*65}")
    for intent, texts in sorted(by_intent.items()):
        print(f"\n[{intent.upper()}]")
        samples = random.sample(texts, min(n_per_intent, len(texts)))
        for t in samples:
            print(f"  • {t}")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description="Générateur de dataset feedback IT")
    parser.add_argument("--total",  type=int, default=500, help="Exemples par intent (défaut: 500)")
    parser.add_argument("--batch",  type=int, default=20,  help="Taille des batches (défaut: 20)")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="Fichier de sortie")
    parser.add_argument("--quick",  action="store_true", help="Mode rapide: 50 par intent pour test")
    args = parser.parse_args()

    if args.quick:
        args.total = 50
        args.batch = 10
        print("Mode QUICK activé : 50 exemples par intent")

    data = generate_dataset(
        total_per_intent = args.total,
        batch_size       = args.batch,
        output_file      = args.output,
    )

    print_samples(data, n_per_intent=5)

    print(f"\nLancez maintenant :")
    print(f"  python train_feedback_classifier.py --data {args.output}")