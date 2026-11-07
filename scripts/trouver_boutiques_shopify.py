#!/usr/bin/env python3
"""Trouve les boutiques Shopify qui vendent un produit, en testant des adresses probables.

Gratuit : lecture des catalogues publics Shopify (/meta.json et /products.json).

Usage :
  python3 scripts/trouver_boutiques_shopify.py DOSSIER --mot sushi --mot sock \\
      --noms sushisocks sushisocken sushisokker sushistrumpor chaussettes-sushi \\
      [--domaines matstrumpor.com autre-boutique.fr]

  --mot       mot(s) à trouver dans le titre du produit (tous doivent y être, sans majuscules)
  --noms      noms de boutique à essayer avec plusieurs extensions (.com .de .fr .es .it .nl
              .se .dk .no .fi .pl .at .ch .be .co.uk .shop .store) et préfixes (the, my, get, shop)
  --domaines  domaines précis à tester tels quels
  --depuis-pistes  teste aussi tous les sites des pistes du dossier (après une recherche d'image
              Google Lens : on garde ceux qui sont des boutiques Shopify, avec leurs dates)

Pour chaque boutique Shopify trouvée : nom, pays, devise, et les produits correspondants avec
leur date de création et leur prix. Classement par date : la plus ancienne en premier.
Résultat aussi dans DOSSIER/travail/boutiques_shopify.json.
"""
import argparse
import concurrent.futures
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import dire  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0"}
EXTENSIONS = ["com", "de", "fr", "es", "it", "nl", "se", "dk", "no", "fi", "pl", "at", "ch", "be",
              "co.uk", "shop", "store", "eu", "net", "co"]
PREFIXES = ["", "the", "my", "get", "shop"]


def lire_json(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def tester(domaine, mots):
    meta = lire_json(f"https://{domaine}/meta.json")
    if not meta or "myshopify_domain" not in meta:
        return None
    produits = (lire_json(f"https://{domaine}/products.json?limit=250") or {}).get("products") or []
    trouves = []
    for p in produits:
        titre = (p.get("title") or "") + " " + (p.get("handle") or "")
        if all(m in titre.lower() for m in mots):
            v = (p.get("variants") or [{}])[0]
            trouves.append({"titre": p.get("title"), "cree_le": (p.get("created_at") or "")[:10],
                            "prix": v.get("price"), "lien": f"https://{domaine}/products/{p.get('handle')}"})
    return {"domaine": domaine, "nom": meta.get("name"), "pays": meta.get("country"),
            "devise": meta.get("currency"), "nb_produits": meta.get("published_products_count"),
            "produits": sorted(trouves, key=lambda x: x["cree_le"])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--mot", action="append", default=[])
    ap.add_argument("--noms", nargs="*", default=[])
    ap.add_argument("--domaines", nargs="*", default=[])
    ap.add_argument("--depuis-pistes", action="store_true",
                    help="tester aussi tous les sites des pistes du dossier (ex. après une recherche d'image)")
    a = ap.parse_args()
    mots = [m.lower() for m in a.mot]
    domaines = list(a.domaines)
    if a.depuis_pistes:
        from commun import charger_pistes, hote
        ignores = ("amazon.", "walmart.", "ebay.", "aliexpress.", "temu.", "etsy.", "pinterest.", "facebook.",
                   "instagram.", "tiktok.", "youtube.", "google.", "yandex.", "shein.", "alibaba.")
        for p in charger_pistes(Path(a.dossier)):
            for u in (p.get("url"), p.get("lien_boutique")):  # lien_boutique : site d'une pub Meta
                if u and u.startswith("http") and not any(i in hote(u) for i in ignores):
                    domaines.append(hote(u))
    candidats = list(dict.fromkeys(
        domaines + [f"{pre}{nom}.{ext}" for nom in a.noms for pre in PREFIXES for ext in EXTENSIONS]))
    dire(f"{len(candidats)} adresse(s) à tester…")
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        res = [r for r in ex.map(lambda d: tester(d, mots), candidats) if r]
    avec = [r for r in res if r["produits"]]
    sans = [r for r in res if not r["produits"]]
    lignes = sorted(((p["cree_le"], r, p) for r in avec for p in r["produits"]), key=lambda x: x[0])
    dire(f"\n{len(res)} boutique(s) Shopify trouvée(s), dont {len(avec)} avec le produit :")
    for date, r, p in lignes:
        dire(f"  {date}  {r['nom'][:28]:28} {r['pays'] or '?':3} {r['devise'] or '':4} {p['prix'] or '?':>8}  "
             f"{p['titre'][:50]:50}  {p['lien']}")
    if sans:
        dire("Boutiques Shopify sans ce produit : " + ", ".join(f"{r['domaine']} ({r['nom']})" for r in sans[:15]))
    out = Path(a.dossier) / "travail"
    out.mkdir(parents=True, exist_ok=True)
    (out / "boutiques_shopify.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
