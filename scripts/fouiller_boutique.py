#!/usr/bin/env python3
"""Étape e (ter) : fouille la boutique d'un annonceur pour trouver la boutique qu'elle copie.

Gratuit : ne consomme ni SerpApi ni Trendtrack (simple lecture des pages publiques).

Usage :
  python3 scripts/fouiller_boutique.py DOSSIER --site mivitalba.com [--page URL_DE_LA_PAGE_DE_VENTE]
  python3 scripts/fouiller_boutique.py DOSSIER --site fresito.es --page "https://fresito.es/pages/..." --essayer-marques

Ce qu'il cherche (les copieurs laissent souvent ces traces) :
  - les produits de la boutique et leur date de création (Shopify : /products.json) ;
  - dans la page de vente : des images chargées depuis le stockage d'UNE AUTRE boutique Shopify,
    un titre ou une adresse dans une autre langue, l'outil de clonage utilisé ;
  - des noms de marque inconnus dans les noms de fichiers (ex. « favicon-frigora-style.png ») ;
  - avec --essayer-marques : essaie <marque>.fr/.com/.es/.de/.it et liste leurs produits.
"""
import argparse
import collections
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import dire, dossier_recherche  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0"}
OUTILS_CLONAGE = {"myshopage": "Shopage (sait cloner des pages)", "gempages": "GemPages", "gemcommerce": "GemPages",
                  "pagefly": "PageFly", "replo": "Replo", "zipify": "Zipify", "shogun": "Shogun"}
MOTS_BANALS = set("""img image images icon logo favicon file files style styles banner bg background thumb thumbnail
poster demo video photo product products main hero frame copy final new old jpg jpeg png webp gif mp4 svg cdn shopify
adv advertorial page pages section block slide slider review reviews avatar avatars medios portada rebajas sale
""".split())


def lire(url: str, json_ok=False):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            data = r.read().decode("utf-8", "ignore")
            return json.loads(data) if json_ok else data
    except Exception:
        return None


def produits(site: str):
    d = lire(f"https://{site}/products.json?limit=250", json_ok=True)
    return (d or {}).get("products") or []


def ids_magasin(texte: str):
    """Identifiants de stockage Shopify (cdn.shopify.com/s/files/1/AAAA/BBBB/CCCC/...)."""
    return collections.Counter(re.findall(r"/s/files/1/(\d{3,4}/\d{3,4}/\d{3,4})/", texte))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--site", required=True, help="domaine de la boutique, ex. mivitalba.com")
    ap.add_argument("--page", default="", help="page de vente (lien de la pub)")
    ap.add_argument("--essayer-marques", action="store_true")
    a = ap.parse_args()
    dossier = dossier_recherche(a.dossier)
    site = a.site.replace("https://", "").replace("http://", "").strip("/")

    accueil = lire(f"https://{site}/") or ""
    nom = re.search(r"<title>(.*?)</title>", accueil, re.S)
    dire(f"Boutique {site} : « {html.unescape(nom.group(1).strip()) if nom else '?'} »"
         f"{' (Shopify)' if 'cdn.shopify.com' in accueil or 'Shopify' in accueil else ''}")
    propre = ids_magasin(accueil).most_common(1)
    propre = propre[0][0] if propre else ""
    for p in sorted(produits(site), key=lambda p: p.get("created_at") or ""):
        v = (p.get("variants") or [{}])[0]
        dire(f"  produit créé le {(p.get('created_at') or '')[:10]} : {p.get('title', '')[:70]} ({v.get('price')})")

    page = lire(a.page) if a.page else ""
    textes = accueil + (page or "")
    if a.page:
        if not page:
            dire("Page de vente illisible.")
        else:
            t = re.search(r"<title>(.*?)</title>", page, re.S)
            dire(f"Page de vente : « {html.unescape(t.group(1).strip()) if t else '?'} »")
            dire(f"  adresse : {a.page}")
            etrangers = {k: n for k, n in ids_magasin(page).items() if propre and k != propre}
            if etrangers:
                dire("  !! Images chargées depuis le stockage d'UNE AUTRE boutique Shopify : "
                     + ", ".join(f"{k} ({n} fichiers)" for k, n in etrangers.items())
                     + " -> page sans doute clonée sur une autre boutique")
            for outil in sorted({o for cle, o in OUTILS_CLONAGE.items() if cle in page}):
                dire(f"  outil de page : {outil}")

    fichiers = set(re.findall(r"/files/([^\"'?\s/]+?\.(?:jpg|jpeg|png|webp|gif|mp4|svg|ico))", textes))
    mots = collections.Counter()
    nom_site = re.sub(r"^(mi|my|get|try|shop|la|le)", "", site.split(".")[0].lower())
    for f in fichiers:
        for m in re.findall(r"[a-z]{4,}", f.lower()):
            if m not in MOTS_BANALS and nom_site not in m and m not in nom_site:
                mots[m] += 1
    if mots:
        dire("Mots inconnus dans les noms de fichiers (marque copiée ?) : "
             + ", ".join(f"{m} ({n})" for m, n in mots.most_common(12)))

    if a.essayer_marques:
        for marque, _ in mots.most_common(5):
            for ext in ("fr", "com", "es", "de", "it"):
                ps = produits(f"{marque}.{ext}")
                if ps:
                    dire(f"  >> {marque}.{ext} existe (Shopify, {len(ps)} produits) :")
                    for p in sorted(ps, key=lambda p: p.get("created_at") or "")[:12]:
                        dire(f"       {(p.get('created_at') or '')[:10]} {p.get('title', '')[:70]}")
    dire("Pour noter une boutique d'origine trouvée : scripts/ajouter_piste.py "
         "(--source 'boutique (traces de copie)', --type-date 'création du produit (Shopify)').")
    _ = dossier


if __name__ == "__main__":
    main()
