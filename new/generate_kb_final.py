import json
import time
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

IT_TOPICS_EXTENDED = {
    "Access Management": [
        "reset domain password", "account locked after failed attempts", "Microsoft Authenticator MFA setup",
        "SSO login loop issue", "access denied to shared network drive", "account expired notification",
        "2FA backup codes recovery", "privileged access request", "service account password rotation",
        "self-service password portal down", "Azure AD join failing", "Kerberos ticket expired",
        "RDP access denied", "sudo permissions Linux", "bitlocker recovery key lost",
        "password complexity requirements", "temporary access grant", "role based access control issue",
        "federated identity failure", "OAuth token expired"
    ],
    "Network & Connectivity": [
        "WiFi connects but no internet", "VPN disconnects every 30 minutes", "slow internet during video calls",
        "network drive mapping fails", "DNS cannot resolve internal websites", "proxy configuration for corporate network",
        "Ethernet not detected after sleep", "packet loss in Microsoft Teams", "firewall blocking specific application",
        "DHCP not renewing IP address", "WiFi certificate expired", "VLAN access wrong",
        "split tunneling VPN issue", "bandwidth throttling suspicion", "network printer offline",
        "TCP connection timeout", "wireless interference high", "5GHz band not available",
        "radius authentication timeout", "MTU size mismatch"
    ],
    "Hardware & Peripherals": [
        "printer shows offline status", "external monitor not detected via HDMI", "keyboard typing wrong characters",
        "mouse cursor jumps erratically", "docking station USB ports not working", "webcam not found in Zoom",
        "headset microphone no sound", "USB flash drive not showing", "laptop battery not charging",
        "loud fan noise continuously", "touchpad not responding", "SSD not detected BIOS",
        "RAM slot not working", "bluetooth mouse disconnects", "thunderbolt port not working",
        "SD card reader not working", "NVMe drive overheating", "graphics card not detected",
        "hard drive clicking sound", "document feeder jammed"
    ],
    "Software & Applications": [
        "Outlook stuck on loading profile", "Microsoft Teams crashes on screen share", "Office 365 activation error",
        "Chrome tabs crashing frequently", "software installation blocked by policy", "Excel file corrupted cannot open",
        "Zoom video not working", "OneDrive sync conflict", "Slack notifications not appearing",
        "Visual Studio build fails", "Adobe Acrobat won't open PDF", "Docker container won't start",
        "Jira attachment upload fails", "Salesforce lightning slow", "SAP GUI connection drops",
        "Power BI refresh fails", "Git push rejected", "Jenkins build stuck",
        "Kubernetes pod crashing", "PostgreSQL connection pool exhausted"
    ],
    "Security": [
        "phishing email clicked by mistake", "Windows Defender found malware", "BitLocker asking for recovery key",
        "suspicious login from different country", "ransomware popup on screen", "SSL certificate expired warning",
        "Windows Update security patch failing", "USB drive autorun warning", "unusual outbound traffic detected",
        "password expired today", "DLP policy blocking email", "CrowdStrike alert triggered",
        "SentinelOne quarantine file", "Palo Alto blocked website", "Zscaler authentication failed",
        "SIEM alert brute force", "endpoint isolation needed", "privilege escalation attempt",
        "lateral movement detected", "data exfiltration attempt"
    ],
    "Data & Storage": [
        "OneDrive storage full", "SharePoint file accidentally deleted", "restore previous version of file",
        "low disk space on C drive", "backup job failed overnight", "access denied to shared folder",
        "network drive keeps disconnecting", "cloud sync stuck at 99%", "file locking prevents editing",
        "lost changes after crash", "external hard drive not recognized", "S3 bucket permission denied",
        "Azure blob storage slow", "Google Drive sync error", "NAS volume full",
        "iSCSI connection timeout", "NFS mount fails", "database backup corrupt",
        "snapshot creation failed", "replication lag high"
    ],
    "Onboarding": [
        "first time laptop setup", "corporate email configuration Outlook", "required software list for new hire",
        "network access request for new employee", "badge access to server room", "VPN setup first time connection",
        "Microsoft Teams welcome setup", "shared drive access request", "printer setup new laptop",
        "MFA enrollment first time", "intune enrollment failed", "Jamf profile not installing",
        "software center empty", "company portal not working", "AD account not synced",
        "Exchange mailbox missing", "SharePoint site access", "GitHub organization invite",
        "password manager setup", "HR system login failed"
    ],
    "IT Support": [
        "PC extremely slow at startup", "computer freezes randomly", "blue screen error CRITICAL PROCESS DIED",
        "PC will not power on", "Windows update stuck at 0%", "CPU usage 100% with no apps open",
        "memory leak detected over time", "graphical glitches on screen", "audio no sound device",
        "sleep mode not waking up", "date and time resets after reboot", "BIOS corrupted message",
        "overheating shutdowns", "SFC found corrupt files", "DISM restore health fails",
        "chkdsk found bad sectors", "DLL missing error", "secure boot violation",
        "TPM not detected", "windows reinstall needed"
    ]
}

# ============================================================
# CALCUL : 160 topics × 3 runs × 21 paires = 10 080 paires
# ============================================================
PAIRS_PER_REQUEST = 21
PAUSE_BETWEEN_REQUESTS = 8  # secondes

def generate_pairs(category, topic, num_pairs, model, temperature):
    prompt = f"""Generate {num_pairs} IT support question/answer pairs in ENGLISH.

CATEGORY: {category}
TECHNICAL ISSUE: {topic}

RULES:
- Questions: casual employee language, 5-20 words, NO placeholders like [Name]
- Answers: 3-6 numbered steps, clear, actionable
- NO mention of "contact IT", "helpdesk", "open a ticket"
- Each question must be unique and different
- End answer with a natural follow-up question
- Priority: "high", "medium", or "low"

Respond ONLY with valid JSON array:
[
  {{
    "question": "...",
    "answer": "1. ...\\n2. ...\\n3. ...",
    "priority": "high|medium|low"
  }}
]

Generate exactly {num_pairs} pairs:"""

    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You generate IT support Q&A pairs. Respond only with valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=temperature,
            )

            text = response.choices[0].message.content.strip()

            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            start = text.find("[")
            end = text.rfind("]") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON array found")

            data = json.loads(text[start:end])

            for item in data:
                item["category"] = category
                item["topic"] = topic
                item["model"] = model
                item["temperature"] = temperature

            return data

        except Exception as e:
            if "429" in str(e):
                print(f"  ⚠️ Rate limit — pause 30s...")
                time.sleep(30)
            else:
                print(f"  ⚠️ Tentative {attempt+1}/5: {str(e)[:60]}")
                time.sleep(5)

    return []


if __name__ == "__main__":

    os.makedirs("data", exist_ok=True)
    SAVE_FILE = "data/kb_10k_final.csv"

    # Reprendre si interrompu
    all_rows = []
    if os.path.exists(SAVE_FILE):
        df_existing = pd.read_csv(SAVE_FILE)
        all_rows = df_existing.to_dict("records")
        print(f"♻️  Reprise: {len(all_rows)} paires déjà générées")

    runs_config = [
        (0.6, MODELS[0]),
        (0.7, MODELS[1]),
        (0.8, MODELS[0]),
    ]

    total_topics = sum(len(v) for v in IT_TOPICS_EXTENDED.values())
    total_expected = total_topics * len(runs_config) * PAIRS_PER_REQUEST
    print(f"\n{'='*60}")
    print(f"🚀 GÉNÉRATION 10 000 PAIRES")
    print(f"   {total_topics} topics × {len(runs_config)} runs × {PAIRS_PER_REQUEST} paires")
    print(f"   = {total_expected} paires attendues")
    print(f"   Durée estimée: ~{round(total_topics * len(runs_config) * PAUSE_BETWEEN_REQUESTS / 60)} minutes")
    print(f"{'='*60}\n")

    for run_num, (temp, model) in enumerate(runs_config):
        print(f"\n{'='*40}")
        print(f"🏃 RUN {run_num+1}/3 — {model} — temp={temp}")
        print(f"{'='*40}")

        task_num = 0
        for category, topics in IT_TOPICS_EXTENDED.items():
            for topic in topics:

                if len(all_rows) >= 10000:
                    break

                task_num += 1
                print(f"[Run {run_num+1} | {task_num}/{total_topics}] {category} — {topic[:40]}")

                pairs = generate_pairs(category, topic, PAIRS_PER_REQUEST, model, temp)

                if pairs:
                    all_rows.extend(pairs)
                    print(f"  ✅ +{len(pairs)} | Total: {len(all_rows)}/10000")

                    # Sauvegarde toutes les 200 paires
                    if len(all_rows) % 200 == 0:
                        pd.DataFrame(all_rows).to_csv(SAVE_FILE, index=False)
                        print(f"  💾 Sauvegarde automatique: {len(all_rows)} paires")
                else:
                    print(f"  ❌ Échec pour ce topic, on continue...")

                time.sleep(PAUSE_BETWEEN_REQUESTS)

            if len(all_rows) >= 10000:
                break

        # Sauvegarde fin de run
        pd.DataFrame(all_rows).to_csv(SAVE_FILE, index=False)
        print(f"\n💾 Fin Run {run_num+1}: {len(all_rows)} paires sauvegardées")

        if run_num < 2 and len(all_rows) < 10000:
            print("⏸️  Pause 60s avant prochain run...")
            time.sleep(60)

    # Sauvegarde finale
    df_final = pd.DataFrame(all_rows[:10000])
    df_final.to_csv(SAVE_FILE, index=False)

    print(f"\n{'='*60}")
    print(f"🎉 TERMINÉ !")
    print(f"📊 Total généré: {len(df_final)} paires")
    print(f"💾 Fichier: {SAVE_FILE}")
    print(f"{'='*60}")