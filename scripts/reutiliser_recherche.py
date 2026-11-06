#!/usr/bin/env python3
"""Réutilise les pistes et les vidéos déjà téléchargées d'une recherche précédente.

Gratuit : rien n'est retéléchargé ni recherché. Très utile quand plusieurs vidéos viennent
du même annonceur ou du même produit : on compare la nouvelle vidéo à tout ce qu'on a déjà.

Usage :
  python3 scripts/reutiliser_recherche.py NOUVEAU_DOSSIER --depuis ANCIEN_DOSSIER
  python3 scripts/comparer_videos.py NOUVEAU_DOSSIER --ids <la liste affichée>

Copie dans le nouveau dossier les pistes qui ont une vidéo téléchargée (mêmes numéros PXX),
sans leurs anciens résultats de comparaison, et relie leurs fichiers vidéo (sans les dupliquer).
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import charger_pistes, dire, dossier_recherche, erreur, sauver_pistes  # noqa: E402

RESULTATS = ("meme_video", "miroir", "distance_mediane", "couverture", "contenu_en_plus", "decalage_s",
             "passages", "plus_longue", "note", "passage_compare")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--depuis", required=True)
    a = ap.parse_args()
    nouveau, ancien = dossier_recherche(a.dossier), dossier_recherche(a.depuis)
    if nouveau == ancien:
        erreur("les deux dossiers sont identiques")

    pistes = charger_pistes(nouveau)
    deja = {p["id"] for p in pistes}
    if deja:
        erreur("le nouveau dossier a déjà des pistes : lance ce script juste après recuperer_video.py")
    (nouveau / "travail" / "candidats").mkdir(parents=True, exist_ok=True)
    copiees = []
    for p in charger_pistes(ancien):
        f = ancien / p["fichier"] if p.get("fichier") else None
        if not f or not f.exists():
            continue
        q = {k: v for k, v in p.items() if k not in RESULTATS}
        q["sources"] = list(dict.fromkeys(q.get("sources", []) + [f"recherche {ancien.name}"]))
        cible = nouveau / "travail" / "candidats" / f.name
        if not cible.exists():
            try:
                os.link(f, cible)          # même fichier, aucune place en plus
            except OSError:
                shutil.copy2(f, cible)
        q["fichier"] = str(cible.relative_to(nouveau))
        pistes.append(q)
        copiees.append(q["id"])
    sauver_pistes(nouveau, pistes)
    dire(f"{len(copiees)} piste(s) avec vidéo reprises de {ancien.name}.")
    dire("Compare-les ensuite (gratuit) :")
    dire(f"  python3 scripts/comparer_videos.py {a.dossier} --ids {','.join(copiees)}")


if __name__ == "__main__":
    main()
