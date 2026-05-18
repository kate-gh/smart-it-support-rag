# ocr_handler.py
# OCR local — extrait le texte des captures d'écran IT
# Dépendances : pip install pytesseract pillow easyocr
# Tesseract binaire : https://github.com/UB-Mannheim/tesseract/wiki

import base64
import io
import re
import os
from PIL import Image

# ── Chemin Tesseract (Windows) ────────────────────────────────────────────────
# Adapte si ton chemin est différent
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── Chargement lazy des modèles ───────────────────────────────────────────────
_tesseract_ok  = False
_easyocr_reader = None

""" 
def _init_tesseract():
    global _tesseract_ok
    try:
        import pytesseract
        if os.path.exists(TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        pytesseract.get_tesseract_version()
        _tesseract_ok = True
        print("  [OCR] Tesseract disponible")
    except Exception as e:
        print(f"  [OCR] Tesseract indisponible : {e}")
"""
def _init_easyocr():
    global _easyocr_reader
    try:
        import easyocr
        _easyocr_reader = easyocr.Reader(["fr", "en"], gpu=False, verbose=False)
        print("  [OCR] EasyOCR chargé (fr+en)")
    except Exception as e:
        print(f"  [OCR] EasyOCR indisponible : {e}")

# Initialisation au démarrage
#_init_tesseract()
_init_easyocr()

# ── Prétraitement image ───────────────────────────────────────────────────────
def _preprocess(image: Image.Image) -> Image.Image:
    """
    Améliore la lisibilité pour l'OCR :
    - Conversion niveaux de gris
    - Redimensionnement si trop petite
    - Pas de binarisation agressive (conserve les UI sombres)
    """
    # Convertir en RGB si nécessaire
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    # Agrandir si trop petite (min 800px de large)
    w, h = image.size
    if w < 800:
        scale = 800 / w
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Niveaux de gris pour Tesseract
    return image


# ── OCR principal ─────────────────────────────────────────────────────────────
def extract_text_from_image(image_base64: str, image_type: str = "image/jpeg") -> str:
    """
    Extrait le texte d'une image encodée en base64.
    Essaie Tesseract en premier, puis EasyOCR, puis retourne "".
    """
    try:
        # Décoder base64 → PIL Image
        image_bytes = base64.b64decode(image_base64)
        image       = Image.open(io.BytesIO(image_bytes))
        image       = _preprocess(image)
    except Exception as e:
        print(f"  [OCR] Erreur décodage image : {e}")
        return ""

    text = ""

    # ── Tentative 1 : Tesseract ───────────────────────────────────────────────
    if _tesseract_ok:
        try:
            import pytesseract
            # Config optimisée pour les UI/fenêtres Windows
            config = "--oem 3 --psm 6 -l fra+eng"
            text   = pytesseract.image_to_string(image, config=config)
            text   = text.strip()
            print(f"  [OCR] Tesseract → {len(text)} chars")
        except Exception as e:
            print(f"  [OCR] Tesseract error: {e}")
            text = ""

    # ── Tentative 2 : EasyOCR (si Tesseract vide ou absent) ──────────────────
    if not text and _easyocr_reader is not None:
        try:
            import numpy as np
            img_array = np.array(image)
            results   = _easyocr_reader.readtext(img_array, detail=0, paragraph=True)
            text      = "\n".join(results).strip()
            print(f"  [OCR] EasyOCR → {len(text)} chars")
        except Exception as e:
            print(f"  [OCR] EasyOCR error: {e}")

    return _clean_ocr_text(text)


# ── Nettoyage du texte OCR ────────────────────────────────────────────────────
def _clean_ocr_text(text: str) -> str:
    """
    Nettoie les artefacts OCR courants dans les captures IT.
    Conserve les codes d'erreur, chemins, messages système.
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned = []

    for line in lines:
        line = line.strip()

        # Ignorer les lignes trop courtes (bruit OCR)
        if len(line) < 3:
            continue

        # Ignorer les lignes de caractères répétés (artefacts UI)
        if len(set(line.replace(" ", ""))) < 3:
            continue

        cleaned.append(line)

    result = "\n".join(cleaned)

    # Supprimer les espaces multiples
    result = re.sub(r" {3,}", "  ", result)

    # Limiter la taille (éviter de noyer le contexte)
    return result[:800]


# ── Extraction des éléments IT clés ──────────────────────────────────────────
def extract_it_keywords(text: str) -> dict:
    """
    Extrait les éléments IT importants du texte OCR :
    codes d'erreur, applications, chemins de fichiers.
    Utilisé pour enrichir la requête RAG.
    """
    result = {
        "error_codes" : [],
        "applications": [],
        "paths"       : [],
        "raw"         : text,
    }

    if not text:
        return result

    # Codes d'erreur Windows (0x..., BSOD, HTTP)
    error_codes = re.findall(
        r"(?:0x[0-9A-Fa-f]{4,8}|error\s+\w+|\d{3,4}(?:\s+error)?|"
        r"BSOD|STOP:\s+\w+|exception\s+\w+)",
        text, re.IGNORECASE
    )
    result["error_codes"] = list(set(error_codes))[:5]

    # Applications connues
    apps = re.findall(
        r"\b(Outlook|Teams|Excel|Word|Chrome|Firefox|Edge|Windows|"
        r"SharePoint|OneDrive|VPN|Cisco|Office|Zoom|Slack|SAP)\b",
        text, re.IGNORECASE
    )
    result["applications"] = list(set(apps))[:5]

    # Chemins de fichiers
    paths = re.findall(r"[A-Z]:\\[\w\\.\-\s]+", text)
    result["paths"] = paths[:3]

    return result


# ── Formatage pour le contexte du chatbot ────────────────────────────────────
def format_ocr_for_chat(text: str, user_message: str = "", lang: str = "en") -> str:
    """
    Formate le texte OCR à injecter dans le message utilisateur.
    """
    if not text:
        return user_message

    keywords = extract_it_keywords(text)

    # Construire le résumé contextuel
    parts = []

    if keywords["error_codes"]:
        codes = ", ".join(keywords["error_codes"])
        parts.append(f"Error codes: {codes}")

    if keywords["applications"]:
        apps = ", ".join(keywords["applications"])
        parts.append(f"Application: {apps}")

    # Texte OCR brut (tronqué)
    ocr_summary = text[:400] if len(text) > 400 else text

    if lang == "fr":
        context = (
            f"\n\n[Capture d'écran analysée par OCR]\n"
            f"{'. '.join(parts) + '. ' if parts else ''}"
            f"Texte visible :\n{ocr_summary}"
        )
    else:
        context = (
            f"\n\n[Screenshot analyzed by OCR]\n"
            f"{'. '.join(parts) + '. ' if parts else ''}"
            f"Visible text:\n{ocr_summary}"
        )

    base = user_message if user_message else (
        "Problème IT détecté dans cette capture d'écran"
        if lang == "fr"
        else
        "IT issue detected in this screenshot"
    )

    return base + context