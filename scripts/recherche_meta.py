#!/usr/bin/env python3
"""Étape e : cherche dans la bibliothèque publicitaire Meta (Facebook, Instagram…) via SerpApi.

Remplace Trendtrack pour les pubs Meta. Donne pour chaque pub : la page qui la diffuse,
la date de début et de fin (données de Meta), active ou non, le nombre de versions,
le texte de la pub et le lien de la vidéo (pour la comparer ensuite).

Usage :
  python3 scripts/recherche_meta.py DOSSIER --mots "huevo microondas"             # annonce le coût
  python3 scripts/recherche_meta.py DOSSIER --mots "huevo microondas" --ok        # lance
  python3 scripts/recherche_meta.py DOSSIER --page-id 1234567890 --ok             # toutes les pubs d'une page

Options :
  --mots TEXTE        mots à chercher dans le texte des pubs (répétable : une recherche par --mots)
  --phrase-exacte     chercher la phrase exacte (sinon les mots dans n'importe quel ordre)
  --page-id ID        les pubs d'un annonceur (son page_id est donné dans les résultats)
  --pays XX           pays de diffusion (défaut : ALL)
  --langues es,fr     langues des pubs
  --tri recent|impressions   (défaut : impressions, comme la bibliothèque Meta)
  --pages N           pages de 30 pubs par recherche (défaut : 1)
  --chercher-id ID    signale si la pub ID est trouvée (ex. l'identifiant du nom du fichier)

Coût : 1 recherche SerpApi par page (au maximum : nombre de --mots/--page-id × --pages).
Pubs actives ET inactives, vidéos seulement. Liens vidéo valables quelques jours.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (ajouter_ou_fusionner, annoncer_cout, charger_pistes, dire, dossier_recherche,  # noqa: E402
                    erreur, sauver_brut, sauver_pistes, serpapi, serpapi_restant)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--mots", action="append", default=[])
    ap.add_argument("--phrase-exacte", action="store_true")
    ap.add_argument("--page-id", action="append", default=[])
    ap.add_argument("--pays", default="ALL")
    ap.add_argument("--langues", default="")
    ap.add_argument("--tri", choices=["impressions", "recent"], default="impressions")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--chercher-id", default="")
    ap.add_argument("--ok", action="store_true")
    a = ap.parse_args()

    if not a.mots and not a.page_id:
        erreur("donne au moins --mots ou --page-id")
    dossier = dossier_recherche(a.dossier)
    requetes = [("mots", m) for m in a.mots] + [("page", p) for p in a.page_id]
    dire("Recherches prévues : " + " ; ".join(f"{k} « {v} »" for k, v in requetes)
         + f" ; {a.pages} page(s) de 30 pubs max chacune")
    if not annoncer_cout(len(requetes) * a.pages, a.ok):
        return

    pistes = charger_pistes(dossier)
    avant, utilisees, trouvee = len(pistes), 0, None
    for genre, valeur in requetes:
        params = {
            "engine": "meta_ad_library", "country": a.pays, "active_status": "all", "media_type": "video",
            "sort_by": "most_recent" if a.tri == "recent" else "impressions_high_to_low",
        }
        if genre == "mots":
            params["q"] = valeur
            if a.phrase_exacte:
                params["search_type"] = "keyword_exact_phrase"
        else:
            params["page_id"] = valeur
        if a.langues:
            params["content_languages"] = a.langues
        jeton = None
        for n in range(a.pages):
            if jeton:
                params["next_page_token"] = jeton
            data = serpapi(params)
            utilisees += 1
            sauver_brut(dossier, f"meta_{genre}_{valeur}_p{n + 1}", data)
            if data.get("error"):
                dire(f"  {genre} « {valeur} » page {n + 1} : pas de résultat ({data['error']})")
                break
            pubs = data.get("ads") or []
            total = (data.get("search_information") or {}).get("total_results")
            dire(f"  {genre} « {valeur} » page {n + 1} : {len(pubs)} pub(s) (total annoncé : {total})")
            for pub in pubs:
                vid = (pub.get("videos") or [{}])[0] if pub.get("videos") else {}
                for carte in pub.get("cards") or []:  # vidéo parfois dans les cartes
                    vid = vid or {"video_hd": carte.get("video_hd_url") or carte.get("video_hd"),
                                  "video_sd": carte.get("video_sd_url") or carte.get("video_sd"),
                                  "video_preview_image": carte.get("video_preview_image_url")}
                aid = str(pub.get("ad_archive_id") or "")
                fin = pub.get("end_date") or ""
                p = ajouter_ou_fusionner(pistes, {
                    "url": pub.get("details_link") or f"https://www.facebook.com/ads/library/?id={aid}",
                    "sources": ["meta_ad_library"],
                    "compte": pub.get("page_name") or "",
                    "date": pub.get("start_date") or "",
                    "date_type": "début de diffusion (bibliothèque Meta)",
                    "media": vid.get("video_hd") or vid.get("video_sd") or "",
                    "miniature": vid.get("video_preview_image") or "",
                    "titre": (pub.get("body") or pub.get("title") or "")[:120],
                })
                p["plateforme"] = "Pub Meta"
                p.update({"ad_id": aid, "page_id": str(pub.get("page_id") or ""),
                          "collation_id": str(pub.get("collation_id") or ""),
                          "versions": pub.get("collation_count"), "active": pub.get("is_active"),
                          "fin_diffusion": fin, "page_lien": pub.get("page_profile_link") or ""})
                p["note"] = (f"{'active' if pub.get('is_active') else 'inactive'}"
                             f"{' (fin ' + fin + ')' if fin else ''} ; {pub.get('collation_count') or 1} version(s) ; "
                             f"page_id {pub.get('page_id')}")
                marque = ""
                if a.chercher_id and a.chercher_id in (aid, str(pub.get("collation_id") or "")):
                    trouvee, marque = p, "   <== C'EST LA PUB DU FICHIER"
                dire(f"    {p['id']} {pub.get('start_date') or '?':10} {'active  ' if pub.get('is_active') else 'inactive'} "
                     f"x{pub.get('collation_count') or 1:<3} {(pub.get('page_name') or '?')[:28]:28} "
                     f"{(pub.get('body') or '')[:50]!r}{marque}")
            jeton = (data.get("serpapi_pagination") or {}).get("next_page_token")
            if not jeton:
                break

    sauver_pistes(dossier, pistes)
    dire(f"{len(pistes) - avant} nouvelle(s) piste(s). Recherches utilisées : {utilisees}. "
         f"Il reste {serpapi_restant()} recherches SerpApi.")
    if a.chercher_id:
        dire(f"Pub {a.chercher_id} : " + (f"trouvée ({trouvee['id']}, page « {trouvee.get('compte')} », "
                                          f"page_id {trouvee.get('page_id')})" if trouvee else "pas dans ces résultats"))


if __name__ == "__main__":
    main()
