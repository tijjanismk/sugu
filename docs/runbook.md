# Runbook — exploitation de Sugu

## Environnements

| Environnement | Où                           | Base               | Photos               | Déclenchement                 |
|---------------|------------------------------|--------------------|----------------------|-------------------------------|
| Local         | machine du développeur       | PostgreSQL Docker  | dossier local        | `runserver`                   |
| Test          | GitHub Actions               | PostgreSQL service | dossier temporaire   | chaque push                   |
| Staging       | même VPS, `staging.sugu.ml`  | base séparée       | bucket `sugu-staging` | manuel, depuis `main`        |
| Production    | VPS, `sugu.ml`               | base prod          | bucket `sugu-prod`   | manuel, depuis un tag `vX.Y.Z` |

Le staging est un deuxième `docker compose` sur le même VPS (projet
`sugu-staging`, fichier `.env.staging`). Il coûte 0 € de plus et évite de
tester en production. À mettre en place après le premier déploiement.

## Premier déploiement

1. VPS Hetzner (CX22, Ubuntu LTS la plus récente proposée, 24.04 ou 26.04). Créer un utilisateur `deploy` avec sudo,
   désactiver la connexion root par mot de passe, activer `ufw` (22, 80, 443)
2. Installer Docker : https://docs.docker.com/engine/install/ubuntu/
3. `git clone https://github.com/<toi>/sugu.git && cd sugu`
4. `cp .env.example .env` et renseigner toutes les valeurs
5. DNS Cloudflare : A record `sugu.ml` → IP du VPS, proxy activé (orange) ;
   SSL/TLS en mode « Full (strict) »
6. `docker compose -f compose.prod.yml up -d --build`
7. `docker compose -f compose.prod.yml exec web /opt/venv/bin/python manage.py migrate`
8. `... manage.py createsuperuser` puis `... manage.py seed --categories-only`
9. Vérifier https://sugu.ml, l'admin, et le dépôt d'une annonce avec photo
   (test R2)

## Déploiement d'une nouvelle version

```bash
git fetch --tags && git checkout vX.Y.Z
docker compose -f compose.prod.yml up -d --build web
docker compose -f compose.prod.yml exec web /opt/venv/bin/python manage.py migrate
```

Interruption : quelques secondes pendant le redémarrage du conteneur `web`.
Acceptable à ce stade ; un déploiement sans coupure sera un sujet de V2.

## Retour arrière

```bash
git checkout vX.Y.(Z-1)
docker compose -f compose.prod.yml up -d --build web
```

Si la version incluait une migration non réversible, restaurer la sauvegarde
(voir ci-dessous) avant de redémarrer.

## Mises à jour

- Dependabot ouvre des PR chaque semaine (dépendances Python, actions GitHub,
  images Docker). Fusionner après CI verte ; lire les notes de version pour les
  changements majeurs (Django, PostgreSQL)
- Changement de version majeure de PostgreSQL : sauvegarde, `pg_upgrade` ou
  dump/restore, jamais en changeant juste le tag de l'image
- Mettre à jour `docs/versions.md` à chaque montée de version significative

## Sauvegardes

- `scripts/backup.sh` : `pg_dump` compressé envoyé sur R2 (bucket `sugu-backups`)
- Cron sur le VPS, tous les jours à 03:00 :
  `0 3 * * * /home/deploy/sugu/scripts/backup.sh >> /home/deploy/backup.log 2>&1`
- Conservation : 30 jours (règle de cycle de vie sur le bucket)
- Les photos sont déjà sur R2 : activer le versioning du bucket
- Tester une restauration une fois par trimestre (noter la date ici : —)

## Restauration

```bash
docker compose -f compose.prod.yml stop web
docker compose -f compose.prod.yml exec -T db psql -U sugu -d postgres \
  -c "DROP DATABASE sugu; CREATE DATABASE sugu;"
gunzip -c sugu-AAAA-MM-JJ.sql.gz | docker compose -f compose.prod.yml exec -T db psql -U sugu sugu
docker compose -f compose.prod.yml start web
```

## Supervision

- Disponibilité : UptimeRobot (gratuit), vérification de https://sugu.ml
  toutes les 5 min
- Erreurs : Sentry (offre gratuite), DSN dans `.env`
- Logs : `docker compose -f compose.prod.yml logs -f web`
- Espace disque : `df -h` ; alerte si > 80 %

## Incidents courants

| Symptôme                   | Cause probable                      | Action                                              |
|----------------------------|-------------------------------------|-----------------------------------------------------|
| 502 Bad Gateway            | conteneur web arrêté                | `docker compose ps`, puis `logs web`                |
| Photos ne s'affichent pas  | clés R2 ou domaine custom           | vérifier `.env`, tester un upload                   |
| Site lent                  | disque plein ou requête sans index  | `df -h`, activer `django-debug-toolbar` en staging  |
| Emails non reçus           | SMTP mal configuré                  | `manage.py sendtestemail`, vérifier `EMAIL_URL` ; sans lui, ni réinitialisation de mot de passe ni email de nouveau message |
