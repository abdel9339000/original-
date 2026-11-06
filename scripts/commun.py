"""Outils partagés par les scripts du Chercheur d'original.

Règle d'or : la clé SerpApi n'est jamais affichée ni écrite.
Tout texte qui sort d'un script passe par masquer().
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_UPLOADS = Path("/root/.claude/uploads")
EXTENSIONS_VIDEO = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi", ".3gp"}


# ---------------------------------------------------------------- sécurité
def masquer(texte) -> str:
    """Remplace la clé SerpApi par *** dans n'importe quel texte."""
    texte = str(texte)
    cle = os.environ.get("SERPAPI_KEY", "")
    if cle:
        texte = texte.replace(cle, "***")
    # Ceinture et bretelles : tout paramètre api_key=... est masqué.
    return re.sub(r"(api_key=)[^&\s\"']+", r"\1***", texte)


def dire(*morceaux):
    print(masquer(" ".join(str(m) for m in morceaux)), flush=True)


def erreur(message: str, code: int = 1):
    print(masquer("ERREUR : " + message), file=sys.stderr, flush=True)
    sys.exit(code)


# ---------------------------------------------------------------- dossiers
def slug(texte: str, longueur: int = 40) -> str:
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    texte = re.sub(r"[^a-zA-Z0-9]+", "-", texte).strip("-").lower()
    return (texte[:longueur].strip("-")) or "video"


def dossier_recherche(chemin: str) -> Path:
    d = Path(chemin)
    if not d.is_absolute():
        d = (Path.cwd() / d).resolve()
    if not d.exists():
        erreur(f"le dossier {d} n'existe pas")
    return d


def source_video(dossier: Path) -> Path:
    for f in sorted((dossier / "travail").glob("source.*")):
        if f.suffix.lower() in EXTENSIONS_VIDEO:
            return f
    erreur("vidéo source introuvable dans travail/ (lance d'abord recuperer_video.py)")


# ---------------------------------------------------------------- pistes.json
def charger_pistes(dossier: Path) -> list[dict]:
    f = dossier / "pistes.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def sauver_pistes(dossier: Path, pistes: list[dict]):
    f = dossier / "pistes.json"
    f.write_text(masquer(json.dumps(pistes, ensure_ascii=False, indent=2)) + "\n", encoding="utf-8")


def nouvel_id(pistes: list[dict]) -> str:
    n = max([int(p["id"][1:]) for p in pistes if re.fullmatch(r"P\d+", p.get("id", ""))] or [0])
    return f"P{n + 1:02d}"


def ajouter_ou_fusionner(pistes: list[dict], piste: dict) -> dict:
    """Ajoute une piste, ou fusionne avec celle qui a la même URL normalisée."""
    cle = normaliser_url(piste["url"])
    for p in pistes:
        if normaliser_url(p["url"]) == cle:
            for s in piste.get("sources", []):
                if s not in p.setdefault("sources", []):
                    p["sources"].append(s)
            for v in piste.get("vu_dans", []):
                if v not in p.setdefault("vu_dans", []):
                    p["vu_dans"].append(v)
            for k, v in piste.items():
                if k not in ("sources", "vu_dans", "id") and v not in (None, "") and not p.get(k):
                    p[k] = v
            return p
    piste = dict(piste)
    piste["id"] = nouvel_id(pistes)
    piste.setdefault("plateforme", plateforme(piste["url"]))
    pistes.append(piste)
    return piste


# ---------------------------------------------------------------- URLs
PARAMS_A_GARDER = {"v", "story_fbid", "id", "fbid", "video_id"}

PLATEFORMES = [
    ("tiktok.com", "TikTok"),
    ("douyin.com", "Douyin"),
    ("instagram.com", "Instagram"),
    ("facebook.com", "Facebook"),
    ("fb.watch", "Facebook"),
    ("fb.com", "Facebook"),
    ("youtube.com", "YouTube"),
    ("youtu.be", "YouTube"),
    ("pinterest.", "Pinterest"),
    ("pin.it", "Pinterest"),
    ("x.com", "X"),
    ("twitter.com", "X"),
    ("snapchat.com", "Snapchat"),
    ("reddit.com", "Reddit"),
    ("kuaishou.com", "Kuaishou"),
    ("bilibili.com", "Bilibili"),
    ("vk.com", "VK"),
    ("ok.ru", "OK.ru"),
    ("dailymotion.com", "Dailymotion"),
    ("vimeo.com", "Vimeo"),
    ("likee.", "Likee"),
    ("capcut.com", "CapCut"),
    ("threads.net", "Threads"),
    ("threads.com", "Threads"),
    ("aliexpress.", "AliExpress"),
    ("alibaba.com", "Alibaba"),
    ("1688.com", "1688"),
    ("amazon.", "Amazon"),
    ("temu.com", "Temu"),
    ("shein.", "Shein"),
    ("trendtrack.io", "Trendtrack"),
]

PLATEFORMES_VIDEO = {
    "TikTok", "Douyin", "Instagram", "Facebook", "YouTube", "Pinterest", "X",
    "Snapchat", "Reddit", "Kuaishou", "Bilibili", "VK", "OK.ru", "Dailymotion",
    "Vimeo", "Likee", "CapCut", "Threads",
}


def hote(url: str) -> str:
    h = urllib.parse.urlsplit(url).netloc.lower()
    h = h.split("@")[-1].split(":")[0]
    for prefixe in ("www.", "m.", "mobile.", "web.", "vm.", "vt."):
        if h.startswith(prefixe):
            h = h[len(prefixe):]
    return h


def plateforme(url: str) -> str:
    h = hote(url)
    for motif, nom in PLATEFORMES:
        if motif in h:
            return nom
    if re.search(r"\.(mp4|mov|webm|m3u8)(\?|$)", url.lower()):
        return "Fichier vidéo"
    return "Web"


def normaliser_url(url: str) -> str:
    p = urllib.parse.urlsplit(url.strip())
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if k in PARAMS_A_GARDER]
    chemin = p.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(("https", hote(url), chemin, urllib.parse.urlencode(q), ""))


# ---------------------------------------------------------------- dates
INSTAGRAM_EPOCH_MS = 1314220021721
X_EPOCH_MS = 1288834974657
ALPHABET_IG = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _valide(ts: float) -> bool:
    return dt.datetime(2010, 1, 1).timestamp() < ts < dt.datetime.now().timestamp() + 86400


def date_depuis_identifiant(url: str):
    """Date de publication cachée dans l'identifiant du post (TikTok, Instagram, X).

    Renvoie (datetime UTC, explication) ou (None, None). Ne télécharge rien.
    """
    try:
        pf = plateforme(url)
        if pf == "TikTok":
            m = re.search(r"/(?:video|photo)/(\d{15,})", url)
            if m:
                ts = int(m.group(1)) >> 32
                if _valide(ts):
                    return dt.datetime.fromtimestamp(ts, dt.timezone.utc), "identifiant TikTok"
        if pf == "Instagram":
            m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]{6,})", url)
            if m:
                code = m.group(1)[:11]
                media_id = 0
                for c in code:
                    media_id = media_id * 64 + ALPHABET_IG.index(c)
                ts = ((media_id >> 23) + INSTAGRAM_EPOCH_MS) / 1000
                if _valide(ts):
                    return dt.datetime.fromtimestamp(ts, dt.timezone.utc), "identifiant Instagram"
        if pf == "X":
            m = re.search(r"/status/(\d{10,})", url)
            if m:
                ts = ((int(m.group(1)) >> 22) + X_EPOCH_MS) / 1000
                if _valide(ts):
                    return dt.datetime.fromtimestamp(ts, dt.timezone.utc), "identifiant X"
    except (ValueError, OverflowError):
        pass
    return None, None


def compte_depuis_url(url: str) -> str:
    m = re.search(r"tiktok\.com/@([^/?#]+)", url)
    if m:
        return "@" + m.group(1)
    m = re.search(r"youtube\.com/@([^/?#]+)", url)
    if m:
        return "@" + m.group(1)
    m = re.search(r"(?:x|twitter)\.com/([^/?#]+)/status", url)
    if m:
        return "@" + m.group(1)
    m = re.search(r"facebook\.com/([^/?#]+)/(?:videos|posts|reels?)/", url)
    if m and m.group(1) not in ("watch", "reel", "share", "story.php"):
        return m.group(1)
    return ""


def jour(d) -> str:
    """'2025-03-14' depuis un datetime, un timestamp ou 'YYYYMMDD'."""
    if d is None or d == "":
        return ""
    if isinstance(d, (int, float)):
        d = dt.datetime.fromtimestamp(d, dt.timezone.utc)
    if isinstance(d, dt.datetime):
        return d.strftime("%Y-%m-%d")
    s = str(d)
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s[:10]


# ---------------------------------------------------------------- vidéo
def ffprobe(chemin: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(chemin)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return {}
    data = json.loads(r.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    fps = video.get("avg_frame_rate", "0/1")
    try:
        n, d = fps.split("/")
        fps = round(int(n) / int(d), 2) if int(d) else 0
    except ValueError:
        fps = 0
    fmt = data.get("format", {})
    return {
        "duree": round(float(fmt.get("duration", 0) or 0), 2),
        "largeur": video.get("width"),
        "hauteur": video.get("height"),
        "fps": fps,
        "debit_kbps": round(int(fmt.get("bit_rate", 0) or 0) / 1000),
        "audio": audio is not None,
        "taille_mo": round(int(fmt.get("size", 0) or 0) / 1e6, 2),
    }


def bandes_noires(chemin: Path, duree: float) -> str:
    """Détecte des bandes noires (signe de recadrage ou de remontage)."""
    if not duree:
        return ""
    debut = max(0.0, duree * 0.2)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{debut:.2f}", "-t", f"{min(10, duree):.2f}", "-i", str(chemin),
         "-vf", "cropdetect=24:2:0", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    if not crops:
        return ""
    w, h, x, y = map(int, crops[-1])
    info = ffprobe(chemin)
    W, H = info.get("largeur") or w, info.get("hauteur") or h
    if W - w > W * 0.04 or H - h > H * 0.04:
        return f"oui (zone utile {w}x{h} sur {W}x{H})"
    return "non"


def qualite(largeur, hauteur) -> str:
    if not largeur or not hauteur:
        return "?"
    cote = min(largeur, hauteur)
    if cote >= 1080:
        label = "HD 1080p+"
    elif cote >= 720:
        label = "HD 720p"
    elif cote >= 480:
        label = "SD"
    else:
        label = "basse"
    return f"{largeur}x{hauteur} ({label})"
