#!/usr/bin/env bash
# Sauvegarde quotidienne de PostgreSQL vers Cloudflare R2.
# Prérequis sur le VPS : aws cli (`apt install awscli`) configuré avec les clés R2.
set -euo pipefail
cd "$(dirname "$0")/.."
DATE=$(date +%F)
FILE="sugu-${DATE}.sql.gz"
BUCKET="${BACKUP_BUCKET:-sugu-backups}"
ENDPOINT="${AWS_S3_ENDPOINT_URL:?AWS_S3_ENDPOINT_URL manquant}"

docker compose -f compose.prod.yml exec -T db pg_dump -U sugu sugu | gzip > "/tmp/${FILE}"
aws s3 cp "/tmp/${FILE}" "s3://${BUCKET}/${FILE}" --endpoint-url "${ENDPOINT}"
rm -f "/tmp/${FILE}"
echo "Sauvegarde ${FILE} envoyée sur ${BUCKET}"
