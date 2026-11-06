#!/usr/bin/env python3
"""Étape b : extrait 6 à 10 images clés de la vidéo source avec ffmpeg.

Usage : python3 scripts/extraire_images.py DOSSIER [--n 8]

Choisit une image au milieu de chaque plan (changements de scène détectés),
complète par des images régulièrement espacées, et ajoute toujours la toute
dernière image (TikTok y met souvent son logo et le @pseudo).
Produit travail/images/img_XX.jpg et travail/mosaique.jpg (vue d'ensemble).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import bandes_noires, dire, dossier_recherche, ffprobe, source_video  # noqa: E402


def coupures(video: Path) -> list[float]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                        "select='gt(scene,0.3)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def choisir_instants(duree: float, n: int, cuts: list[float]) -> list[float]:
    marge = min(0.3, duree / 20)
    bornes = [0.0] + [c for c in cuts if marge < c < duree - marge] + [duree]
    plans = [(a, b) for a, b in zip(bornes, bornes[1:]) if b - a > 0.4]
    milieux = [(a + b) / 2 for a, b in plans]
    if len(milieux) > n - 1:  # trop de plans : on en garde n-1 répartis dans le temps
        pas = len(milieux) / (n - 1)
        milieux = [milieux[int(i * pas)] for i in range(n - 1)]
    instants = list(milieux)
    # Compléter avec des instants réguliers, loin de ceux déjà pris.
    k = 1
    while len(instants) < n - 1 and k < 50:
        for i in range(k * (n - 1)):
            t = marge + (duree - 2 * marge) * (i + 0.5) / (k * (n - 1))
            if all(abs(t - u) > duree / (3 * n) for u in instants):
                instants.append(t)
            if len(instants) >= n - 1:
                break
        k += 1
    instants = sorted(instants)[: n - 1]
    instants.append(max(0.0, duree - 0.15))  # dernière image (fin TikTok, logo…)
    return instants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier")
    ap.add_argument("--n", type=int, default=8, help="nombre d'images (6 à 10)")
    a = ap.parse_args()
    n = max(6, min(10, a.n))

    dossier = dossier_recherche(a.dossier)
    video = source_video(dossier)
    info = ffprobe(video)
    duree = info["duree"]
    sortie = dossier / "travail" / "images"
    sortie.mkdir(parents=True, exist_ok=True)
    for ancien in sortie.glob("img_*.jpg"):
        ancien.unlink()

    cuts = coupures(video)
    instants = choisir_instants(duree, n, cuts)
    dire(f"{len(cuts)} changement(s) de plan détecté(s) ; {len(instants)} images extraites :")
    fichiers = []
    for i, t in enumerate(instants, 1):
        f = sortie / f"img_{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
                        "-frames:v", "1", "-q:v", "2", str(f)], check=True)
        if not f.exists():  # la toute fin peut être vide : on recule un peu
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-sseof", "-0.6", "-i", str(video),
                            "-frames:v", "1", "-q:v", "2", str(f)], check=True)
        fichiers.append((f, t))
        dire(f"  {f.relative_to(dossier)}  à {t:5.1f} s")

    # Mosaïque pour tout voir d'un coup d'œil.
    vignettes = [Image.open(f).convert("RGB") for f, _ in fichiers]
    h = 480
    vignettes = [im.resize((max(1, round(im.width * h / im.height)), h)) for im in vignettes]
    cols = min(5, len(vignettes))
    lignes = (len(vignettes) + cols - 1) // cols
    w = max(v.width for v in vignettes)
    mos = Image.new("RGB", (cols * w, lignes * (h + 28)), "white")
    dessin = ImageDraw.Draw(mos)
    for k, (v, (f, t)) in enumerate(zip(vignettes, fichiers)):
        x, y = (k % cols) * w, (k // cols) * (h + 28)
        mos.paste(v, (x, y + 28))
        dessin.text((x + 6, y + 8), f"{f.stem}  {t:.1f}s", fill="black")
    mos.save(dossier / "travail" / "mosaique.jpg", quality=85)
    dire("Mosaïque : travail/mosaique.jpg")
    bn = bandes_noires(video, duree)
    if bn:
        dire(f"Bandes noires : {bn}")


if __name__ == "__main__":
    main()
