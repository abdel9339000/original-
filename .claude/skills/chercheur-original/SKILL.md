---
name: chercheur-original
description: Retrouver la version originale d'une vidéo (souvent une pub) et le premier compte qui l'a postée. Images clés avec ffmpeg, recherche d'image inversée (Google Lens et Yandex via SerpApi), Trendtrack (pubs Meta, scan, bibliothèque TikTok, produit par image), vérification avec yt-dlp et imagehash, rapport en français poussé dans le dépôt. Utiliser dès que l'utilisateur envoie une vidéo (avec le « + ») ou un lien et demande qui l'a postée en premier, où est l'original, ou d'où vient cette pub.
---

# Chercheur d'original : la méthode

Rappel des règles (détail dans `CLAUDE.md`) : tu parles en français, tu tutoies, tu restes
simple. La clé SerpApi n'apparaît jamais. Tu ne publies rien. **Rien de payant sans « ok ».**

Tous les scripts se lancent depuis la racine du dépôt. Ci-dessous, `$D` est le dossier de
la recherche, par exemple `recherches/2026-11-06/ma-video`.

---

## 0. Vérifier l'installation (gratuit)

```bash
python3 scripts/verifier_installation.py
```

Il vérifie la clé (présente ou non, **jamais affichée**), yt-dlp, ffmpeg, imagehash, les sites
(tiktok, instagram, facebook, serpapi, raw.githubusercontent) et les recherches SerpApi
restantes. Vérifie aussi les crédits Trendtrack avec l'outil `check_credits`.
Si quelque chose manque, dis-le simplement et propose la solution.

## a) Récupérer la vidéo (gratuit)

- **Vidéo jointe avec le « + »** : elle est dans `/root/.claude/uploads/<session>/`.
  ```bash
  python3 scripts/recuperer_video.py auto --nom <nom-court>
  ```
  (ou donne le chemin exact à la place de `auto`).
- **Lien** (TikTok, Instagram, Facebook, YouTube…) :
  ```bash
  python3 scripts/recuperer_video.py "<lien>" --nom <nom-court>
  ```
  Le lien envoyé devient la piste **P01**. Si le téléchargement est bloqué (souvent
  Instagram ou Facebook), demande-moi d'envoyer la vidéo avec le « + ».

Le script crée `$D`, copie la vidéo dans `$D/travail/source.*` (jamais poussée) et affiche
la durée et la qualité.

**Regarde le nom du fichier d'origine**, c'est souvent un indice :
- `1234567890123456_video_0.mp4` : vidéo téléchargée depuis la **bibliothèque publicitaire
  Meta**. Le nombre est l'**identifiant de la pub** : donne-le à `scan_ad` (étape e).
  Lien : `https://www.facebook.com/ads/library/?id=<nombre>`. yt-dlp est en général
  bloqué par Facebook (erreur 403, un contrôle anti-robot) : passe par Trendtrack.
- `7xxxxxxxxxxxxxxxxxx.mp4` (19 chiffres) : sûrement un identifiant **TikTok**. La date se
  calcule à partir de ce numéro (voir `date_depuis_identifiant` dans `scripts/commun.py`).
- `snaptik_…`, `ssstik_…`, `SnapTik…` : téléchargée depuis TikTok par un site de téléchargement.

## b) Extraire les images clés et noter les indices (gratuit)

```bash
python3 scripts/extraire_images.py $D --n 8
```

Tu obtiens 6 à 10 images dans `$D/travail/images/` (une par plan, plus la **toute dernière**,
où TikTok met son logo et le @pseudo) et une vue d'ensemble `$D/travail/mosaique.jpg`.

**Regarde la mosaïque, puis chaque image utile en grand** (outil Read), et note :
- **filigrane TikTok** avec un **@pseudo** (il bouge pendant la vidéo, et réapparaît à la fin) ;
- autre filigrane : CapCut, Instagram, Kwai, Likee, logo d'une appli de montage ;
- **logo, nom de marque, site web** (souvent en bas ou à la fin) ;
- **texte à l'écran** (accroche, sous-titres ajoutés, prix, promo) : recopie-le mot pour mot ;
- **langue** (texte et voix si tu l'entends dans le contexte) ;
- **produit** : ce que c'est, sa couleur, sa forme, son emballage ;
- signes de **copie** : bandes noires, image recadrée, sous-titres ajoutés par-dessus,
  vidéo accélérée, effet miroir, qualité dégradée.

Montre-moi ces indices en quelques lignes.

**Raccourci gratuit si tu vois un @pseudo TikTok** : liste les vidéos du compte sans rien
télécharger, puis repère celles qui ont la même durée :
```bash
yt-dlp --flat-playlist --dump-json "https://www.tiktok.com/@<pseudo>" -I 1:300 \
  | python3 -c "import sys,json; [print(d.get('url') or d.get('webpage_url'), d.get('duration')) for d in map(json.loads, sys.stdin)]"
```
Ajoute les bonnes candidates avec `ajouter_piste.py` (source `filigrane`).

## c) Mettre 3 à 5 images en ligne (gratuit)

Choisis **3 à 5 images** nettes et différentes : un plan où le produit se voit bien, un
visage ou une scène marquante, un plan sans texte par-dessus si possible. Évite les écrans
noirs, flous ou couverts de texte.

```bash
bash scripts/mettre_en_ligne.sh $D img_02 img_04 img_06
```

Le script copie les images dans `$D/images/`, les pousse sur la branche, attend que les liens
`raw.githubusercontent.com` répondent et les écrit dans `$D/images/liens.txt`.
Préviens-moi que ces images sont maintenant **publiques**.

## Avant la suite : annoncer le budget et attendre « ok »

1. Calcule le coût SerpApi sans rien lancer :
   ```bash
   python3 scripts/recherche_inversee.py $D --exact 1
   ```
   (1 recherche par image et par moteur, +1 par image en « correspondances exactes » Lens).
2. Vérifie les crédits Trendtrack (`check_credits`) et estime le coût :
   - `search_ads` : environ 1 crédit par pub renvoyée (`limit` 10 à 20) ;
   - `scan_ad` : quelques crédits par scan ;
   - `search_tiktok_library` : **1 crédit par résultat** (`limit` 10, deux fois : pubs et vidéos normales) ;
   - `search_products_by_image` : environ 1 crédit par résultat (`limit` 10).
   Note le solde **avant** et **après** pour donner le vrai coût dans le rapport.
3. Annonce, puis **attends « ok »**, par exemple :
   > Pour chercher l'original, je vais utiliser :
   > - SerpApi : 7 recherches (il t'en reste 250 sur 250 ce mois-ci)
   > - Trendtrack : environ 60 crédits (il t'en reste 4 200)
   > Je lance ? Réponds « ok ».

   Si Trendtrack est à **0 crédit**, dis-le et propose de faire sans (SerpApi seul), ou
   d'attendre le renouvellement.

## d) Recherche d'image inversée SerpApi : Google Lens et Yandex Images (payant)

```bash
python3 scripts/recherche_inversee.py $D --exact 1 --ok
```

Pour chaque image : Google Lens (résultats « visuels ») et Yandex Images (pages où l'image
apparaît). `--exact 1` ajoute les « correspondances exactes » Lens sur la première image.
Les résultats bruts sont dans `$D/travail/serpapi/` (clé masquée) et chaque lien devient une
piste dans `$D/pistes.json` (avec `nb_images` : sur combien d'images on l'a retrouvé ; plus
c'est haut, plus c'est sûr).

## e) Trendtrack (payant)

Utilise les mots trouvés à l'étape b (texte à l'écran, marque, site, produit).

1. **Pubs Meta, de la plus ancienne à la plus récente, actives et inactives** :
   `search_ads` avec `query` = texte ou marque, `status: "all"`, `media_type: "video"`,
   `sort_by: "createdAt"`, `order: "asc"`, `limit: 10` à `20`.
   Si un site est visible : refais avec `search_in: "domain"` (ou `"website"`) et le domaine.
   Garde les pubs qui ressemblent à ta vidéo (miniature, texte, durée).
2. **Scan d'une pub** (copies et durée de diffusion) : `scan_ad` sur la pub la plus ancienne
   (`collation_id` si `search_ads` en donne un, sinon `ad_identifier` = identifiant ou lien
   de la pub). Si le nom du fichier contenait un identifiant Meta (étape a), scanne-le
   directement : `scan_ad` avec `ad_identifier: "<nombre>"`.
   Note : nombre de copies, pages qui la diffusent, première et dernière date vues.
3. **Bibliothèque TikTok, pubs et vidéos normales** : `search_tiktok_library` avec `query`
   (ou `handle` si tu as vu un @pseudo), `type: "ad"` puis `type: "organic"`,
   `sort_by: "newest"`, `order: "asc"` (les plus anciennes d'abord), `limit: 10`.
4. **Qui vend le produit** : `search_products_by_image` avec `image_url` = le lien raw de
   l'image où le produit se voit le mieux, `limit: 10`.

Pour chaque résultat intéressant, ajoute une piste (le « Media URL » sert à télécharger la
vidéo si la page est bloquée) :
```bash
python3 scripts/ajouter_piste.py $D --url "<lien de la pub ou du post>" --source trendtrack_meta \
  --compte "<page ou @pseudo>" --date AAAA-MM-JJ --type-date "première vue Trendtrack" \
  --media "<Media URL>" --duree <secondes> --note "<copies, durée de diffusion…>"
```
Sources possibles : `trendtrack_meta`, `trendtrack_scan`, `trendtrack_tiktok`,
`trendtrack_produit`, `filigrane`. Pour une vidéo TikTok normale avec une vraie date de
publication, mets `--type-date "publication (Trendtrack)"`.

## f) Lire chaque lien puis vérifier les meilleures pistes (gratuit)

1. **Lire sans télécharger** (date, auteur, durée, qualité) :
   ```bash
   python3 scripts/infos_liens.py $D            # les 25 pistes vidéo les plus prometteuses
   python3 scripts/infos_liens.py $D --ids P04,P09
   ```
   C'est `yt-dlp --dump-json`. Si c'est bloqué (Instagram, Facebook), la date est calculée
   à partir de l'identifiant du post quand c'est possible (TikTok, Instagram, X).
2. **Télécharger seulement les meilleures pistes** (3 à 8 : les plus anciennes, celles vues
   sur plusieurs images, les correspondances exactes, les pubs Trendtrack) et **confirmer
   avec imagehash** :
   ```bash
   python3 scripts/comparer_videos.py $D --ids P03,P07,P12
   ```
   Pour chaque piste : même vidéo **oui / partiel / non**, part de la vidéo retrouvée,
   décalage, durée, qualité, bandes noires. Si la piste dure plus longtemps et contient des
   images en plus, c'est peut-être **la version complète**. Regarde
   `$D/travail/comparaison_PXX.jpg` pour vérifier à l'œil (sous-titres ajoutés, recadrage, miroir).
   Si tu as déjà le fichier : `--ids P05 --fichier chemin/video.mp4`.

## g) Classer les pistes

```bash
python3 scripts/tableau.py $D
```

Le classement : **date la plus ancienne**, puis **version la plus longue**, puis **meilleure
qualité**, puis **sans bandes noires ni recadrage**. Corrige à la main ce que le script ne
voit pas : **sous-titres ajoutés**, logo d'un revendeur, effet miroir, accéléré.
Le script propose une **confiance** :
- **élevée** : même vidéo confirmée, vraie date de publication, rien de plus ancien en attente ;
- **moyenne** : un doute (date vue par Trendtrack, piste bloquée, autre version le même jour) ;
- **faible** : rien de confirmé, ou plusieurs doutes.

## h) Rapport en français, enregistré puis poussé

Écris `$D/rapport.md` avec ce plan :

```markdown
# Qui a posté cette vidéo en premier ?

**Vidéo envoyée :** <nom du fichier ou lien> · <durée> s · <qualité>
**Recherche du :** <date>

## En bref
<2 ou 3 phrases : l'original le plus probable, le compte, la date, la confiance.>

## Ce que j'ai vu dans la vidéo
- <filigrane, @pseudo, logo, site, texte à l'écran, langue, produit, signes de copie>

## Images utilisées pour la recherche
![img_02](images/img_02.jpg) ![img_04](images/img_04.jpg) …

## Pistes trouvées
<tableau de scripts/tableau.py : plateforme, compte, date, lien, même vidéo, qualité, durée>

## L'original le plus probable
<compte, plateforme, date, lien ; pourquoi (date, durée, qualité, pas de sous-titres
ajoutés) ; niveau de confiance et ce qui pourrait le faire changer>

## Ce que la recherche a consommé
- SerpApi : <n> recherches (il en reste <x> sur 250 ce mois-ci)
- Trendtrack : <n> crédits (il en reste <x>)

## Limites à garder en tête
- La date Trendtrack est la **première fois que Trendtrack a vu la pub**, pas forcément
  le jour où elle a été publiée.
- Les **posts supprimés** et **Douyin** (le TikTok chinois, souvent la vraie source des
  vidéos de produits) restent invisibles pour cette recherche.
- Instagram et Facebook bloquent souvent la lecture automatique : certaines dates manquent.
- « Même vidéo » vient d'une comparaison d'images automatique (imagehash).
```

Puis pousse (seulement ces fichiers, jamais `travail/`) :
```bash
git add $D/rapport.md $D/pistes.json $D/images/
git commit -m "Rapport : <nom>"
git push -u origin "$(git rev-parse --abbrev-ref HEAD)"
```

Dans le chat, donne-moi **le résumé** : l'original le plus probable (compte, date, lien), la
confiance, le tableau en court, ce qui a été consommé, et le lien vers le rapport sur GitHub.

## i) Toujours rappeler les limites

Même si je ne demande rien, termine en rappelant :
- la date Trendtrack = **première fois vue par Trendtrack**, pas forcément la publication ;
- les **posts supprimés** et **Douyin** restent invisibles.

---

## Si ça coince

| Problème | Que faire |
|---|---|
| yt-dlp « connexion requise » / 403 sur Instagram ou Facebook | Normal depuis un serveur. Garde la date calculée à partir de l'identifiant si elle existe, sinon passe par Trendtrack (Media URL) ou demande-moi la vidéo avec le « + ». |
| Aucun résultat SerpApi | Essaie d'autres images (plan sans texte, produit en gros plan). Annonce le nouveau coût et attends « ok ». |
| Trendtrack à 0 crédit | Dis-le, fais sans, et note-le dans les limites du rapport. |
| `comparer_videos.py` dit « non » alors que ça se ressemble | Regarde la planche `comparaison_PXX.jpg`. Effet miroir, gros recadrage ou montage différent : écris « en partie » à la main et explique. |
| Liens raw en erreur 404 | Le dépôt doit être public et la branche poussée. Relance `mettre_en_ligne.sh`. |
