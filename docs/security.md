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
- Annonces (ticket #10) : les vues de gestion passent par `_own_listing` (404 si l'annonce
  est supprimée ou n'existe pas, 403 si elle est à un autre) et les services revérifient le
  propriétaire (`services.check_owner`). Les actions définitives (vendre, supprimer) passent
  par une page de confirmation puis un POST ; un GET ne modifie jamais rien. Une contre-épreuve
  (vérification retirée → les 5 tests « autre utilisateur » échouent) a été faite.
- Favoris (ticket #11) : un favori ne se lit et ne s'écrit que pour `request.user` (pas
  d'identifiant d'utilisateur dans l'URL), en POST avec jeton CSRF. L'adresse de retour
  (`next`, ou l'en-tête `HX-Current-URL` en htmx) est validée par
  `url_has_allowed_host_and_scheme` : une adresse d'un autre site est ignorée, pas de
  redirection ouverte. Contre-épreuves faites (contrôle de connexion ou d'adresse retiré → les
  tests échouent).
- Les requêtes de lecture filtrent par utilisateur dans l'ORM
  (`Conversation.objects.filter(Q(buyer=user) | Q(seller=user))`), jamais après coup.
- L'admin Django n'est accessible qu'aux comptes `is_staff`, protégé par un mot de
  passe fort, et son URL n'est pas `/admin/` en production (ticket #15).

### Comptes

- Mots de passe hachés en Argon2 (`PASSWORD_HASHERS`), longueur minimale et liste
  des mots de passe courants (`AUTH_PASSWORD_VALIDATORS`).
- Limitation des tentatives : 5 connexions ratées par compte et par IP sur 15 min,
  3 inscriptions par IP par heure. Mis en œuvre par la limitation intégrée d'allauth
  (`ACCOUNT_RATE_LIMITS`), compteurs dans le cache en base (`django_cache`). En production,
  l'IP du visiteur est lue dans `CF-Connecting-IP` (`ALLAUTH_TRUSTED_CLIENT_IP_HEADER`) :
  cet en-tête n'est fiable que si le serveur refuse le trafic web qui ne vient pas de
  Cloudflare (ticket #15). Point à surveiller : les opérateurs mobiles partagent souvent une
  même IP entre de nombreux abonnés ; relever la limite par IP si des inscriptions
  légitimes sont bloquées.
- Réinitialisation par email avec lien valable une heure (`PASSWORD_RESET_TIMEOUT`), sans
  révéler si l'adresse a un compte.
- Vérification de l'email « optionnelle » (l'email de confirmation part, le compte sert
  tout de suite) ; à passer en « obligatoire » si les faux comptes arrivent.
- Déconnexion uniquement par POST : un lien piégé ne déconnecte pas.
- La session expire après 30 jours d'inactivité ; « Déconnecter mes autres appareils »
  depuis le profil (ticket #13) : `User.session_version` entre dans le hachage de session
  (`_get_session_auth_hash`), l'augmenter invalide toutes les sessions sans changer le mot
  de passe ; la session courante est gardée (`update_session_auth_hash`). Tant qu'il vaut
  0, le hachage est celui de Django : la mise en production ne déconnecte personne.
- Numéro de téléphone visible uniquement aux utilisateurs connectés (ticket #13) : absent
  du HTML pour un visiteur, sous aucune forme (testé, contre-épreuve faite) ; vérification
  OTP envisagée en V2.

### Entrées utilisateur

- Validation côté serveur de chaque champ : longueur, format, valeurs permises
  (prix positif, catégorie existante, 6 photos au plus, 8 Mo chacune).
- Liens vers d'autres sites, adresses web et emails refusés dans le titre, le quartier et la
  description d'une annonce (`forms.LINK_PATTERN`, dépôt et modification) : d'autres sites
  d'annonces ne détournent pas les acheteurs ; le contact passe par Sugu.
- Les photos sont ouvertes et **réencodées** par Pillow en WebP (`apps/listings/images.py`) :
  seuls JPEG, PNG et WebP valides sont acceptés, un fichier tronqué ou déguisé est rejeté,
  une image de plus de 40 Mpx est refusée avant décodage (bombe de décompression),
  l'original n'est jamais écrit ni servi. L'orientation EXIF est appliquée puis toutes les
  métadonnées (dont la position GPS) disparaissent au réencodage. La réduction faite dans le
  navigateur avant l'envoi (`photo-picker.js`) n'est qu'un confort : le serveur revérifie tout.
- Email de nouveau message (ticket #12) : l'auteur, l'annonce et le lien, jamais le texte
  du message (vie privée ; un lien d'arnaque ne part pas depuis l'adresse de Sugu). Nom
  ramené sur une ligne dans le sujet (pas d'en-tête injecté). Un email par conversation tant
  qu'elle n'est pas ouverte, rien pendant un échange en direct, désactivable au profil ;
  une panne d'envoi est journalisée sans l'adresse et n'empêche pas le message.
- Les messages sont du texte brut : liens cliquables (`urlize`, `rel="nofollow"`), rien
  d'autre interprété ; le HTML saisi est échappé (testé). 1 000 caractères au plus.
- Messagerie (ticket #12) : une conversation n'est lue, écrite ou rafraîchie que par ses deux
  participants (`services.get_conversation` filtre dans la requête ; un tiers reçoit 404,
  testé, contre-épreuve faite) ; `send_message` revérifie l'auteur. Un vendeur ne peut pas
  s'écrire (403, et contrainte CHECK en base).
- Les paramètres de recherche sont validés par un `Form` (`SearchForm.valid_filters`) ; une
  valeur inattendue est ignorée, pas renvoyée telle quelle dans la page : les liens (chips,
  « Voir plus ») sont reconstruits à partir des seuls filtres valides. Les mots-clés ne
  gardent que lettres et chiffres avant d'atteindre PostgreSQL (`tsquery` brute construite
  par `services.search_query`), ce qui neutralise la syntaxe `& | ! :`.

### Transport et en-têtes

- HTTPS partout : Caddy termine le TLS, Cloudflare en mode « Full (strict) ».
- `prod.py` : `SECURE_SSL_REDIRECT`, cookies `Secure`, HSTS, `nosniff`, politique
  de référent stricte, protection contre l'inclusion dans un cadre.
- Une Content-Security-Policy stricte reste à ajouter (ticket #15 ; Django 6 l'intègre) :
  le service worker est en place (ticket #14). Déjà prêt : aucun `hx-on` ni filtre htmx
  (`static/js/conversation.js`) ; restent le script de thème en ligne de `base.html` et de
  la page hors-ligne (nonce ou empreinte) et la balise `<style>` d'indicateurs de htmx.
- Service worker (ticket #14) : il ne met jamais une page en cache (messages, téléphone,
  jeton CSRF) ; seuls la charte publique et la page hors-ligne, identique pour tous et sans
  cookie, sont précachés. Servi à la racine, `Cache-Control: no-cache`.

### Secrets et configuration

- Aucun secret dans le code ni dans Git : tout vient de l'environnement (`.env`
  ignoré, `.env.example` ne contient que des valeurs d'exemple).
- `SECRET_KEY` de production : 50 caractères aléatoires, générée une fois, jamais
  réutilisée entre staging et production.
- Clés R2 limitées au bucket concerné ; une clé par environnement.

### Débit et robots

- Limitation de débit sur inscription, connexion, dépôt d'annonce, envoi de message
  et signalement (inscription et connexion : ticket #3 ; dépôt d'annonce : 5 par heure et
  20 par jour par utilisateur, ticket #7, via `apps/core/ratelimit.py` ; messagerie,
  ticket #12 : 10 nouvelles conversations par heure et 30 par jour, 60 messages par heure et
  300 par jour).
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
  preuves en cas de litige tout en respectant la vie privée (ticket #13). Confirmée par le
  mot de passe (5 essais par heure). Annonces retirées, messages gardés et signés
  « Compte supprimé », email, nom, téléphone et ville effacés, favoris et adresses email
  supprimés, compte désactivé et sessions invalidées ; plus personne ne peut lui écrire.
  Les photos des annonces retirées restent sur le disque (noms non devinables) ; leur
  effacement après un délai est à décider avec les mentions légales (ticket #17).

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
