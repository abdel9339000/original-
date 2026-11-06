#!/usr/bin/env python3
"""Étape f (2/2) : télécharge les meilleures pistes et vérifie avec imagehash
que c'est bien la même vidéo que celle envoyée.

Usage :
  python3 scripts/comparer_videos.py DOSSIER --ids P03,P07
  python3 scripts/comparer_videos.py DOSSIER --ids P05 --fichier /chemin/video.mp4   # fichier déjà là
  python3 scripts/comparer_videos.py DOSSIER --ids P03 --passage 25.1-29.5           # un passage seulement

Méthode : 2 images par seconde dans chaque vidéo, empreinte perceptuelle (pHash)
de l'image entière, du centre et du haut (pour résister aux sous-titres ajoutés
et aux recadrages). Une image « correspond » si la distance est ≤ 10 sur 64.
  - couverture : part de la vidéo envoyée retrouvée dans la piste
  - en plus     : part de la piste absente de la vidéo envoyée (version plus longue ?)
Verdict : oui (≥ 60 %), partiel (≥ 30 %), non.
Produit travail/comparaison_PXX.jpg (côte à côte) pour vérifier à l'œil.
Gratuit : ne consomme ni SerpApi ni Trendtrack.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, ImageDraw, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (bandes_noires, charger_pistes, dire, dossier_recherche, erreur, ffprobe,  # noqa: E402
                    qualite, sauver_pistes, source_video)

FPS = 2
SEUIL = 10


def images(video: Path, dossier_tmp: Path, debut: float = 0.0, fin: float | None = None):
    dossier_tmp.mkdir(parents=True, exist_ok=True)
    coupe = ["-ss", f"{debut:.2f}"] + (["-to", f"{fin:.2f}"] if fin else [])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *coupe, "-i", str(video),
                    "-vf", f"fps={FPS},scale=320:-2", "-q:v", "4", str(dossier_tmp / "f_%05d.jpg")], check=True)
    return sorted(dossier_tmp.glob("f_*.jpg"))


def variantes(im: Image.Image):
    w, h = im.size
    return [
        im,
        im.crop((int(w * .15), int(h * .15), int(w * .85), int(h * .85))),  # centre
        im.crop((0, 0, w, int(h * .6))),                                      # haut (sans sous-titres)
    ]


def empreintes(fichiers, miroir=False):
    """Tableau (n_images, 3) d'empreintes 64 bits + masque des images exploitables."""
    hs, utiles = [], []
    for f in fichiers:
        im = Image.open(f).convert("L")
        if miroir:
            im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        utiles.append(ImageStat.Stat(im).stddev[0] > 8)  # écran uni = inutilisable
        hs.append([int(str(imagehash.phash(v)), 16) for v in variantes(im)])
    return np.array(hs, dtype=np.uint64), np.array(utiles, dtype=bool)


def distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distance minimale (toutes variantes croisées) entre chaque image de a et de b."""
    x = a[:, None, :, None] ^ b[None, :, None, :]
    return np.bitwise_count(x).min(axis=(2, 3))


def telecharger(p: dict, dest_dir: Path, refaire: bool = False) -> Path | None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    deja = [f for f in dest_dir.glob(f"{p['id']}.*") if not f.name.endswith(".part")]
    if deja and not refaire:  # déjà téléchargée : on la réutilise
        return deja[0]
    for ancien in deja:
        ancien.unlink()
    # Lien direct de la vidéo d'abord (pub Meta, Trendtrack) : la page elle-même est souvent bloquée.
    for url in [u for u in (p.get("media"), p.get("page") or p["url"]) if u]:
        try:
            r = subprocess.run(["yt-dlp", "--no-playlist", "--no-warnings", "-f", "bv*+ba/b", "-S", "res,br",
                                "--merge-output-format", "mp4", "-o", str(dest_dir / f"{p['id']}.%(ext)s"), url],
                               capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            continue
        sortie = [f for f in dest_dir.glob(f"{p['id']}.*") if not f.name.endswith(".part")]
        if r.returncode == 0 and sortie:
            return sortie[0]
    return None


def planche(ref_imgs, cand_imgs, paires, sortie: Path, titre: str, debut: float = 0.0):
    choix = [paires[int(i * (len(paires) - 1) / 2)] for i in range(3)] if len(paires) >= 3 else paires
    if not choix:
        return
    h = 360
    morceaux = []
    for i, j, d in choix:
        a, b = Image.open(ref_imgs[i]), Image.open(cand_imgs[j])
        a = a.resize((round(a.width * h / a.height), h))
        b = b.resize((round(b.width * h / b.height), h))
        bloc = Image.new("RGB", (a.width + b.width + 10, h + 24), "white")
        bloc.paste(a, (0, 24))
        bloc.paste(b, (a.width + 10, 24))
        ImageDraw.Draw(bloc).text((4, 6), f"envoyée {debut + i / FPS:.1f}s | piste {j / FPS:.1f}s | distance {d}",
                                  fill="black")
        morceaux.append(bloc)
    W = sum(m.width for m in morceaux) + 10 * (len(morceaux) - 1)
    out = Image.new("RGB", (W, h + 50), "white")
    ImageDraw.Draw(out).text((6, 4), titre, fill="black")
    x = 0
    for m in morceaux:
        out.paste(m, (x, 26))
        x += m.width + 10
    out.save(sortie, quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--ids", required=True)
    ap.add_argument("--fichier", help="vidéo déjà téléchargée (une seule piste dans --ids)")
    ap.add_argument("--retelecharger", action="store_true", help="retélécharger même si déjà là")
    ap.add_argument("--passage", help="ne comparer qu'un passage de la vidéo envoyée, ex. 25.1-29.5 "
                                      "(utile quand la pub est un montage de plusieurs vidéos)")
    a = ap.parse_args()
    debut, fin = 0.0, None
    if a.passage:
        try:
            debut, fin = (float(x) for x in a.passage.split("-"))
        except ValueError:
            erreur("--passage s'écrit DEBUT-FIN en secondes, ex. 25.1-29.5")

    dossier = dossier_recherche(a.dossier)
    travail = dossier / "travail"
    pistes = charger_pistes(dossier)
    ids = [i.strip() for i in a.ids.split(",") if i.strip()]
    if a.fichier and len(ids) != 1:
        erreur("--fichier va avec une seule piste")

    ref = source_video(dossier)
    info_ref = ffprobe(ref)
    tmp = Path(tempfile.mkdtemp(dir=travail))
    try:
        ref_imgs = images(ref, tmp / "ref", debut, fin)
        ref_h, ref_ok = empreintes(ref_imgs)
        if ref_ok.sum() == 0:
            erreur("la vidéo envoyée n'a que des écrans unis ?")
        for pid in ids:
            p = next((x for x in pistes if x["id"] == pid), None)
            if not p:
                dire(f"  {pid} : piste inconnue")
                continue
            if a.fichier:
                if not Path(a.fichier).exists():
                    erreur(f"fichier introuvable : {a.fichier}")
                (travail / "candidats").mkdir(parents=True, exist_ok=True)
                fichier = travail / "candidats" / f"{pid}{Path(a.fichier).suffix.lower()}"
                if Path(a.fichier).resolve() != fichier.resolve():
                    shutil.copy2(a.fichier, fichier)
            else:
                fichier = telecharger(p, travail / "candidats", a.retelecharger)
            if not fichier or not fichier.exists():
                p["meme_video"] = "?"
                p["comparaison"] = "téléchargement impossible"
                dire(f"  {pid} : téléchargement impossible ({p['url']})")
                continue
            info = ffprobe(fichier)
            cand_imgs = images(fichier, tmp / pid)
            resultats = []
            for miroir in (False, True):  # les copies volées sont souvent retournées (miroir)
                cand_h, cand_ok = empreintes(cand_imgs, miroir=miroir)
                D = distances(ref_h, cand_h)
                D[:, ~cand_ok] = 64
                trouve = (D.min(axis=1) <= SEUIL) & ref_ok
                resultats.append((trouve.sum() / ref_ok.sum(), miroir, D, cand_ok, trouve))
            couverture, miroir, D, cand_ok, trouve = max(resultats, key=lambda r: r[0])
            meilleur_j = D.argmin(axis=1)
            meilleur_d = D.min(axis=1)
            mediane = int(np.median(meilleur_d[ref_ok]))
            en_plus = 1 - ((D.min(axis=0) <= SEUIL) & cand_ok).sum() / max(1, cand_ok.sum())
            paires = [(i, int(meilleur_j[i]), int(meilleur_d[i])) for i in np.where(trouve)[0]]
            decalage = float(np.median([(j - i) / FPS - debut for i, j, _ in paires])) if paires else 0.0

            verdict = "oui" if couverture >= .6 else "partiel" if couverture >= .3 else "non"
            resultat = {
                "meme_video": verdict,
                "miroir": bool(miroir and verdict != "non"),
                "distance_mediane": mediane,
                "couverture": round(float(couverture), 2),
                "contenu_en_plus": round(float(en_plus), 2),
                "decalage_s": round(decalage, 1),
            }
            if a.passage:  # rangé à part : ne remplace pas la comparaison avec la vidéo entière
                p.setdefault("passages", {})[f"{debut:g}-{fin:g} s"] = resultat
            else:
                p.update(resultat)
            p.update({
                "duree": info.get("duree") or p.get("duree"),
                "qualite": qualite(info.get("largeur"), info.get("hauteur")),
                "debit_kbps": info.get("debit_kbps"),
                "bandes_noires": bandes_noires(fichier, info.get("duree") or 0),
                "fichier": str(fichier.relative_to(dossier)),
            })
            if paires:
                planche(ref_imgs, cand_imgs, paires, travail / f"comparaison_{pid}.jpg",
                        f"{pid} {p.get('plateforme')} {p.get('compte') or ''} : même vidéo = {verdict} "
                        f"({couverture:.0%})", debut)
            plus = ""
            duree_ref = (fin or info_ref["duree"]) - debut
            if not a.passage and verdict != "non" and (info.get("duree") or 0) > duree_ref + 1 and en_plus > .15:
                plus = f" ; version PLUS LONGUE (+{info['duree'] - duree_ref:.0f} s)"
                p["plus_longue"] = True
            if resultat["miroir"]:
                plus += " ; image RETOURNÉE (miroir) par rapport à la vidéo envoyée"
            if a.passage:
                plus += f" [comparé au passage {debut:g}-{fin:g} s]"
            dire(f"  {pid} {p.get('plateforme')} {p.get('compte') or ''} : même vidéo = {verdict} "
                 f"(couverture {couverture:.0%}, distance {mediane}/64, décalage {decalage:+.1f} s) ; {p['qualite']}, "
                 f"{info.get('duree')} s, {info.get('debit_kbps')} kb/s{plus}")
        sauver_pistes(dossier, pistes)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
