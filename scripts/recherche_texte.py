#!/usr/bin/env python3
"""Étape e (bis) : cherche le texte vu à l'écran dans les vidéos courtes indexées par Google
(TikTok, Instagram Reels, YouTube Shorts, Facebook…), via SerpApi.

Remplace la bibliothèque TikTok de Trendtrack.

Usage :
  python3 scripts/recherche_texte.py DOSSIER --phrase "quien inventó esto se merece un aumento"
  python3 scripts/recherche_texte.py DOSSIER --phrase "..." --phrase "..." --ok

Options :
  --phrase TEXTE     phrase à chercher, entre guillemets pour Google (répétable : 1 recherche chacune)
  --mots TEXTE       mots à chercher sans guillemets (répétable)
  --moteur courtes|videos   vidéos courtes Google (défaut) ou onglet Vidéos de Google
  --langue es        langue de l'interface Google (défaut : es)

Coût : 1 recherche SerpApi par --phrase / --mots.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (ajouter_ou_fusionner, annoncer_cout, charger_pistes, compte_depuis_url,  # noqa: E402
                    date_depuis_identifiant, dire, dossier_recherche, erreur, jour, sauver_brut,
                    sauver_pistes, serpapi, serpapi_restant)


def secondes(txt: str):
    m = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+)", (txt or "").strip())
    if not m:
        return None
    h, mi, s = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
    return h * 3600 + mi * 60 + s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--phrase", action="append", default=[])
    ap.add_argument("--mots", action="append", default=[])
    ap.add_argument("--moteur", choices=["courtes", "videos"], default="courtes")
    ap.add_argument("--langue", default="es")
    ap.add_argument("--ok", action="store_true")
    a = ap.parse_args()

    requetes = [f'"{p.strip(chr(34))}"' for p in a.phrase] + a.mots
    if not requetes:
        erreur("donne au moins --phrase ou --mots")
    dossier = dossier_recherche(a.dossier)
    dire("Recherches prévues : " + " ; ".join(requetes))
    if not annoncer_cout(len(requetes), a.ok):
        return

    engine = "google_short_videos" if a.moteur == "courtes" else "google_videos"
    cle_res = "short_video_results" if a.moteur == "courtes" else "video_results"
    pistes = charger_pistes(dossier)
    avant = len(pistes)
    for q in requetes:
        data = serpapi({"engine": engine, "q": q, "hl": a.langue})
        sauver_brut(dossier, f"{engine}_{q}", data)
        if data.get("error"):
            dire(f"  {q} : pas de résultat ({data['error']})")
            continue
        res = data.get(cle_res) or []
        dire(f"  {q} : {len(res)} vidéo(s)")
        for rang, r in enumerate(res, 1):
            if not str(r.get("link", "")).startswith("http"):
                continue
            p = ajouter_ou_fusionner(pistes, {
                "url": r["link"], "sources": [engine], "vu_dans": [f"texte {q}"],
                "titre": (r.get("title") or "")[:120],
                "compte": r.get("channel") or compte_depuis_url(r["link"]),
                "duree": secondes(r.get("duration")), "miniature": r.get("thumbnail") or "",
                "site": r.get("source") or "",
            })
            p["meilleur_rang"] = min(p.get("meilleur_rang") or 999, rang)
            if not p.get("date"):
                d, comment = date_depuis_identifiant(r["link"])
                if d:
                    p["date"], p["date_type"] = jour(d), f"publication (déduite de l'{comment})"
            dire(f"    {p['id']} {p['plateforme']:9} {(p.get('compte') or '?')[:22]:22} "
                 f"{r.get('duration') or '':>6}  {(r.get('title') or '')[:60]}")
    for p in pistes:
        p["nb_images"] = len([v for v in p.get("vu_dans", []) if not v.startswith("texte ")])
    sauver_pistes(dossier, pistes)
    dire(f"{len(pistes) - avant} nouvelle(s) piste(s). Il reste {serpapi_restant()} recherches SerpApi.")


if __name__ == "__main__":
    main()
