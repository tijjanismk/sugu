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

## Répétition générale en local

La vraie pile de production (image, Caddy, PostgreSQL sans superutilisateur) sur le poste,
sans Cloudflare, R2 ni Brevo (ticket #15). À refaire avant chaque changement du
`Dockerfile`, de `compose.prod.yml` ou du `Caddyfile`.

1. Créer `.env.repetition` (ignoré par git) avec des valeurs aléatoires : `ENV_FILE`,
   `DJANGO_SETTINGS_MODULE=config.settings.prod`, `SECRET_KEY`, `ALLOWED_HOSTS=localhost`,
   `ADMIN_URL`, `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `DATABASE_URL` (rôle `sugu`) et
   `EMAIL_URL=smtp://mailpit:1025`
2. Lancer :
   ```bash
   docker compose -p sugu-repetition --env-file .env.repetition -f compose.prod.yml -f compose.repetition.yml up -d --build
   ```
3. Vérifier : https://localhost:8443 (certificat local de Caddy), `check --deploy` dans le
   conteneur `web`, `seed --categories-only`, un dépôt d'annonce avec photo, les emails
   dans Mailpit (http://localhost:8025)
4. Arrêter : même commande avec `down` (ajouter `-v` pour repartir d'une base vide)

Ce que la répétition du 2026-10-15 a trouvé et corrigé : `collectstatic` lancé avec les
réglages de développement (pas de manifeste : 500 partout en production), la source
Tailwind `input.css` qui faisait échouer `collectstatic`, et la coupure du trafic hors
Cloudflare qui ne s'appliquait pas (ordre des directives Caddy).

## Premier déploiement

1. VPS Hetzner (CX22, Ubuntu LTS la plus récente proposée, 24.04 ou 26.04). Créer un utilisateur `deploy` avec sudo,
   désactiver la connexion root par mot de passe, activer `ufw` (22, 80, 443)
2. Installer Docker : https://docs.docker.com/engine/install/ubuntu/
3. `git clone https://github.com/<toi>/sugu.git && cd sugu`
4. `cp .env.example .env` et renseigner toutes les valeurs (`ADMIN_URL` aléatoire,
   mots de passe de la base aléatoires)
5. DNS Cloudflare : A record `sugu.ml` → IP du VPS, proxy activé (orange) ;
   SSL/TLS en mode « Full (strict) ». Le serveur refuse tout ce qui ne passe pas par
   Cloudflare (`Caddyfile`) : sans le proxy orange, le site ne répond pas. Plages IP de
   Cloudflare dans `compose.prod.yml` (`EDGE_RANGES`), à comparer de temps en temps avec
   https://www.cloudflare.com/ips/
6. R2 : bucket `sugu-prod`, jeton d'API limité à ce bucket, domaine public
   `photos.sugu.ml` ; renseigner les variables `AWS_*` de `.env`
7. Brevo : compte, domaine `sugu.ml` authentifié (enregistrements DKIM et SPF ajoutés chez
   Cloudflare), clé SMTP ; `EMAIL_URL` dans `.env`
8. `docker compose -f compose.prod.yml up -d --build` (les migrations passent au démarrage
   du conteneur `web`)
9. `docker compose -f compose.prod.yml exec web python manage.py createsuperuser` puis
   `... seed --categories-only`, et `... check --deploy`
10. Vérifier https://sugu.ml, l'admin à son adresse secrète, un dépôt d'annonce avec photo
    (photo servie par `photos.sugu.ml`) et un email de mot de passe oublié
11. Connexion avec Google (ADR 0002), facultative : dans la console Google Cloud, créer un
    identifiant OAuth « Application Web », adresse de retour autorisée
    `https://sugu.ml/comptes/google/login/callback/` (et
    `http://localhost:8000/comptes/google/login/callback/` pour le développement), écran de
    consentement publié ; puis `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` dans `.env`. Sans
    ces deux variables, le bouton « Continuer avec Google » n'apparaît pas.

## Serveur partagé (KVM 2 Hostinger, avec GardienTV)

Mise en ligne de test décidée le 2026-10-15 : Sugu sur le VPS qui héberge déjà GardienTV,
à l'adresse `https://sugu.gardientv.tech`, en attendant son propre serveur et `sugu.ml`.

- Le Caddy de l'hôte (systemd, `/etc/caddy/Caddyfile`) tient 80/443 et le HTTPS pour tous les
  sites ; Sugu tourne dans `/opt/sugu` (projet Docker `sugu`) et son Caddy n'écoute que sur
  `127.0.0.1:8081` (`compose.serveur-partage.yml`). GardienTV n'est pas touché.
- Pas de Cloudflare : le Caddy de l'hôte écrase `CF-Connecting-IP` avec l'IP du visiteur, que
  Django utilise pour les limites de débit. Photos sur le disque du serveur (volume `media`).
- Emails capturés par Mailpit, pas livrés : `ssh -L 8025:127.0.0.1:8025 root@45.9.188.18`
  puis http://localhost:8025. Brevo plus tard : changer `EMAIL_URL` dans `/opt/sugu/.env`.
- DNS : enregistrement A `sugu` → `45.9.188.18` dans la zone de gardientv.tech.

Bloc ajouté au Caddyfile de l'hôte (sauvegarde du fichier, `caddy validate`, puis
`systemctl reload caddy`) :

```
sugu.gardientv.tech {
	reverse_proxy 127.0.0.1:8081 {
		header_up CF-Connecting-IP {remote_host}
	}
}
```

Commandes (dans `/opt/sugu`) :

```bash
git pull
docker compose -p sugu -f compose.prod.yml -f compose.serveur-partage.yml up -d --build
docker compose -p sugu -f compose.prod.yml -f compose.serveur-partage.yml exec web python manage.py createsuperuser
```

L'adresse de l'admin est dans `/opt/sugu/.env` (`ADMIN_URL`).

## Déploiement d'une nouvelle version

```bash
git fetch --tags && git checkout vX.Y.Z
docker compose -f compose.prod.yml up -d --build web
```

Les migrations passent au démarrage du conteneur `web`.

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
