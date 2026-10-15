#!/usr/bin/env bash
# Restauration d'une sauvegarde (ticket #17, docs/runbook.md « Restauration »).
#   scripts/restore.sh sauvegardes/sugu-2026-10-15-030000.dump    copie du serveur
#   scripts/restore.sh quotidien/sugu-2026-10-15.dump              bucket (sauvegarde_lister)
#
# La sauvegarde est d'abord restaurée dans une base à part, site en ligne : une sauvegarde
# illisible s'arrête là, sans rien toucher. Ensuite seulement, le site est coupé quelques
# secondes, la base actuelle est mise de côté sous sugu_avant_<date> (retour possible) et la
# base restaurée prend sa place. Au redémarrage, `web` applique les migrations plus récentes.
# COMPOSE : comme scripts/backup.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
read -ra COMPOSE <<< "${COMPOSE:-docker compose -f compose.prod.yml}"
SOURCE="${1:?Usage : scripts/restore.sh <fichier .dump ou clé du bucket>}"
STAMP="$(date +%Y%m%d%H%M%S)"
NEW=sugu_restauration
OLD="sugu_avant_$STAMP"

psql() { "${COMPOSE[@]}" exec -T db psql -U postgres -v ON_ERROR_STOP=1 -q "$@"; }

umask 077
if [[ -f "$SOURCE" ]]; then
  DUMP="$SOURCE"
else
  DUMP="$(mktemp)"
  trap 'rm -f "$DUMP"' EXIT
  echo "Téléchargement de $SOURCE"
  "${COMPOSE[@]}" exec -T web python manage.py sauvegarde_telecharger "$SOURCE" > "$DUMP"
fi

echo "1/3 Restauration dans la base $NEW (le site reste en ligne)"
psql -d postgres -c "DROP DATABASE IF EXISTS $NEW" -c "CREATE DATABASE $NEW OWNER sugu"
# Objets créés par le rôle de l'application, comme au premier démarrage (docker/postgres/init).
"${COMPOSE[@]}" exec -T db pg_restore -U postgres --dbname="$NEW" --no-owner --role=sugu \
  --single-transaction --exit-on-error < "$DUMP"
psql -d "$NEW" -c "ALTER SCHEMA public OWNER TO sugu"

echo "2/3 Échange des bases (site coupé quelques secondes)"
"${COMPOSE[@]}" stop web
psql -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'sugu'" \
  -c "ALTER DATABASE sugu RENAME TO $OLD" \
  -c "ALTER DATABASE $NEW RENAME TO sugu"

echo "3/3 Redémarrage du site"
"${COMPOSE[@]}" start web

echo "Restauration terminée. L'ancienne base est gardée sous $OLD : après vérification du site,"
echo "  ${COMPOSE[*]} exec db dropdb -U postgres $OLD"
