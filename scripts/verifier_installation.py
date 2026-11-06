#!/usr/bin/env python3
"""Vérifie que tout est prêt, sans jamais afficher la clé SerpApi.

Usage : python3 scripts/verifier_installation.py
Ne consomme aucune recherche SerpApi (la page « compte » est gratuite).
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import masquer  # noqa: E402

ok_total = True


def ligne(ok: bool, nom: str, detail: str = ""):
    global ok_total
    ok_total &= ok
    print(masquer(f"{'OK ' if ok else 'KO '} {nom}{' : ' + detail if detail else ''}"))


# 1. Clé SerpApi : on dit seulement si elle est là.
cle = os.environ.get("SERPAPI_KEY", "")
ligne(bool(cle), "SERPAPI_KEY", "présente" if cle else "absente (à ajouter dans les variables de l'environnement)")

# 2. Outils
for outil, args in (("yt-dlp", ["--version"]), ("ffmpeg", ["-version"]), ("ffprobe", ["-version"])):
    chemin = shutil.which(outil)
    if chemin:
        v = subprocess.run([outil, *args], capture_output=True, text=True).stdout.splitlines()
        ligne(True, outil, (v[0] if v else "").replace("Copyright", "").strip()[:60])
    else:
        ligne(False, outil, "absent")

try:
    import imagehash  # noqa: F401
    import PIL

    ligne(True, "imagehash", f"{imagehash.__version__} (Pillow {PIL.__version__})")
except ImportError as e:
    ligne(False, "imagehash", f"absent ({e.name}) : pip install imagehash")

# 3. Sites
for site in ("https://www.tiktok.com/", "https://www.instagram.com/", "https://www.facebook.com/",
             "https://serpapi.com/", "https://raw.githubusercontent.com/"):
    try:
        req = urllib.request.Request(site, headers={"User-Agent": "Mozilla/5.0"})
        code = urllib.request.urlopen(req, timeout=15).status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # réseau coupé, DNS, proxy…
        ligne(False, site, f"ne répond pas ({type(e).__name__})")
        continue
    # 3xx/4xx = le site répond (il refuse juste les robots) ; seul « rien » est un échec.
    ligne(code < 500, site, f"répond (HTTP {code})")

# 4. Recherches SerpApi restantes (gratuit)
if cle:
    try:
        u = "https://serpapi.com/account.json?" + urllib.parse.urlencode({"api_key": cle})
        d = json.load(urllib.request.urlopen(u, timeout=20))
        if d.get("error"):
            ligne(False, "compte SerpApi", d["error"])
        else:
            ligne(True, "compte SerpApi",
                  f"{d.get('plan_name')} : {d.get('total_searches_left')} recherches restantes "
                  f"sur {d.get('searches_per_month')} ce mois-ci")
    except Exception as e:
        ligne(False, "compte SerpApi", type(e).__name__)

print()
print("Tout est prêt." if ok_total else "Il manque quelque chose (voir les lignes KO).")
print("Rappel : les crédits Trendtrack se vérifient avec l'outil Trendtrack « check_credits ».")
sys.exit(0 if ok_total else 1)
