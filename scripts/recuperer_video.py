#!/usr/bin/env python3
"""Étape a : récupère la vidéo et crée le dossier de la recherche.

Usage :
  python3 scripts/recuperer_video.py auto  [--nom NOM]   # dernière vidéo jointe avec le « + »
  python3 scripts/recuperer_video.py CHEMIN [--nom NOM]  # un fichier précis
  python3 scripts/recuperer_video.py URL    [--nom NOM]  # un lien (TikTok, Insta, FB…)

Crée recherches/<date>/<nom>/ avec :
  travail/source.<ext>   la vidéo (jamais poussée : travail/ est ignoré par git)
  pistes.json            la liste des pistes (le lien envoyé devient la piste P01)
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (DOSSIER_UPLOADS, EXTENSIONS_VIDEO, RACINE, ajouter_ou_fusionner, charger_pistes,  # noqa: E402
                    compte_depuis_url, date_depuis_identifiant, dire, erreur, ffprobe, jour, masquer,
                    qualite, sauver_pistes, slug)


def derniere_video_jointe() -> Path:
    videos = [f for f in DOSSIER_UPLOADS.rglob("*") if f.is_file() and f.suffix.lower() in EXTENSIONS_VIDEO]
    if not videos:
        erreur(f"aucune vidéo jointe trouvée dans {DOSSIER_UPLOADS}. Envoie-la avec le « + ».")
    return max(videos, key=lambda f: f.stat().st_mtime)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entree", help="auto, un chemin de fichier ou un lien")
    ap.add_argument("--nom", help="nom court de la recherche (sinon déduit)")
    a = ap.parse_args()

    est_lien = a.entree.startswith(("http://", "https://"))
    infos_lien = None
    if est_lien:
        dire("Lecture des infos du lien (sans télécharger)…")
        r = subprocess.run(["yt-dlp", "--dump-json", "--no-playlist", "--no-warnings", a.entree],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and r.stdout.strip():
            infos_lien = json.loads(r.stdout.splitlines()[0])
        nom = a.nom or (infos_lien and f"{infos_lien.get('uploader') or ''}-{infos_lien.get('id') or ''}") or "lien"
    else:
        fichier = derniere_video_jointe() if a.entree == "auto" else Path(a.entree)
        if not fichier.exists():
            erreur(f"fichier introuvable : {fichier}")
        nom = a.nom or fichier.stem

    dossier = RACINE / "recherches" / dt.date.today().isoformat() / slug(nom)
    travail = dossier / "travail"
    travail.mkdir(parents=True, exist_ok=True)
    (dossier / "images").mkdir(exist_ok=True)
    for ancien in travail.glob("source.*"):
        ancien.unlink()

    if est_lien:
        dire("Téléchargement de la vidéo envoyée…")
        r = subprocess.run(["yt-dlp", "--no-playlist", "--no-warnings", "-f", "bv*+ba/b", "-S", "res,br",
                            "--merge-output-format", "mp4", "-o", str(travail / "source.%(ext)s"), a.entree],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            erreur("yt-dlp n'a pas pu télécharger ce lien : " + (r.stderr.strip().splitlines() or ["?"])[-1]
                   + "\nAstuce : télécharge la vidéo sur ton téléphone et envoie-la avec le « + ».")
        source = next(travail.glob("source.*"))
    else:
        source = travail / ("source" + fichier.suffix.lower())
        shutil.copy2(fichier, source)

    info = ffprobe(source)
    pistes = charger_pistes(dossier)
    if est_lien:
        d, comment = (None, None)
        if infos_lien and (infos_lien.get("timestamp") or infos_lien.get("upload_date")):
            d, comment = infos_lien.get("timestamp") or infos_lien.get("upload_date"), "yt-dlp"
        else:
            d, comment = date_depuis_identifiant(a.entree)
        ajouter_ou_fusionner(pistes, {
            "url": (infos_lien or {}).get("webpage_url") or a.entree,
            "sources": ["lien envoyé"],
            "compte": (infos_lien or {}).get("uploader_id") or (infos_lien or {}).get("uploader")
                      or compte_depuis_url(a.entree),
            "date": jour(d), "date_type": f"publication ({comment})" if comment else "",
            "duree": (infos_lien or {}).get("duration"),
            "qualite": qualite((infos_lien or {}).get("width"), (infos_lien or {}).get("height")),
            "titre": ((infos_lien or {}).get("title") or "")[:120],
        })
    sauver_pistes(dossier, pistes)
    (travail / "source_info.json").write_text(masquer(json.dumps(
        {"entree": a.entree if est_lien else str(fichier), **info}, ensure_ascii=False, indent=2)), encoding="utf-8")

    dire(f"Dossier : {dossier.relative_to(RACINE)}")
    dire(f"Vidéo   : {info.get('duree')} s, {qualite(info.get('largeur'), info.get('hauteur'))}, "
         f"{info.get('fps')} img/s, {info.get('debit_kbps')} kb/s, son : {'oui' if info.get('audio') else 'non'}")
    nom_fichier = source.name if est_lien else fichier.name
    dire(f"Nom du fichier d'origine : {nom_fichier}")


if __name__ == "__main__":
    main()
