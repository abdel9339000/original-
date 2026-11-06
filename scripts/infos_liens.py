#!/usr/bin/env python3
"""Étape f (1/2) : lit date, auteur, durée et qualité de chaque piste, SANS télécharger.

Usage :
  python3 scripts/infos_liens.py DOSSIER                 # pistes vidéo les plus prometteuses (max 25)
  python3 scripts/infos_liens.py DOSSIER --ids P03,P07   # seulement ces pistes
  python3 scripts/infos_liens.py DOSSIER --max 40

Utilise « yt-dlp --dump-json » (aucun téléchargement). Si yt-dlp est bloqué
(Instagram et Facebook demandent souvent une connexion), la date est déduite
de l'identifiant du post quand c'est possible (TikTok, Instagram, X).
Gratuit : ne consomme ni SerpApi ni Trendtrack.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (PLATEFORMES_VIDEO, charger_pistes, compte_depuis_url, date_depuis_identifiant, dire,  # noqa: E402
                    dossier_recherche, jour, qualite, sauver_pistes)


def priorite(p: dict):
    return (
        0 if "lien envoyé" in p.get("sources", []) else 1,
        0 if p.get("correspondance_exacte") else 1,
        -(p.get("nb_images") or 0),
        p.get("meilleur_rang") or 999,
    )


def lire(url: str) -> tuple[dict | None, str]:
    try:
        r = subprocess.run(["yt-dlp", "--dump-json", "--skip-download", "--no-playlist", "--no-warnings",
                            "--socket-timeout", "20", url], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return None, "délai dépassé"
    if r.returncode == 0 and r.stdout.strip():
        return json.loads(r.stdout.splitlines()[0]), ""
    msg = (r.stderr.strip().splitlines() or ["?"])[-1]
    for motif, court in (("login", "connexion requise"), ("log in", "connexion requise"),
                         ("cookies", "connexion requise"), ("private", "post privé"),
                         ("not available", "indisponible ou supprimé"), ("removed", "supprimé"),
                         ("Unsupported URL", "pas une vidéo"), ("No video", "pas une vidéo"),
                         ("404", "introuvable (supprimé ?)")):
        if motif.lower() in msg.lower():
            return None, court
    return None, msg.replace("ERROR: ", "")[:100]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--ids", default="")
    ap.add_argument("--max", type=int, default=25)
    ap.add_argument("--refaire", action="store_true", help="relire même les pistes déjà lues")
    a = ap.parse_args()

    dossier = dossier_recherche(a.dossier)
    pistes = charger_pistes(dossier)
    if a.ids:
        ids = {i.strip() for i in a.ids.split(",")}
        choix = [p for p in pistes if p["id"] in ids]
    else:
        choix = sorted([p for p in pistes if p.get("plateforme") in PLATEFORMES_VIDEO
                        and (a.refaire or not p.get("lu"))], key=priorite)[: a.max]
    if not choix:
        dire("Aucune piste à lire.")
        return

    for p in choix:
        info, err = lire(p["url"])
        p["lu"] = True
        if info:
            uid = str(info.get("uploader_id") or "")
            if p["plateforme"] == "TikTok":  # uploader = @pseudo ; uploader_id = numéro interne
                compte = info.get("uploader") or compte_depuis_url(p["url"])
                compte = ("@" + compte.lstrip("@")) if compte else ""
            else:
                compte = (uid if uid and not uid.isdigit() else "") or info.get("uploader") or info.get("channel")
            p["compte"] = compte or p.get("compte") or ""
            p["nom_affiche"] = info.get("uploader") or info.get("channel") or ""
            d = info.get("timestamp") or info.get("upload_date")
            if d:
                p["date"], p["date_type"] = jour(d), "publication (yt-dlp)"
            p["duree"] = info.get("duration") or p.get("duree")
            l, h = info.get("width"), info.get("height")
            if not (l and h):  # meilleure qualité parmi les formats proposés
                vids = [f for f in info.get("formats") or [] if f.get("height") and f.get("vcodec") != "none"]
                if vids:
                    best = max(vids, key=lambda f: (f["height"] or 0) * (f.get("width") or 0))
                    l, h = best.get("width"), best.get("height")
            p["qualite"] = qualite(l, h)
            p["vues"] = info.get("view_count")
            p["titre"] = (info.get("title") or info.get("description") or p.get("titre") or "")[:120]
            p["page"] = info.get("webpage_url") or p["url"]
            p.pop("erreur_lecture", None)
        else:
            p["erreur_lecture"] = err
            p["compte"] = p.get("compte") or compte_depuis_url(p["url"])
        if not p.get("date"):
            d, comment = date_depuis_identifiant(p.get("page") or p["url"])
            if d:
                p["date"], p["date_type"] = jour(d), f"publication (déduite de l'{comment})"
        etat = "ok" if info else f"bloqué : {err}"
        dire(f"  {p['id']} {p['plateforme']:9} {p.get('compte') or '?':22} {p.get('date') or '?':10} "
             f"{str(p.get('duree') or '?'):>6}s  {p.get('qualite') or '?':22} [{etat}]")
    sauver_pistes(dossier, pistes)


if __name__ == "__main__":
    main()
