#!/usr/bin/env python3
"""Étape g : classe les pistes et affiche le tableau du rapport (Markdown).

Usage : python3 scripts/tableau.py DOSSIER [--tout]

Classement des versions confirmées (même vidéo = oui ou partiel) :
  1. date la plus ancienne   2. version la plus longue
  3. meilleure qualité       4. sans bandes noires (pas recadrée)
Donne aussi un niveau de confiance (élevée / moyenne / faible) avec ses raisons.
L'agent relit et corrige à la main si besoin (sous-titres ajoutés, etc.).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import charger_pistes, dossier_recherche, normaliser_url  # noqa: E402

OUI_NON = {"oui": "oui", "partiel": "en partie", "non": "non", "?": "? (pas pu vérifier)"}


def pixels(p):
    m = re.match(r"(\d+)x(\d+)", p.get("qualite") or "")
    return int(m.group(1)) * int(m.group(2)) if m else 0


def cle_classement(p):
    return (p.get("date") or "9999-99-99", -(p.get("duree") or 0), -pixels(p),
            1 if str(p.get("bandes_noires", "")).startswith("oui") else 0)


def date_txt(p):
    d = p.get("date") or "?"
    t = p.get("date_type") or ""
    if "Trendtrack" in t:
        return f"{d} (vue par Trendtrack)"
    if "bibliothèque Meta" in t:
        return f"{d} (début de la pub)"
    if "identifiant" in t:
        return f"{d} (calculée)"
    return d


def ligne(p):
    lien = p.get("page") or p["url"]
    if p.get("plateforme") != "Fichier vidéo":  # enlève les paramètres de suivi (?is_from_webapp…)
        lien = normaliser_url(lien)
    court = re.sub(r"^https?://(www\.)?", "", lien)
    court = court if len(court) <= 45 else court[:42] + "…"
    duree = f"{p['duree']:.0f} s" if isinstance(p.get("duree"), (int, float)) and p.get("duree") else "?"
    qual = p.get("qualite") or "?"
    if str(p.get("bandes_noires", "")).startswith("oui"):
        qual += ", bandes noires"
    meme = OUI_NON.get(p.get("meme_video"), "non vérifié")
    if p.get("miroir"):
        meme += " (miroir)"
    for passage, r in (p.get("passages") or {}).items():
        if r.get("meme_video") in ("oui", "partiel"):
            meme += f" ; passage {passage} : {OUI_NON[r['meme_video']]}"
    if p.get("plus_longue"):
        duree += " (plus longue)"
    if p.get("erreur_lecture") and not p.get("meme_video"):
        meme += f" ({p['erreur_lecture']})"
    return (f"| {p['id']} | {p.get('plateforme', '?')} | {p.get('compte') or '?'} | {date_txt(p)} | "
            f"[{court}]({lien}) | {meme} | {qual} | {duree} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier")
    ap.add_argument("--tout", action="store_true", help="montrer aussi les pistes non vérifiées")
    a = ap.parse_args()
    pistes = charger_pistes(dossier_recherche(a.dossier))

    confirmees = sorted([p for p in pistes if p.get("meme_video") in ("oui", "partiel")], key=cle_classement)
    verifiees = [p for p in pistes if p not in confirmees and (p.get("meme_video") or p.get("lu")
                 or any(s.startswith(("trendtrack", "lien", "filigrane")) for s in p.get("sources", [])))]
    verifiees.sort(key=cle_classement)
    autres = [p for p in pistes if p not in confirmees and p not in verifiees]

    print("| # | Plateforme | Compte | Date | Lien | Même vidéo | Qualité | Durée |")
    print("|---|---|---|---|---|---|---|---|")
    for p in confirmees + verifiees + (sorted(autres, key=cle_classement) if a.tout else []):
        print(ligne(p))
    if autres and not a.tout:
        print(f"\n_{len(autres)} autre(s) piste(s) non vérifiée(s) (ressemblances visuelles) : voir pistes.json._")

    print("\n## Classement proposé\n")
    if not confirmees:
        print("Aucune version confirmée comme identique : **confiance faible**. "
              "Pistes à creuser : celles marquées « non vérifié » ou « ? » ci-dessus.")
        return
    for rang, p in enumerate(confirmees[:5], 1):
        print(f"{rang}. {p['id']} {p.get('plateforme')} {p.get('compte') or '?'} : {date_txt(p)}, "
              f"{p.get('duree') or '?'} s, {p.get('qualite') or '?'}")
    best = confirmees[0]
    raisons, niveau = [], 2
    if best.get("meme_video") != "oui":
        niveau -= 1
        raisons.append("la meilleure piste n'est identique qu'en partie")
    if not best.get("date"):
        niveau -= 1
        raisons.append("sa date est inconnue")
    elif "Trendtrack" in (best.get("date_type") or ""):
        niveau -= 1
        raisons.append("sa date est celle où Trendtrack l'a vue, pas forcément sa publication")
    sans_date = [p for p in confirmees[1:] if not p.get("date")]
    if sans_date:
        niveau -= 1
        raisons.append(f"{len(sans_date)} autre(s) copie(s) identique(s) sans date connue, peut-être plus "
                       "ancienne(s) (" + ", ".join(p["id"] for p in sans_date[:6]) + ")")
    bloquees = [p for p in verifiees if p.get("meme_video") == "?"
                or (p.get("erreur_lecture") and not p.get("date") and p.get("meme_video") != "non")]
    if bloquees:
        niveau -= 1
        raisons.append(f"{len(bloquees)} piste(s) n'ont pas pu être vérifiées (" +
                       ", ".join(p["id"] for p in bloquees[:6]) + ")")
    plus_anciennes = [p for p in verifiees if p.get("date") and p["date"] < (best.get("date") or "9")
                      and p.get("meme_video") != "non"]
    if plus_anciennes:
        niveau -= 1
        raisons.append("des pistes plus anciennes restent non confirmées (" +
                       ", ".join(p["id"] for p in plus_anciennes[:6]) + ")")
    if len(confirmees) > 1 and confirmees[1].get("date") == best.get("date"):
        niveau -= 1
        raisons.append("une autre version a la même date")
    if not raisons:
        raisons.append("même vidéo confirmée, date de publication réelle, rien de plus ancien trouvé")
    label = "élevée" if niveau >= 2 else "moyenne" if niveau == 1 else "faible"
    print(f"\n**Original le plus probable : {best['id']} ({best.get('plateforme')} {best.get('compte') or '?'}, "
          f"{date_txt(best)})** ; confiance **{label}** : " + " ; ".join(raisons) + ".")


if __name__ == "__main__":
    main()
