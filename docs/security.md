# Sécurité — Sugu

Règles de sécurité du projet, par couche. Chaque règle dit où elle est mise en
œuvre. Les points marqués « ticket #N » ne sont pas encore codés.

## Le modèle de menace

Par ordre de probabilité pour un site d'annonces :

1. **Escrocs et spammeurs** : faux comptes, fausses annonces, arnaques par messagerie
   (paiement d'avance, faux livreurs). C'est le risque principal.
2. **Vol de compte** : mot de passe deviné ou réutilisé, lien de réinitialisation
   intercepté.
3. **Accès à des données d'un autre utilisateur** : modifier l'annonce d'un autre,
   lire une conversation qui n'est pas la sienne, en changeant un identifiant
   dans l'URL. C'est la faille la plus fréquente dans le code écrit avec l'IA.
4. **Fichiers malveillants** déguisés en photos.
5. **Saturation** (robots, attaques par déni de service).
6. **Faille dans une dépendance** non mise à jour.

## Règles

### Le cadre fait le gros du travail

- Jamais de requête SQL brute (ORM uniquement ; exception justifiée en commentaire).
- Jamais de `|safe` ni de `mark_safe` sur un contenu saisi par un utilisateur.
- Tout formulaire passe par un `Form` Django avec le jeton CSRF ; les vues htmx aussi.
- `manage.py check --deploy` sans avertissement avant chaque mise en production
  (ticket #15).

### Permissions : qui a le droit ?

- Chaque vue qui modifie ou lit une donnée privée vérifie que l'utilisateur
  connecté en est le propriétaire ou le participant : `Listing.user`,
  `Conversation.buyer` / `Conversation.seller`. Pas de vérification = faille.
- Les tests d'intégration couvrent le cas « un autre utilisateur essaie » (réponse
  403 ou 404) pour chaque action de modification. C'est obligatoire dans la PR.
- Les requêtes de lecture filtrent par utilisateur dans l'ORM
  (`Conversation.objects.filter(Q(buyer=user) | Q(seller=user))`), jamais après coup.
- L'admin Django n'est accessible qu'aux comptes `is_staff`, protégé par un mot de
  passe fort, et son URL n'est pas `/admin/` en production (ticket #15).

### Comptes

- Mots de passe hachés en Argon2 (`PASSWORD_HASHERS`), longueur minimale et liste
  des mots de passe courants (`AUTH_PASSWORD_VALIDATORS`).
- Limitation des tentatives : 5 connexions ratées par compte et par IP sur 15 min,
  3 inscriptions par IP par heure (ticket #3, `django-ratelimit` ou équivalent).
- Réinitialisation par email avec lien à durée limitée (allauth, ticket #3).
- La session expire après 30 jours d'inactivité ; déconnexion possible de tous les
  appareils depuis le profil (ticket #13).
- Numéro de téléphone visible uniquement aux utilisateurs connectés (ticket #13) ;
  vérification OTP envisagée en V2.

### Entrées utilisateur

- Validation côté serveur de chaque champ : longueur, format, valeurs permises
  (prix positif, catégorie existante, 6 photos au plus, 8 Mo chacune).
- Les photos sont ouvertes et **réencodées** par Pillow en WebP ; un fichier qui
  n'est pas une image valide est rejeté ; l'original n'est jamais conservé ni servi
  (ticket #7). Les métadonnées EXIF (dont la position GPS) sont retirées.
- Les messages sont du texte brut : liens cliquables, rien d'autre interprété
  (ticket #12).
- Les paramètres de recherche sont validés par un `Form` ; une valeur inattendue
  est ignorée, pas renvoyée telle quelle dans la page.

### Transport et en-têtes

- HTTPS partout : Caddy termine le TLS, Cloudflare en mode « Full (strict) ».
- `prod.py` : `SECURE_SSL_REDIRECT`, cookies `Secure`, HSTS, `nosniff`, politique
  de référent stricte, protection contre l'inclusion dans un cadre.
- Une Content-Security-Policy stricte sera ajoutée une fois le service worker en
  place (ticket #14), car elle interagit avec lui.

### Secrets et configuration

- Aucun secret dans le code ni dans Git : tout vient de l'environnement (`.env`
  ignoré, `.env.example` ne contient que des valeurs d'exemple).
- `SECRET_KEY` de production : 50 caractères aléatoires, générée une fois, jamais
  réutilisée entre staging et production.
- Clés R2 limitées au bucket concerné ; une clé par environnement.

### Débit et robots

- Limitation de débit sur inscription, connexion, dépôt d'annonce, envoi de message
  et signalement (ticket #3, #7, #12).
- Cloudflare devant le site : absorption des attaques par saturation, filtrage des
  robots, cache des fichiers statiques.
- Si le spam d'inscriptions arrive : défi Turnstile (Cloudflare) sur le formulaire
  d'inscription, pas de CAPTCHA à images.

### Dépendances

- Dependabot ouvre une PR par mise à jour chaque semaine ; la CI la valide.
- Une mise à jour de sécurité (Django, Pillow, psycopg) se fusionne le jour même,
  sans attendre le délai de prudence de `docs/versions.md`.
- `uv.lock` fige les versions : la production installe exactement ce qui a été testé.

### Serveur

- Utilisateur `deploy` sans connexion root par mot de passe, clés SSH uniquement,
  `ufw` n'ouvre que 22, 80 et 443, mises à jour de sécurité automatiques.
- L'application tourne en utilisateur non privilégié dans son conteneur (`USER app`
  du Dockerfile) ; la base n'est pas exposée hors du réseau Docker.
- L'utilisateur PostgreSQL de l'application n'est pas superutilisateur.

### Surveillance et reprise

- Sentry pour les erreurs, UptimeRobot pour la disponibilité (ticket #17).
- Sauvegarde quotidienne de la base vers R2, restauration testée une fois par
  trimestre (`docs/runbook.md`).
- Les journaux ne contiennent jamais de mot de passe, de jeton ni de numéro de
  téléphone complet.

### Protection des utilisateurs entre eux

- Rappel de sécurité sur chaque annonce : rencontre dans un lieu public, jamais de
  paiement d'avance sans avoir vu l'objet.
- Bouton « Signaler » sur chaque annonce et chaque conversation ; file de modération
  dans l'admin (V2, mais le modèle `moderation_report` est prévu).
- Suppression de compte : anonymisation plutôt que destruction, pour garder les
  preuves en cas de litige tout en respectant la vie privée (ticket #13).

### Revue

- Chaque PR passe par le prompt de revue de code de `docs/ia-rituels.md`, dont le
  point 2 cherche explicitement les permissions manquantes, les injections et les
  données exposées.
- La liste de contrôle de la PR contient la question « Ai-je vérifié qui a le droit
  de faire cette action ? ».
- Audit externe ou test d'intrusion : à envisager quand le site a des revenus ;
  d'ici là, une relecture par un pair une fois par trimestre.

## En cas d'incident

1. Couper l'accès si nécessaire (mode maintenance Cloudflare).
2. Révoquer les secrets compromis (clé Django, clés R2, mot de passe de la base),
   redéployer.
3. Comprendre l'étendue dans les journaux ; restaurer une sauvegarde si des données
   ont été altérées.
4. Prévenir les utilisateurs concernés, honnêtement et vite.
5. Écrire un post-mortem dans `docs/` : ce qui s'est passé, pourquoi, ce qui change.
