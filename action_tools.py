import platform, requests
from datetime import datetime
from tickets_store import save_ticket

# ─────────────────────────────────────────
# TOOL 1 — Reset Password (log + ticket)
# ─────────────────────────────────────────
def tool_reset_password(username: str, user_id: str = "anonymous") -> dict:
    """
    Simule un reset password.
    """
    try:
        ticket_id = f"PWD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        save_ticket(
            ticket_id = ticket_id,
            user_id   = user_id,
            summary   = f"Password reset request for user: {username}",
            category  = "Access Management",
            priority  = "high",
            source    = "agent_action"
        )
        return {
            "success"  : True,
            "ticket_id": ticket_id,
            "message"  : f"Password reset initiated for {username}. "
                         f"Check your recovery email. Ticket: {ticket_id}"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────
# TOOL 2 — Vérifier statut services cloud
# ─────────────────────────────────────────
SERVICE_URLS = {
    "teams"      : "https://teams.microsoft.com",
    "outlook"    : "https://outlook.office365.com",
    "office365"  : "https://portal.office.com",
    "sharepoint" : "https://www.sharepoint.com",
    "onedrive"   : "https://onedrive.live.com",
    "zoom"       : "https://zoom.us",
    "azure"      : "https://portal.azure.com",
    "github"     : "https://github.com",
}

def tool_check_service(service: str) -> dict:
    """
    Ping un service cloud pour vérifier s'il est accessible.
    """
    key = service.lower().strip()
    url = SERVICE_URLS.get(key)

    if not url:
        return {
            "success": False,
            "message": f"Service '{service}' not in monitoring list.",
            "known_services": list(SERVICE_URLS.keys())
        }

    try:
        r      = requests.get(url, timeout=5)
        is_up  = r.status_code < 500
        return {
            "success" : True,
            "service" : service,
            "status"  : "up" if is_up else "down",
            "code"    : r.status_code,
            "message" : f"{service} is {'reachable' if is_up else 'unreachable'} (HTTP {r.status_code})"
        }
    except requests.exceptions.Timeout:
        return {"success": True, "service": service, "status": "timeout",
                "message": f"{service} is not responding (timeout)"}
    except Exception as e:
        return {"success": True, "service": service, "status": "unreachable",
                "message": f"{service} is unreachable: {str(e)[:50]}"}


# ─────────────────────────────────────────
# TOOL 3 — Diagnostique système local
# (utile si agent tourne sur la machine user — sinon info serveur)
# ─────────────────────────────────────────
def tool_system_diagnostic() -> dict:
    """
    Retourne les infos système basiques.
    """
    try:
        import psutil

        cpu     = psutil.cpu_percent(interval=1)
        ram     = psutil.virtual_memory()
        disk    = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")

        warnings = []
        if cpu > 80:
            warnings.append(f"CPU usage very high: {cpu}%")
        if ram.percent > 85:
            warnings.append(f"RAM usage very high: {ram.percent}%")
        if disk.percent > 90:
            warnings.append(f"Disk almost full: {disk.percent}%")

        return {
            "success" : True,
            "cpu"     : f"{cpu}%",
            "ram"     : f"{ram.percent}% used ({ram.available // (1024**3)}GB free)",
            "disk"    : f"{disk.percent}% used ({disk.free // (1024**3)}GB free)",
            "warnings": warnings,
            "os"      : f"{platform.system()} {platform.release()}"
        }
    except ImportError:
        return {"success": False, "message": "psutil not installed. Run: pip install psutil"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────
# TOOL 4 — Détecter le service mentionné
# ─────────────────────────────────────────
SERVICE_KEYWORDS = {
    "teams"     : ["teams", "microsoft teams"],
    "outlook"   : ["outlook", "email", "mail", "messagerie"],
    "onedrive"  : ["onedrive", "one drive"],
    "sharepoint": ["sharepoint", "share point"],
    "zoom"      : ["zoom"],
    "office365" : ["office", "office365", "microsoft 365", "o365"],
}

def detect_service_from_text(text: str) -> str | None:
    t = text.lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return service
    return None


# ─────────────────────────────────────────
# TOOL 5 — Générer guide de nettoyage cache
# ─────────────────────────────────────────
CACHE_GUIDES = {
    "teams": """To clear Microsoft Teams cache:
1. Completely quit Teams (right-click taskbar icon → Quit)
2. Press Win+R, type: %appdata%\\Microsoft\\Teams
3. Delete all files in these folders: Cache, blob_storage, databases, GPUCache, IndexedDB, Local Storage, tmp
4. Restart Teams and sign back in.
5. If issue persists, contact the IT helpdesk.""",

    "outlook": """To clear Outlook cache:
1. Close Outlook completely.
2. Press Win+R, type: %localappdata%\\Microsoft\\Outlook
3. Delete files ending in .ost (offline cache) — your emails will re-sync.
4. Also clear autocomplete: File → Options → Mail → Empty Auto-Complete List
5. Restart Outlook.
6. If issue persists, contact the IT helpdesk.""",

    "browser": """To clear browser cache:
1. Press Ctrl+Shift+Delete in your browser.
2. Select 'All time' as the time range.
3. Check: Cached images, Cookies, Browsing history.
4. Click 'Clear data'.
5. Restart the browser.
6. If issue persists, contact the IT helpdesk.""",
}

def tool_get_cache_guide(service: str) -> dict:
    key   = service.lower()
    guide = CACHE_GUIDES.get(key)
    if guide:
        return {"success": True, "service": service, "guide": guide}
    return {"success": False, "message": f"No cache guide for '{service}'"}