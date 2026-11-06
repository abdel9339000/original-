#!/usr/bin/env python3
"""Ajoute une piste à la main (trouvée par Trendtrack, un filigrane, une recherche…).

Usage :
  python3 scripts/ajouter_piste.py DOSSIER --url URL --source trendtrack_meta \\
      [--compte NOM] [--date AAAA-MM-JJ] [--type-date "première vue Trendtrack"] \\
      [--media URL_DU_FICHIER_VIDEO] [--duree SECONDES] [--note TEXTE]

--media : lien direct vers le fichier vidéo (ex. « Media URL » de Trendtrack),
          utilisé par comparer_videos.py quand la page elle-même n'est pas lisible.
Si l'URL existe déjà, les infos sont fusionnées.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ajouter_ou_fusionner, charger_pistes, dire, dossier_recherche, sauver_pistes  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--url", required=True)
    ap.add_argument("--source", required=True,
                    help="ex. trendtrack_meta, trendtrack_scan, trendtrack_tiktok, trendtrack_produit, filigrane")
    ap.add_argument("--compte", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--type-date", default="")
    ap.add_argument("--media", default="")
    ap.add_argument("--duree", type=float)
    ap.add_argument("--titre", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    dossier = dossier_recherche(a.dossier)
    pistes = charger_pistes(dossier)
    p = ajouter_ou_fusionner(pistes, {
        "url": a.url, "sources": [a.source], "compte": a.compte, "date": a.date,
        "date_type": a.type_date, "media": a.media, "duree": a.duree, "titre": a.titre[:120],
        "note": a.note,
    })
    # Une info donnée à la main remplace l'ancienne.
    for champ, val in (("compte", a.compte), ("date", a.date), ("date_type", a.type_date),
                       ("media", a.media), ("note", a.note)):
        if val:
            p[champ] = val
    if a.duree:
        p["duree"] = a.duree
    sauver_pistes(dossier, pistes)
    dire(f"Piste {p['id']} : {p['plateforme']} {p.get('compte') or ''} {p['url']}")


if __name__ == "__main__":
    main()
