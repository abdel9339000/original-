#!/usr/bin/env python3
"""Compare plusieurs boutiques qui vendent le même produit : qui copie qui ?

Gratuit : lecture des pages publiques seulement (aucune recherche SerpApi).

Usage :
  python3 scripts/comparer_boutiques.py DOSSIER URL1 URL2 URL3 [--candidat URL_SUSPECTE]

  URLn : la page produit de chaque boutique (ou juste le domaine).
  --candidat : une boutique soupçonnée d'être l'originale (répétable).

Pour chaque boutique : nom, pays, thème, date de création du produit, catalogue (les cadeaux
« e-book », « mystery gift »… sont souvent copiés aussi), e-mails, stockage d'images.
Puis ce que les boutiques ont EN COMMUN, deux à deux :
  - les mêmes **avis clients** (prénom + initiale, ex. « Sofia L. », même traduits) ;
  - les mêmes **pourcentages** et **prix** ;
  - les mêmes **noms de fichiers** d'images.
Règle simple : si B reprend des choses propres à A (qu'on ne trouve chez personne d'autre),
et que le produit de A est plus ancien, alors B a copié A.
Écrit le résultat dans DOSSIER/travail/boutiques.json.
"""
import argparse
import html
import itertools
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import dire, masquer  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0"}
PAGES_LEGALES = ["/policies/refund-policy", "/policies/privacy-policy", "/policies/terms-of-service",
                 "/policies/shipping-policy", "/policies/contact-information", "/policies/legal-notice"]
EQUIVALENTS = {  # prénoms traduits d'une langue à l'autre (ex. Sofia = Sophie)
    "sophie": "sofia", "sofía": "sofia", "chiara": "claire", "clara": "claire", "antonio": "antoine",
    "sebastiano": "sebastien", "sébastien": "sebastien", "bastien": "sebastien", "maria": "marie",
    "marta": "marthe", "giulia": "julie", "julia": "julie", "giovanni": "jean", "juan": "jean",
    "john": "jean", "francesca": "francoise", "françoise": "francoise", "luca": "luc", "lucas": "luc",
    "pietro": "pierre", "pedro": "pierre", "peter": "pierre", "carmen": "carmen", "laura": "laure",
    "camilla": "camille", "camila": "camille", "raffaele": "raphael", "raphaël": "raphael",
    "rafael": "raphael", "tommaso": "thomas", "tomás": "thomas", "tomas": "thomas", "marco": "marc",
    "marcos": "marc", "marcus": "marc", "davide": "david", "sara": "sarah", "elena": "helene",
    "hélène": "helene", "nadia": "nadia", "natalia": "natalie", "nathalie": "natalie", "giorgio": "georges",
    "jorge": "georges", "george": "georges", "andrea": "andre", "andrés": "andre", "andré": "andre",
    "amelia": "amelie", "amélie": "amelie", "anaïs": "anais", "carlotta": "charlotte", "carlota": "charlotte",
    "elodia": "elodie", "élodie": "elodie", "fabio": "fabien", "fiorenza": "florence", "florencia": "florence",
    "giulio": "julien", "julio": "julien", "cesare": "cedric", "cédric": "cedric", "emilia": "emilie",
    "émilie": "emilie", "giorgia": "georgia", "matteo": "mathieu", "mateo": "mathieu", "matthew": "mathieu",
    "lorenzo": "laurent", "chiara": "claire",
}


def lire(url, json_ok=False):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            data = r.read().decode("utf-8", "ignore")
        return json.loads(data) if json_ok else data
    except Exception:
        return None


def visible(t):
    t = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", t or "", flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def analyser(url):
    if not url.startswith("http"):
        url = "https://" + url
    p = urllib.parse.urlsplit(url)
    base = f"https://{p.netloc}"
    handle = re.search(r"/products/([^/?#]+)", p.path)
    handle = handle.group(1) if handle else ""
    accueil = lire(base + "/") or ""
    page = lire(url) if handle else ""
    legales = "".join(lire(base + chemin) or "" for chemin in PAGES_LEGALES)
    meta = lire(base + "/meta.json", True) or {}
    produit = (lire(f"{base}/products/{handle}.json", True) or {}).get("product") if handle else None
    catalogue = (lire(base + "/products.json?limit=250", True) or {}).get("products") or []
    tout = accueil + (page or "") + legales
    v_page = visible(page or accueil)
    theme = re.search(r'Shopify\.theme\s*=\s*\{"name":"([^"]*)".*?"schema_name":"?([^",]*)', tout)
    noms_avis = set(re.findall(r"\b([A-ZÀ-Ý][a-zà-ÿ]{2,})\s([A-Z])\.(?=\s|$|[^a-z])", v_page))
    alts = set(re.findall(r'alt="([A-ZÀ-Ý][a-zà-ÿ]{2,}) ([A-Z])\.', page or ""))
    noms_avis |= alts
    images = ([i["src"].split("/")[-1].split("?")[0] for i in (produit or {}).get("images", [])]
              if produit else re.findall(r"/files/([^\"'?\s/]+?\.(?:jpg|jpeg|png|webp))", page or ""))
    return {
        "url": url, "domaine": p.netloc.replace("www.", ""),
        "nom": meta.get("name") or (re.search(r"<title>(.*?)</title>", accueil, re.S) or [None, "?"])[1].strip(),
        "pays": meta.get("country") or "?", "myshopify": meta.get("myshopify_domain") or
        ",".join(set(re.findall(r'Shopify\.shop\s*=\s*"([^"]+)"', tout))),
        "theme": f"{theme.group(1)} ({theme.group(2)})" if theme else "?",
        "produit": (produit or {}).get("title") or "", "cree_le": ((produit or {}).get("created_at") or "")[:10],
        "catalogue": sorted(((x.get("created_at") or "")[:10], x.get("title", "")[:60]) for x in catalogue),
        "emails": sorted(set(e.rstrip(".") for e in re.findall(r"[\w.+-]+@[\w-]+\.[a-z]{2,}(?:\.[a-z]{2,})?",
                                                                html.unescape(tout)))),
        "stockage": sorted(set(re.findall(r"/s/files/1/(\d{3,4}/\d{3,4}/\d{3,4})/", tout))),
        "avis": sorted({f"{n} {i}." for n, i in noms_avis}),
        "pourcentages": sorted(set(re.sub(r"\s", "", x).replace(",", ".")
                                   for x in re.findall(r"\b\d{1,3}(?:[.,]\d)?\s?%", v_page))),
        "prix": sorted(set(re.sub(r"\s", "", x).replace(",", ".")
                           for x in re.findall(r"\d{1,4}[.,]\d{2}\s?(?:€|\$|£)|(?:€|\$|£)\s?\d{1,4}[.,]\d{2}", v_page))),
        "images": images[:30],
    }


def cle_nom(n):
    prenom, ini = n.split(" ")
    return EQUIVALENTS.get(prenom.lower(), prenom.lower()) + " " + ini


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--candidat", action="append", default=[])
    a = ap.parse_args()
    dossier = Path(a.dossier)
    (dossier / "travail").mkdir(parents=True, exist_ok=True)

    res = []
    for u in a.urls + a.candidat:
        r = analyser(u)
        r["candidat"] = u in a.candidat
        res.append(r)
        dire(f"\n== {r['nom']} ({r['domaine']}){' [CANDIDATE]' if r['candidat'] else ''}")
        dire(f"   pays du compte : {r['pays']} | thème : {r['theme']} | Shopify : {r['myshopify'] or '?'}")
        dire(f"   produit : {r['produit'] or '?'} | créé le {r['cree_le'] or '? (catalogue protégé)'}")
        if r["catalogue"]:
            dire("   catalogue : " + " ; ".join(f"{d} {t}" for d, t in r["catalogue"][:12]))
        dire(f"   e-mails : {', '.join(r['emails'][:5]) or '-'} | stockage d'images : {', '.join(r['stockage']) or '-'}")
        dire(f"   avis : {', '.join(r['avis'][:15]) or '-'}")

    dire("\n== Ce que les boutiques ont en commun (deux à deux)")
    for x, y in itertools.combinations(res, 2):
        avis = sorted({cle_nom(n) for n in x["avis"]} & {cle_nom(n) for n in y["avis"]})
        pct = sorted(set(x["pourcentages"]) & set(y["pourcentages"]))
        prix = sorted(set(x["prix"]) & set(y["prix"]))
        img = sorted(set(x["images"]) & set(y["images"]))
        stock = sorted(set(x["stockage"]) & set(y["stockage"]))
        if avis or pct or prix or img or stock:
            dire(f"   {x['nom']} <-> {y['nom']} : avis communs {avis or '-'} ; % {pct or '-'} ; prix {prix or '-'}"
                 + (f" ; mêmes images {img[:5]}" if img else "") + (f" ; MÊME STOCKAGE {stock}" if stock else ""))
    dates = sorted((r["cree_le"], r["nom"]) for r in res if r["cree_le"])
    if dates:
        dire("\n== Dates de création du produit (la plus ancienne d'abord)")
        for d, n in dates:
            dire(f"   {d}  {n}")
    (dossier / "travail" / "boutiques.json").write_text(masquer(json.dumps(res, ensure_ascii=False, indent=1)),
                                                          encoding="utf-8")


if __name__ == "__main__":
    main()
