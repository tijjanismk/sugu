#!/bin/sh
# Premier démarrage de la base (ticket #15, docs/security.md) : l'application se connecte avec
# un rôle « sugu » qui n'est pas superutilisateur, propriétaire de sa base. Le superutilisateur
# « postgres » ne sert qu'à l'administration. Ne tourne qu'une fois, sur un volume vide.
set -e
psql -v ON_ERROR_STOP=1 -v app_password="$APP_DB_PASSWORD" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
CREATE ROLE sugu LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
ALTER DATABASE sugu OWNER TO sugu;
ALTER SCHEMA public OWNER TO sugu;
EOSQL
