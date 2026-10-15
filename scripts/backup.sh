#!/usr/bin/env bash
# Sauvegarde de la base (ticket #17, docs/runbook.md « Sauvegardes ») :
#   1. pg_dump au format « custom » dans le conteneur de la base, en superutilisateur ;
#   2. copie gardée sur le serveur, dans sauvegardes/ (7 jours, lisible par root seul) ;
#   3. envoi sur le bucket de sauvegarde (R2) par l'application : manage.py sauvegarde_envoyer,
#      clés BACKUP_* du .env. Sans elles, seule la copie du serveur existe (check --deploy le dit).
#
# COMPOSE : la commande docker compose du serveur. Par défaut compose.prod.yml seul ; sur le
# serveur partagé : COMPOSE="docker compose -p sugu -f compose.prod.yml -f compose.serveur-partage.yml"
# Tous les jours à 3 h (cron, voir le runbook).
set -euo pipefail
cd "$(dirname "$0")/.."
read -ra COMPOSE <<< "${COMPOSE:-docker compose -f compose.prod.yml}"
DIR="${BACKUP_LOCAL_DIR:-sauvegardes}"
KEEP_DAYS="${BACKUP_LOCAL_DAYS:-7}"

umask 077
mkdir -p "$DIR"
FILE="$DIR/sugu-$(date +%Y-%m-%d-%H%M%S).dump"
PARTIAL="$FILE.partiel"
trap 'rm -f "$PARTIAL"' EXIT

echo "$(date -Is) sauvegarde de la base"
# Fichier partiel d'abord : un pg_dump interrompu ne laisse jamais une sauvegarde d'apparence
# complète (set -e et pipefail arrêtent le script avant le renommage).
"${COMPOSE[@]}" exec -T db pg_dump -U postgres --format=custom sugu > "$PARTIAL"
mv "$PARTIAL" "$FILE"
echo "Copie du serveur : $FILE ($(wc -c < "$FILE") octets)"

"${COMPOSE[@]}" exec -T web python manage.py sauvegarde_envoyer < "$FILE"

find "$DIR" -maxdepth 1 -name 'sugu-*.dump' -mtime "+$KEEP_DAYS" -print -delete
echo "$(date -Is) terminé"
