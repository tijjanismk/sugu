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
4. Sauvegarde et restauration (ticket #17), avec le bucket S3 local du service `s3` :
   ajouter à `.env.repetition` `BACKUP_S3_ENDPOINT_URL=http://s3:9000`,
   `BACKUP_ACCESS_KEY_ID=repetition` et `BACKUP_SECRET_ACCESS_KEY=repetition-secret`, créer le
   bucket (`exec web python -c "import django; django.setup(); from apps.core import backups;
   backups.client().create_bucket(Bucket=backups.bucket())"`), puis avec
   `COMPOSE="docker compose -p sugu-repetition --env-file .env.repetition -f compose.prod.yml -f compose.repetition.yml"` :
   `scripts/backup.sh`, abîmer des données, `scripts/restore.sh quotidien/sugu-<date>.dump`
5. Arrêter : même commande avec `down` (ajouter `-v` pour repartir d'une base vide)

Ce que la répétition du 2026-10-15 a trouvé et corrigé : `collectstatic` lancé avec les
réglages de développement (pas de manifeste : 500 partout en production), la source
Tailwind `input.css` qui faisait échouer `collectstatic`, et la coupure du trafic hors
Cloudflare qui ne s'appliquait pas (ordre des directives Caddy).

Sauvegarde et restauration essayées le 2026-10-15 (ticket #17) : `backup.sh` (88 Ko, copie
locale et bucket), 5 annonces effacées, `restore.sh` depuis le bucket puis depuis la copie
locale : 13 annonces retrouvées, tables au rôle `sugu`, extension `unaccent` et recherche
fonctionnelles, site coupé une vingtaine de secondes. Une sauvegarde abîmée s'arrête à
l'étape 1, site intact (la base `sugu_restauration` vide reste, effacée au prochain essai).

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

### Référencement (Google Search Console)

1. https://search.google.com/search-console → « Ajouter une propriété » → « Préfixe de
   l'URL » `https://sugu.gardientv.tech/`
2. Vérification par « Balise HTML » : copier la valeur `content="…"` dans `/opt/sugu/.env`
   (`GOOGLE_SITE_VERIFICATION=…`), redémarrer `web`, puis « Valider »
3. « Sitemaps » → envoyer `sitemap.xml`
4. Bing Webmaster Tools : « Importer depuis Google Search Console »
5. Au passage à sugu.ml : nouvelle propriété, redirection 301 de l'ancienne adresse
   (Caddy de l'hôte) et « Changement d'adresse » dans la Search Console

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

Ticket #17. `scripts/backup.sh` fait un `pg_dump` (format « custom », en superutilisateur dans
le conteneur `db`), en garde une copie sur le serveur dans `sauvegardes/` (7 jours, lisible par
root seul, jamais dans git ni dans l'image) et l'envoie sur le bucket de sauvegarde par
`manage.py sauvegarde_envoyer`. Sans bucket configuré, seule la copie du serveur existe, et
`check --deploy` le signale (`sugu.W004`).

- Bucket R2 **privé** `sugu-backups`, distinct de celui des photos, avec son propre jeton
  d'API (« Object Read & Write », limité à ce bucket). Variables de `.env` :
  `BACKUP_S3_ENDPOINT_URL` (`https://<id du compte>.r2.cloudflarestorage.com`),
  `BACKUP_ACCESS_KEY_ID`, `BACKUP_SECRET_ACCESS_KEY`, `BACKUP_BUCKET` (`sugu-backups` par défaut)
- Règles de cycle de vie du bucket (Cloudflare, R2, bucket, « Settings », « Object lifecycle
  rules ») : préfixe `quotidien/` supprimé après 30 jours, préfixe `mensuel/` (sauvegarde du
  1er du mois) après 365 jours. Le serveur n'efface jamais rien dans le bucket
- Cron, tous les jours à 3 h (`/etc/cron.d/sugu-sauvegarde`, serveur partagé) :
  ```
  COMPOSE=docker compose -p sugu -f compose.prod.yml -f compose.serveur-partage.yml
  0 3 * * * root /opt/sugu/scripts/backup.sh >> /var/log/sugu-sauvegarde.log 2>&1
  ```
  Sur un serveur dédié, sans la ligne `COMPOSE` (par défaut `compose.prod.yml` seul)
- Lister ce qu'il y a dans le bucket :
  `docker compose -f compose.prod.yml exec web python manage.py sauvegarde_lister`
- Photos sur R2 : activer le versioning du bucket des photos
- Restauration testée : le 2026-10-15 à la répétition générale (bucket S3 local), à refaire
  une fois par trimestre et noter la date ici

## Restauration

```bash
scripts/restore.sh sauvegardes/sugu-2026-10-15-030000.dump   # copie du serveur
scripts/restore.sh quotidien/sugu-2026-10-15.dump            # bucket (sauvegarde_lister)
```

(préfixer de `COMPOSE="docker compose -p sugu -f compose.prod.yml -f compose.serveur-partage.yml"`
sur le serveur partagé). Le script restaure d'abord dans une base à part, site en ligne : une
sauvegarde illisible s'arrête là sans rien toucher. Puis il coupe `web` quelques secondes, met la
base actuelle de côté sous `sugu_avant_<date>`, met la base restaurée à sa place et redémarre
`web`, qui applique les migrations plus récentes que la sauvegarde. Après vérification du site :
`docker compose -f compose.prod.yml exec db dropdb -U postgres sugu_avant_<date>`.

Retour en arrière si la restauration ne convient pas : arrêter `web`, renommer les bases dans
l'autre sens (`ALTER DATABASE … RENAME TO …` dans `psql -U postgres`), redémarrer `web`.

## Supervision

- Disponibilité : UptimeRobot (offre gratuite, compte à créer par l'éditeur). Moniteur
  « Keyword » sur `https://<domaine>/sante/`, mot-clé `ok`, toutes les 5 min, alerte par email.
  `/sante/` interroge aussi la base : une base arrêtée déclenche l'alerte
- Erreurs : Sentry (offre gratuite « Developer », compte à créer par l'éditeur ; choisir la
  région de données **EU** à la création de l'organisation). Projet « Django », puis
  `SENTRY_DSN=…` dans `.env` et redémarrage de `web`. Rien n'est envoyé sans DSN. Aucune
  donnée personnelle ne part (utilisateur, IP, cookies, corps des requêtes, variables locales,
  jetons des liens : `apps/core/sentry.py`). Vérifier l'envoi avec
  `docker compose -f compose.prod.yml exec web python -c "import django, sentry_sdk; django.setup(); sentry_sdk.capture_message('Essai Sugu'); sentry_sdk.flush()"`
- Sauvegardes : `tail /var/log/sugu-sauvegarde.log` ; une ligne « Envoyée : » par jour
- Logs : `docker compose -f compose.prod.yml logs -f web`
- Espace disque : `df -h` ; alerte si > 80 %

## Pages légales

Ticket #17 : « À propos » (`/a-propos/`), mentions légales (`/mentions-legales/`) et politique
de confidentialité (`/confidentialite/`), liées dans le pied de page de toutes les pages de
navigation et depuis l'inscription. Gabarits dans `templates/legal/`.

L'éditeur (particulier ou société, pas encore décidé au 2026-10-15) remplace chaque
« [À COMPLÉTER … » ; tant qu'il en reste, `check --deploy` le signale (`sugu.W003`) :

- `_publisher.html` : identité de l'éditeur (particulier : prénom, nom, adresse ; société :
  raison sociale, forme juridique, capital, siège, RCCM, NIF), directeur de la publication,
  email et téléphone de contact. Repris par les deux pages
- `legal_notice.html` : hébergeur (aujourd'hui Hostinger pour le serveur de test : reprendre
  ses coordonnées dans ses propres mentions légales), récépissé de déclaration à l'APDP
- `privacy.html` : pays des serveurs et autorisation de transfert de l'APDP le cas échéant,
  durée de conservation des annonces retirées et des messages

Déclaration à l'APDP (Autorité de protection des données à caractère personnel, loi
n° 2013-015 du 21 mai 2013) : formalité de l'éditeur avant l'ouverture au public. Faire relire
les trois pages par un juriste au Mali. La politique décrit ce que fait le code : la mettre à
jour à chaque nouvelle donnée collectée ou nouveau prestataire.

## Incidents courants

| Symptôme                   | Cause probable                      | Action                                              |
|----------------------------|-------------------------------------|-----------------------------------------------------|
| 502 Bad Gateway            | conteneur web arrêté                | `docker compose ps`, puis `logs web`                |
| Photos ne s'affichent pas  | clés R2 ou domaine custom           | vérifier `.env`, tester un upload                   |
| Site lent                  | disque plein ou requête sans index  | `df -h`, activer `django-debug-toolbar` en staging  |
| Emails non reçus           | SMTP mal configuré                  | `manage.py sendtestemail`, vérifier `EMAIL_URL` ; sans lui, ni réinitialisation de mot de passe ni email de nouveau message |
