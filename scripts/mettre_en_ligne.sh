#!/usr/bin/env bash
# Étape c : met 3 à 5 images clés en ligne dans ce dépôt public
# et donne leurs liens raw.githubusercontent.com.
#
# Usage : bash scripts/mettre_en_ligne.sh DOSSIER img_02 img_04 img_07
#
# Copie travail/images/img_XX.jpg vers DOSSIER/images/, fait un commit avec
# seulement ces images, pousse la branche courante, puis attend que chaque lien
# réponde. Les liens utilisent l'identifiant du commit : ils restent valables
# même si la branche change ensuite. Liste écrite dans DOSSIER/images/liens.txt.
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage : bash scripts/mettre_en_ligne.sh DOSSIER img_02 img_04 ..." >&2
  exit 1
fi
DOSSIER="${1%/}"; shift
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
DOSSIER="$(realpath --relative-to=. "$DOSSIER")"
[ -d "$DOSSIER/travail/images" ] || { echo "ERREUR : lance d'abord extraire_images.py" >&2; exit 1; }
if [ $# -gt 5 ]; then echo "ERREUR : 5 images maximum" >&2; exit 1; fi

mkdir -p "$DOSSIER/images"
fichiers=()
for img in "$@"; do
  img="${img%.jpg}"
  src="$DOSSIER/travail/images/$img.jpg"
  [ -f "$src" ] || { echo "ERREUR : $src introuvable" >&2; exit 1; }
  cp "$src" "$DOSSIER/images/$img.jpg"
  fichiers+=("$DOSSIER/images/$img.jpg")
done

git add -- "${fichiers[@]}"
if git diff --cached --quiet -- "${fichiers[@]}"; then
  echo "Images déjà en ligne (aucun changement)."
else
  git commit -q -m "Images clés : $(basename "$DOSSIER")" -- "${fichiers[@]}"
fi

branche="$(git rev-parse --abbrev-ref HEAD)"
essai=0; attente=2
until git push -q -u origin "$branche" 2>/tmp/push_err_$$; do
  essai=$((essai + 1))
  if [ $essai -ge 5 ]; then echo "ERREUR : push impossible : $(tail -1 /tmp/push_err_$$)" >&2; exit 1; fi
  sleep $attente; attente=$((attente * 2))
done
rm -f /tmp/push_err_$$

sha="$(git rev-parse HEAD)"
# owner/repo depuis l'adresse du dépôt (marche aussi derrière un proxy git).
depot="$(git remote get-url origin | sed -E 's#\.git$##; s#^.*[/:]([^/]+/[^/]+)$#\1#')"

: > "$DOSSIER/images/liens.txt"
for f in "${fichiers[@]}"; do
  url="https://raw.githubusercontent.com/$depot/$sha/$f"
  code=000
  for _ in $(seq 1 30); do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || true)"
    [ "$code" = "200" ] && break
    sleep 3
  done
  echo "$url" >> "$DOSSIER/images/liens.txt"
  if [ "$code" = "200" ]; then echo "OK  $url"; else echo "KO (HTTP $code) $url"; fi
done
echo "Liens enregistrés dans $DOSSIER/images/liens.txt"
