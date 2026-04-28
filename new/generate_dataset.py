# generate_dataset.py
import json, pandas as pd, time, os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"  # gratuit et puissant

IT_TOPICS = {
    "Access Management": [
        "password reset windows", "account locked active directory",
        "MFA setup", "VPN access denied", "SSO login issue",
        "permission denied shared folder", "account expired"
    ],
    "Network & Connectivity": [
        "WiFi not connecting", "VPN disconnects frequently",
        "internet very slow", "network drive not accessible",
        "DNS resolution failure", "proxy configuration"
    ],
    "Hardware & Peripherals": [
        "printer not recognized", "external monitor not detected",
        "keyboard not working", "mouse cursor freezing",
        "docking station issues", "webcam not working in Teams",
        "headset no sound", "USB port not working"
    ],
    "Software & Applications": [
        "Outlook not opening", "Teams crashes on startup",
        "Office 365 activation failed", "browser slow or crashing",
        "software installation blocked", "Excel file corrupted",
        "Zoom audio issues", "OneDrive sync error"
    ],
    "Security": [
        "suspected phishing email", "malware detected",
        "BitLocker recovery key", "suspicious login alert",
        "ransomware warning", "certificate expired"
    ],
    "Data & Storage": [
        "OneDrive storage full", "SharePoint file deleted",
        "file recovery needed", "disk space low",
        "backup not running", "file access denied"
    ],
    "Onboarding": [
        "new laptop first setup", "corporate email setup",
        "software installation list", "network access new employee",
        "badge access IT systems"
    ],
    "IT Support": [
        "PC very slow", "computer freezing randomly",
        "blue screen of death", "PC won't turn on",
        "Windows update stuck", "CPU fan loud noise"
    ],
}

def generate_pairs(category: str, topic: str, n: int = 8) -> list:
    prompt = f"""You are an expert IT support specialist in a corporate environment.

Generate {n} realistic question/answer pairs for an internal IT support chatbot.
Category: {category}
Topic: {topic}

Rules:
- Questions: written like a real non-technical employee (casual, sometimes vague)
- Include variations: urgent tone, vague descriptions, mix of FR/EN words
- Answers: numbered steps, clear, no excessive jargon
- Last step always: "If the issue persists, contact the IT helpdesk."
- NO placeholders like [Name], [Company], [User]
- Answers between 80 and 300 words
- Priority: "high" if blocking work, "medium" if inconvenient, "low" if minor

Respond ONLY with valid JSON array, no markdown, no explanation:
[
  {{
    "question": "...",
    "answer": "1. ... 2. ... 3. ...",
    "priority": "high|medium|low",
    "intent_tag": "{topic.lower().replace(' ', '_')}"
  }}
]"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model    = MODEL,
                messages = [
                    {"role": "system", "content": "You generate IT support datasets. Respond only with valid JSON arrays."},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens  = 3000,
                temperature = 0.7,
            )
            text = response.choices[0].message.content.strip()

            # Nettoyer si markdown
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            # Extraire le JSON array
            start = text.find("[")
            end   = text.rfind("]") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON array found")

            return json.loads(text[start:end])

        except Exception as e:
            print(f"  ⚠️  Retry {attempt+1}/3 — {e}")
            time.sleep(2)
    return []

# ── Génération ───────────────────────────────────────────
rows = []

for category, topics in IT_TOPICS.items():
    print(f"\n📂 {category}")
    for topic in topics:
        pairs = generate_pairs(category, topic, n=8)
        for item in pairs:
            item["category"]       = category
            item["source"]         = "synthetic_groq"
            item["auto_resolution"] = True
            rows.append(item)
        print(f"  ✅ {topic} → {len(pairs)} paires")
        time.sleep(0.3)  # rate limit Groq

# ── Fusion avec dataset existant ─────────────────────────
df_new      = pd.DataFrame(rows)
df_existing = pd.read_csv("data/chatbot_rag_clean.csv")
df_final    = pd.concat([df_existing, df_new], ignore_index=True)
df_final    = df_final.drop_duplicates(subset=["question"])

df_final.to_csv("data/chatbot_rag_final_v2.csv", index=False)

print(f"\n{'='*40}")
print(f"✅ Dataset final : {len(df_final)} paires")
print(f"\nPar catégorie :")
print(df_final["category"].value_counts().to_string())
print(f"\nPar source :")
print(df_final["source"].value_counts().to_string())