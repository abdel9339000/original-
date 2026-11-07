---
name: chercheur-original
description: Retrouver la version originale d'une vidéo (souvent une pub) et le premier compte qui l'a postée. Images clés avec ffmpeg, recherche d'image inversée (Google Lens et Yandex), bibliothèque publicitaire Meta et vidéos courtes Google, le tout via SerpApi, vérification avec yt-dlp et imagehash, rapport en français poussé dans le dépôt. Utiliser dès que l'utilisateur envoie une vidéo (avec le « + ») ou un lien et demande qui l'a postée en premier, où est l'original, ou d'où vient cette pub.
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
restantes. (Trendtrack n'est pas utilisé : plus de crédit.)
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
  Meta**. Le nombre est l'**identifiant de la pub** : utilise-le avec
  `recherche_meta.py --chercher-id <nombre>` (étape e).
  Lien : `https://www.facebook.com/ads/library/?id=<nombre>`. yt-dlp est bloqué par
  Facebook sur cette page (erreur 403, un contrôle anti-robot) : passe par `recherche_meta.py`.
- `7xxxxxxxxxxxxxxxxxx.mp4` (19 chiffres) : sûrement un identifiant **TikTok**. La date se
  calcule à partir de ce numéro (voir `date_depuis_identifiant` dans `scripts/commun.py`).
- `snaptik_…`, `ssstik_…`, `SnapTik…` : téléchargée depuis TikTok par un site de téléchargement.

**Avant de dépenser quoi que ce soit : réutilise les recherches précédentes** (gratuit).
Si une recherche existe déjà pour le même annonceur ou le même produit (dossiers dans
`recherches/`), compare la nouvelle vidéo à toutes les vidéos déjà téléchargées :
```bash
python3 scripts/reutiliser_recherche.py $D --depuis recherches/<date>/<ancienne-recherche>
python3 scripts/comparer_videos.py $D --ids <la liste affichée>
```
Exemple réel : la 2ᵉ vidéo Vitalba a été remontée jusqu'au réseau US/UK et à Frigora avec
**0 recherche SerpApi**. Les vidéos ne sont gardées que dans `travail/` : si la session a été
recréée, elles ont disparu (il faudra les retélécharger).

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

Tout ce qui suit passe par **SerpApi** (250 recherches gratuites par mois). **Trendtrack
n'est pas utilisé** : il n'a plus de crédit. S'il en a un jour (vérifie avec `check_credits`),
il reste un bonus facultatif (voir tout en bas).

1. Prépare les recherches et calcule leur coût **sans rien lancer** (chaque script sans
   `--ok` affiche le coût et ce qu'il reste) :
   ```bash
   python3 scripts/recherche_inversee.py $D --exact 1                       # d) images
   python3 scripts/recherche_meta.py $D --mots "<produit>" --langues es     # e1) pubs Meta
   python3 scripts/recherche_texte.py $D --phrase "<texte vu à l'écran>"    # e2) vidéos courtes
   ```
   Coûts : 1 recherche par image et par moteur (+1 par image en « correspondances exactes »),
   1 par page de 30 pubs Meta, 1 par phrase.
2. Annonce le total, puis **attends « ok »**, par exemple :
   > Pour chercher l'original, je vais utiliser **SerpApi : 13 recherches** (il t'en reste
   > 238 sur 250 ce mois-ci) :
   > - 11 pour la recherche d'image (Google Lens et Yandex sur 5 images)
   > - 1 dans la bibliothèque des pubs Meta
   > - 1 sur le texte de l'accroche dans les vidéos courtes
   > Je lance ? Réponds « ok ».

   Sois raisonnable : en général **15 recherches au plus** pour une vidéo. S'il faut aller
   plus loin (page suivante, toutes les pubs d'un annonceur…), annonce le supplément et
   redemande « ok ».

## d) Recherche d'image inversée SerpApi : Google Lens et Yandex Images (payant)

```bash
python3 scripts/recherche_inversee.py $D --exact 1 --ok
```

Pour chaque image : Google Lens (résultats « visuels ») et Yandex Images (pages où l'image
apparaît). `--exact 1` ajoute les « correspondances exactes » Lens sur la première image.
Les résultats bruts sont dans `$D/travail/serpapi/` (clé masquée) et chaque lien devient une
piste dans `$D/pistes.json` (avec `nb_images` : sur combien d'images on l'a retrouvé ; plus
c'est haut, plus c'est sûr). Les pistes vues sur plusieurs images sont souvent des **pages de
vente** : elles disent **qui vend le produit**.

## e) Pubs Meta et vidéos courtes, avec SerpApi (payant)

1. **Bibliothèque publicitaire Meta** (Facebook, Instagram, Messenger…), pubs **actives et
   inactives**, vidéos seulement :
   ```bash
   python3 scripts/recherche_meta.py $D --mots "huevo microondas" --langues es --ok
   python3 scripts/recherche_meta.py $D --mots "<marque ou site vu>" --ok
   ```
   Les mots sont cherchés dans le **texte de la pub** (pas dans la vidéo) : essaie le nom du
   produit dans la langue de la pub, la marque, le site. `--phrase-exacte` pour une phrase.
   Le nom **précis** du produit marche le mieux (exemple réel : « escalfador huevos » a
   trouvé la pub du premier coup, « huevo microondas » ramenait surtout des recettes).
   Chaque pub donne : **la page qui la diffuse**, la **date de début** (et de fin) selon Meta,
   active ou non, le **nombre de versions**, et le **lien de la vidéo** (`media`).
   - Si le nom du fichier contenait un identifiant de pub (étape a), ajoute
     `--chercher-id <nombre>` : le script signale la pub si elle est dans les résultats.
   - Quand tu as trouvé l'annonceur, ses autres pubs (pour trouver la version la plus ancienne) :
     `python3 scripts/recherche_meta.py $D --page-id <page_id> --tri recent --ok`
   - La page n'est pas lisible depuis ce serveur, mais le lien `media` se télécharge :
     `comparer_videos.py` s'en sert tout seul. Ces liens expirent après quelques jours.
2. **Vidéos courtes Google** (TikTok, Reels, Shorts, Facebook), sur le **texte vu à l'écran** :
   ```bash
   python3 scripts/recherche_texte.py $D --phrase "quien inventó esto se merece un aumento" --ok
   ```
   Une phrase rare (l'accroche) marche mieux que des mots courants. `--moteur videos` pour
   l'onglet Vidéos de Google.

3. **Fouiller les boutiques des annonceurs** (gratuit), même quand tu crois avoir trouvé :
   la première pub vue n'est pas forcément la boutique d'origine. Les copieurs laissent des
   traces (exemple réel : Vitalba avait une icône « vitalba-favicon-**frigora**-style.png »,
   Fresito une page au titre français dont les images venaient du stockage de Frigora) :
   ```bash
   python3 scripts/fouiller_boutique.py $D --site <domaine> --page "<lien de la pub>" --essayer-marques
   ```
   Il liste les produits et leur date de création, signale les images chargées depuis
   **une autre boutique**, l'outil de clonage, les noms de marque inconnus dans les fichiers,
   et essaie `<marque>.fr/.com/.es/.de/.it`. Remonte la chaîne de copie jusqu'au bout.
   Pense aussi à la **langue d'origine** : une accroche traduite mot à mot (« quien inventó
   esto se merece un aumento » = « whoever invented this deserves a raise ») trahit une
   source en anglais. Cherche alors en anglais, aux États-Unis (US) et au Royaume-Uni (GB).
   Les pubs inactives aux US et au UK apparaissent aussi (constaté), mais il peut en manquer.
   **Même fichier chez plusieurs comptes le même jour** (`comparer_videos.py` le signale :
   « FICHIER IDENTIQUE ») = vidéo **distribuée** (fournisseur, réseau de boutiques). Regarde
   alors la structure de leurs liens (ex. tous en `/funnel/news-…-cp-…`) : c'est souvent un
   même réseau. Les pages protégées par un contrôle anti-robot (Cloudflare) : on n'insiste pas.

Tu peux aussi ajouter une piste à la main (filigrane, lien que je te donne…) :
```bash
python3 scripts/ajouter_piste.py $D --url "<lien>" --source filigrane --compte "<@pseudo>" \
  [--date AAAA-MM-JJ --type-date "publication"] [--media "<lien direct de la vidéo>"] [--note "..."]
```

## f) Lire chaque lien puis vérifier les meilleures pistes (gratuit)

1. **Lire sans télécharger** (date, auteur, durée, qualité) :
   ```bash
   python3 scripts/infos_liens.py $D            # les 25 pistes vidéo les plus prometteuses
   python3 scripts/infos_liens.py $D --ids P04,P09
   ```
   C'est `yt-dlp --dump-json`. Si c'est bloqué (Instagram, Facebook), la date est calculée
   à partir de l'identifiant du post quand c'est possible (TikTok, Instagram, X).
2. **Télécharger seulement les meilleures pistes** (3 à 8 : les plus anciennes, celles vues
   sur plusieurs images, les correspondances exactes, les pubs Meta) et **confirmer
   avec imagehash** :
   ```bash
   python3 scripts/comparer_videos.py $D --ids P03,P07,P12
   ```
   Pour chaque piste : même vidéo **oui / partiel / non**, part de la vidéo retrouvée,
   décalage, durée, qualité, bandes noires. Si la piste dure plus longtemps et contient des
   images en plus, c'est peut-être **la version complète**. Regarde
   `$D/travail/comparaison_PXX.jpg` pour vérifier à l'œil (sous-titres ajoutés, recadrage, miroir).
   Si tu as déjà le fichier : `--ids P05 --fichier chemin/video.mp4`.
3. **Si la pub est un montage** (plusieurs vidéos collées, ou une partie IA plus un vrai
   passage), une source ne contient qu'un morceau. Comparée à la pub entière, elle sera
   jugée « non ». Compare alors **chaque passage** à part :
   ```bash
   python3 scripts/comparer_videos.py $D --ids P03,P07 --passage 25.1-29.5
   ```
   (les changements de plan affichés à l'étape b donnent les bornes). Le résultat est rangé
   à part (`passages` dans `pistes.json`) : il ne remplace pas la comparaison complète.
   Les vidéos déjà téléchargées sont réutilisées (`--retelecharger` pour forcer).
4. Si une piste ne se télécharge pas, regarde au moins sa **miniature** (lien `thumbnail`
   ou `original_image` dans `$D/travail/serpapi/*.json`) et compare-la à l'œil.

## g) Classer les pistes

```bash
python3 scripts/tableau.py $D
```

Le classement : **date la plus ancienne**, puis **version la plus longue**, puis **meilleure
qualité**, puis **sans bandes noires ni recadrage**.
Si plusieurs comptes ont **la même vidéo de base avec d'autres sous-titres**, regarde aussi
qui fait des **variantes à son nom** (nouvelle accroche, carton de fin avec sa marque) :
c'est souvent celui qui a monté la pub. Corrige à la main ce que le script ne
voit pas : **sous-titres ajoutés**, logo d'un revendeur, effet miroir, accéléré.
Le script propose une **confiance** :
- **élevée** : même vidéo confirmée, vraie date de publication, rien de plus ancien en attente ;
- **moyenne** : un doute (date incertaine, piste bloquée, autre version le même jour) ;
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
- SerpApi : <n> recherches (il en reste <x> sur 250 ce mois-ci) : <détail images / pubs Meta / vidéos courtes>

## Limites à garder en tête
- La date de début d'une pub Meta est le **début de diffusion de cette pub** : la vidéo a pu
  être postée avant, ailleurs. (Et si Trendtrack est utilisé : sa date est la **première fois
  que Trendtrack a vu la pub**, pas forcément le jour où elle a été publiée.)
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
- la date de début d'une pub Meta = **début de diffusion de cette pub**, la vidéo a pu exister
  avant ; la date Trendtrack = **première fois vue par Trendtrack**, pas forcément la publication ;
- les **posts supprimés** et **Douyin** restent invisibles.

---

## Variante : trouver la boutique copiée (sans vidéo)

Quand je t'envoie **plusieurs boutiques** qui vendent le même produit et que je te demande
**qui elles ont copié** (exemple réel : Ondellia, Coccoli Milano, Bebysh → K9Clean) :

1. Crée le dossier `recherches/<date>/<nom>/` (avec `travail/`, `images/`, `pistes.json` = `[]`).
2. **Compare les boutiques** (gratuit) :
   ```bash
   python3 scripts/comparer_boutiques.py $D URL1 URL2 URL3
   ```
   Il donne pour chacune : pays, thème, date de création du produit, catalogue (les cadeaux
   « e-book », « mystery gift », « free shipping » sont souvent copiés), e-mails, et surtout ce
   qu'elles ont **en commun** : **avis clients** (même traduits : Sofia L. = Sophie L.),
   pourcentages, prix, images, stockage d'images.
3. **Regarde les images du produit** (outil Read) : les copieurs **traduisent les images** de
   l'original (« Same Great Product, Sweet New Look! » → « Stessa Formula Potente, Nuovo Look
   Raffinato! »). Une étiquette dans une autre langue sur le pot « de nos vidéos » trahit l'original.
4. **Remets en anglais** (ou dans la langue de départ) les phrases et chiffres marquants, et
   cherche-les sur le web avec l'outil **WebSearch** (gratuit pour moi : ce n'est pas SerpApi).
   Cherche aussi dans les **recueils de pages à copier** (« swipe », « listicle », « presell »).
5. Quand tu tiens une candidate, relance l'étape 2 avec `--candidat <sa page produit>`.
   Règle : si B reprend des choses **propres à A** et que le produit de A est **plus ancien**,
   alors B a copié A. Fais un tableau « qui a copié qui ».
6. **Qui d'autre vend ce produit sur Shopify** (gratuit) : teste des adresses probables
   (nom du produit dans plusieurs langues) et lis leurs catalogues :
   ```bash
   python3 scripts/trouver_boutiques_shopify.py $D --mot sushi --noms sushisocks sushisocken sushistrumpor
   ```
   Après une recherche d'image Google Lens (payante), ajoute `--depuis-pistes` pour tester tous
   les sites trouvés. Même stockage d'images, mêmes produits et prix, thème nommé dans la même
   langue = souvent **le même vendeur** avec plusieurs boutiques (exemple réel : Matstrumpor,
   Sushi Sock, Matsokker).
   Pour savoir qui **fait de la pub en ce moment** : `recherche_meta.py --actives`.
7. Cherche aussi le **fabricant** : l'« ancien emballage » montré par la boutique d'origine est
   souvent le produit d'une marque d'usine (Amazon, Chewy, AliExpress…).
8. Rapport avec : la chaîne de copie, les preuves (une image côte à côte des versions traduites
   aide beaucoup), la confiance, ce qui a été consommé et les limites.

---

## Si ça coince

| Problème | Que faire |
|---|---|
| yt-dlp « connexion requise », « bloque ce serveur » ou 403 (Instagram, YouTube, la bibliothèque pub Meta, certains TikTok) | Normal depuis un serveur. Ne cherche pas à contourner ces protections anti-robot. Garde la date calculée à partir de l'identifiant si elle existe, regarde la miniature, cherche la pub avec `recherche_meta.py` (son lien `media` se télécharge) ou demande-moi la vidéo avec le « + ». Les posts Facebook publics passent souvent. |
| Aucun résultat SerpApi | Essaie d'autres images (plan sans texte, produit en gros plan). Annonce le nouveau coût et attends « ok ». |
| Pas de résultat dans la bibliothèque Meta | Les mots sont cherchés dans le texte de la pub, pas dans la vidéo : essaie d'autres mots (nom du produit, autre langue, marque). Annonce le coût et attends « ok ». |
| `comparer_videos.py` dit « non » alors que ça se ressemble | Regarde la planche `comparaison_PXX.jpg`. Effet miroir, gros recadrage ou montage différent : écris « en partie » à la main et explique. |
| Liens raw en erreur 404 | Le dépôt doit être public et la branche poussée. Relance `mettre_en_ligne.sh`. |

---

## Bonus facultatif : Trendtrack (seulement s'il a des crédits)

Trendtrack n'a plus de crédit : **ne l'utilise pas**, sauf si je te dis qu'il en a de nouveau.
Dans ce cas, vérifie avec `check_credits`, annonce le coût, attends « ok », puis :
`search_ads` (`status: "all"`, `media_type: "video"`, `sort_by: "createdAt"`, `order: "asc"`),
`scan_ad` (copies, durée de diffusion), `search_tiktok_library` (`type: "ad"` puis `"organic"`),
`search_products_by_image` (qui vend le produit). Ajoute les pistes avec `ajouter_piste.py`
(`--source trendtrack_…`, `--type-date "première vue Trendtrack"`, `--media "<Media URL>"`).
