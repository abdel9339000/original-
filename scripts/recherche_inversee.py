#!/usr/bin/env python3
"""Étape d : recherche d'image inversée avec SerpApi (Google Lens + Yandex Images).

Usage :
  python3 scripts/recherche_inversee.py DOSSIER            # annonce le coût, ne lance rien
  python3 scripts/recherche_inversee.py DOSSIER --ok       # lance (après le « ok » de l'utilisateur)

Options :
  --moteurs lens,yandex   moteurs à utiliser (défaut : les deux)
  --exact N               en plus, Google Lens « correspondances exactes » sur les N premières images
  --images img_02,img_05  seulement ces images (défaut : toutes celles de images/liens.txt)

Coût : 1 recherche SerpApi par image et par moteur (+ N pour --exact).
La clé est lue dans SERPAPI_KEY et n'est jamais affichée ni enregistrée.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (PLATEFORMES_VIDEO, ajouter_ou_fusionner, charger_pistes, dire, dossier_recherche,  # noqa: E402
                    erreur, masquer, plateforme, sauver_pistes)

API = "https://serpapi.com/search.json"


def appel(params: dict) -> dict:
    cle = os.environ.get("SERPAPI_KEY")
    if not cle:
        erreur("SERPAPI_KEY absente")
    url = API + "?" + urllib.parse.urlencode({**params, "api_key": cle})
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": type(e).__name__}


def restant() -> int:
    cle = os.environ.get("SERPAPI_KEY", "")
    u = "https://serpapi.com/account.json?" + urllib.parse.urlencode({"api_key": cle})
    try:
        return int(json.load(urllib.request.urlopen(u, timeout=20)).get("total_searches_left", 0))
    except Exception:
        return -1


def resultats(data: dict):
    """Toutes les pages trouvées (lien + titre), dans l'ordre."""
    for cle in ("exact_matches", "visual_matches", "image_results", "inline_videos", "videos"):
        for rang, item in enumerate(data.get(cle) or [], 1):
            if isinstance(item, dict) and str(item.get("link", "")).startswith("http"):
                yield cle, rang, item


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--ok", action="store_true", help="lancer pour de vrai (consomme des recherches)")
    ap.add_argument("--moteurs", default="lens,yandex")
    ap.add_argument("--exact", type=int, default=0)
    ap.add_argument("--images", default="")
    a = ap.parse_args()

    dossier = dossier_recherche(a.dossier)
    liens_txt = dossier / "images" / "liens.txt"
    if not liens_txt.exists():
        erreur("pas de images/liens.txt : lance d'abord mettre_en_ligne.sh")
    liens = [l.strip() for l in liens_txt.read_text().splitlines() if l.strip()]
    if a.images:
        voulues = {i.strip().removesuffix(".jpg") for i in a.images.split(",")}
        liens = [l for l in liens if Path(l).stem in voulues]
    moteurs = [m.strip() for m in a.moteurs.split(",") if m.strip()]
    for m in moteurs:
        if m not in ("lens", "yandex"):
            erreur(f"moteur inconnu : {m} (lens ou yandex)")
    exact = min(a.exact, len(liens)) if "lens" in moteurs or a.exact else 0
    cout = len(liens) * len(moteurs) + exact
    reste = restant()

    dire(f"Images : {len(liens)} ; moteurs : {', '.join(moteurs)}"
         + (f" ; + correspondances exactes Lens sur {exact} image(s)" if exact else ""))
    dire(f"Coût : {cout} recherche(s) SerpApi. Il en reste {reste if reste >= 0 else '?'} ce mois-ci "
         f"(250 gratuites par mois).")
    if not a.ok:
        dire("Rien n'a été lancé. Relance avec --ok après l'accord de l'utilisateur.")
        return
    if 0 <= reste < cout:
        erreur(f"pas assez de recherches SerpApi ({reste} restantes pour {cout} nécessaires)")

    brut = dossier / "travail" / "serpapi"
    brut.mkdir(parents=True, exist_ok=True)
    pistes = charger_pistes(dossier)
    avant = len(pistes)
    taches = []
    for i, lien in enumerate(liens):
        if "lens" in moteurs:
            taches.append(("google_lens", lien, {"engine": "google_lens", "url": lien}))
        if "yandex" in moteurs:
            taches.append(("yandex", lien, {"engine": "yandex_images", "url": lien}))
        if i < exact:
            taches.append(("google_lens_exact", lien, {"engine": "google_lens", "type": "exact_matches", "url": lien}))

    for nom_moteur, lien, params in taches:
        img = Path(lien).stem
        data = appel(params)
        (brut / f"{nom_moteur}_{img}.json").write_text(masquer(json.dumps(data, ensure_ascii=False, indent=1)),
                                                       encoding="utf-8")
        if data.get("error"):
            dire(f"  {nom_moteur:18} {img} : pas de résultat ({data['error']})")
            continue
        n = nv = 0
        for section, rang, item in resultats(data):
            n += 1
            pf = plateforme(item["link"])
            nv += pf in PLATEFORMES_VIDEO
            p = ajouter_ou_fusionner(pistes, {
                "url": item["link"],
                "sources": [nom_moteur],
                "vu_dans": [img],
                "titre": (item.get("title") or "")[:120],
                "site": item.get("source") or "",
                "miniature": item.get("thumbnail") or "",
            })
            if section == "exact_matches" or item.get("exact_matches") is True:
                p["correspondance_exacte"] = True
            p["meilleur_rang"] = min(p.get("meilleur_rang") or 999, rang)
        dire(f"  {nom_moteur:18} {img} : {n} résultat(s), dont {nv} sur des plateformes vidéo")

    for p in pistes:
        p["nb_images"] = len(p.get("vu_dans", []))
    sauver_pistes(dossier, pistes)
    dire(f"{len(pistes) - avant} nouvelle(s) piste(s) ; total {len(pistes)}. "
         f"Il reste {restant()} recherches SerpApi.")


if __name__ == "__main__":
    main()
