# Découpage en tâches — Sugu

Chaque ticket tient en une session de travail (2 à 4 heures). À créer comme
issues GitHub, dans cet ordre. Format : titre, description, critères
d'acceptation.

---

## #1 — Squelette du projet ✅ (fait le 2026-10-11)

Initialiser le dépôt avec Django, `uv`, réglages découpés (base/dev/test/prod),
`compose.yml` pour PostgreSQL, ruff, pre-commit, `.env.example`, README.

Critères d'acceptation :
- `uv run python manage.py runserver` affiche la page par défaut sur PostgreSQL
- `ruff check .` passe
- pre-commit installé et fonctionnel
- README à jour

## #2 — Intégration continue ✅ (fait le 2026-10-13)

Ajouter `ci.yml`, un premier test factice, le modèle de PR, protéger `main`.

Critères d'acceptation :
- La CI passe sur une PR
- Un push direct sur `main` est refusé
- `makemigrations --check` est dans la CI

## #3 — Modèle utilisateur et authentification ✅ (fait le 2026-10-13 ; Google le 2026-10-14 ; email confirmé pour déposer le 2026-10-15)

Créer `accounts.User` (email, display_name, phone, city), configurer allauth
(inscription, connexion, déconnexion, mot de passe oublié par email).

Critères d'acceptation :
- Inscription et connexion fonctionnent
- Tests d'intégration sur les trois flux
- `AUTH_USER_MODEL` fixé dès la première migration
- Limitation de débit sur connexion et inscription (voir `docs/security.md`)

Ajout du 2026-10-14 : **connexion avec Google** dès la V1, bouton « Continuer avec Google » en
tête des pages de connexion et d'inscription. Compte créé d'un clic (nom affiché repris de
Google, adresse vérifiée par Google) ; une adresse déjà inscrite retrouve son compte, sans
doublon ; aucun jeton Google conservé. Bouton masqué tant que les identifiants OAuth ne sont
pas configurés (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). Dépendances : ADR 0002.

Critères ajoutés :
- Inscription et connexion par Google (tests avec la réponse de Google simulée)
- Même adresse email : le compte existant est retrouvé, pas de doublon
- La suppression de compte (#13) délie aussi le compte Google

Ajout du 2026-10-15 : **email confirmé obligatoire pour déposer une annonce et écrire à un
vendeur** (parcourir, chercher et mettre en favori restent ouverts). Sans confirmation : page
« Confirmez votre adresse email », le lien est renvoyé (délai entre deux envois, allauth). Les
comptes Google sont déjà confirmés. Réglage `VERIFIED_EMAIL_REQUIRED` (vrai par défaut).
Suppose des emails réellement livrés (Resend).

Critères ajoutés :
- Sans email confirmé, ni dépôt ni premier message (tests) ; avec, rien ne change

## #4 — Base HTML, Tailwind et htmx ✅ (fait le 2026-10-13)

`base.html` mobile-first, navigation, messages flash, htmx servi localement,
binaire Tailwind, `input.css`, pages 404 et 500.

Critères d'acceptation :
- Page d'accueil < 50 Ko hors images
- Tailwind compilé sans Node
- `django-htmx` installé et un exemple de partial fonctionnel

## #5 — Catégories, villes et données de démo ✅ (fait le 2026-10-13)

Modèles `Category` (deux niveaux) et `City`, admin, commande `seed` avec
~20 catégories et les principales villes.

Critères d'acceptation :
- `manage.py seed` est idempotent
- Les catégories s'affichent sur l'accueil
- Tests unitaires sur le slug et la hiérarchie

## #6 — Modèles Listing et Photo ✅ (fait le 2026-10-14)

Modèles, statuts, contraintes, index, trigger PostgreSQL pour `search_vector`,
admin. Baisse de prix : `previous_price` et `price_dropped_at`, service `update_price`
(ajout du 2026-10-14).

Critères d'acceptation :
- Migrations commitées
- Tests des transitions de statut
- Une baisse de prix sur une annonce publiée mémorise l'ancien prix ; une hausse ou
  « à débattre » l'efface ; contrainte en base : ancien prix > prix actuel (tests)
- `docs/database.md` à jour

## #7 — Dépôt d'annonce avec photos ✅ (fait le 2026-10-14)

Formulaire multipart, validation, service de redimensionnement WebP
(1200 px + 400 px), stockage local en dev et R2 en prod via `django-storages`.

Critères d'acceptation :
- Une annonce avec 3 photos est créée en moins de 5 s
- Les originaux ne sont pas conservés ; un fichier qui n'est pas une image est rejeté ; EXIF retiré
- Tests unitaires du service d'images avec une image générée en mémoire
- Réduction des photos dans le navigateur avant l'envoi (≈ 1 600 px, ajout du 2026-10-14) :
  envoi environ 10 fois plus léger en 3G ; sans JavaScript, l'envoi direct fonctionne toujours
  et le serveur garde toutes ses vérifications

## #8 — Liste, page annonce et pagination ✅ (fait le 2026-10-14 ; photo entière et référencement le 2026-10-15 ; bannières le 2026-10-17)

Accueil avec les dernières annonces, page détail, bouton « voir plus » en htmx,
images avec dimensions fixes.

Critères d'acceptation :
- Pagination à 20
- Le partial htmx est renvoyé si `HX-Request`
- Test d'intégration pour les deux cas
- Aucun saut de mise en page au chargement des images
- Baisse de prix récente (14 jours) : ancien prix barré et badge « Prix en baisse » sur la
  carte et la page annonce ; badge ajouté d'abord dans `design/` (Badge)
- Lieu précis (ajout du 2026-10-14) : champs facultatifs « quartier ou commune » (ex.
  Sabalibougou, Commune V) et « distance de la ville » en km (ex. à 20 km de Bamako),
  saisis au dépôt et affichés « Sabalibougou, Bamako » / « À 15 km de Ségou » sur la carte et
  la page annonce
- Photo entière sur les cartes (retour du 2026-10-15, un logo carré arrivait coupé en haut et
  en bas) : la miniature n'est plus recadrée en 4:3, elle est centrée dans la carte sur le
  fond `surface-sunken` ; les miniatures déjà en ligne sont régénérées
  (`manage.py regenerer_miniatures`)
- Référencement (demande du 2026-10-15, sans publicité) : balises Open Graph sur la page
  annonce (photo, prix, titre : aperçu quand l'annonce est partagée sur WhatsApp ou
  Facebook) et données structurées schema.org `Product` / `Offer` (prix en XOF, disponible
  ou vendue) pour des résultats enrichis ; une seule description par page
- Bannières images en haut de l'accueil (demande du 2026-10-17, avant la V2) : gérées dans
  l'admin (texte alternatif obligatoire, lien facultatif vers une page de Sugu ou une adresse
  https, active, dates de début et de fin, ordre) ; image réencodée en WebP 1200 et 600 px
  sans métadonnées, format 2:1 exigé (refusée plutôt que recadrée) ; entre la recherche et la
  bannière « Installer l'application », qui reste ; défilement au doigt, la suivante dépasse,
  sans JavaScript ni défilement automatique ; seule la première est chargée tout de suite ;
  5 au plus ; rien n'est affiché sans bannière active. Composant `sg-banner` dans `design/`

## #9 — Recherche et filtres ✅ (fait le 2026-10-14 ; pages catégorie et ville le 2026-10-15)

Recherche plein texte (`french`), filtres catégorie / ville / prix, formulaire
GET conservant les paramètres.

Critères d'acceptation :
- « velo » trouve « Vélo de course »
- Les filtres se combinent
- L'URL est partageable
- Tests d'intégration sur 5 scénarios
- Le quartier fait partie de la recherche plein texte (« sabalibougou » trouve l'annonce) ;
  un filtre « dans un rayon de N km » reste possible plus tard grâce à `distance_km`
- Référencement (demande du 2026-10-15) : pages catégorie et ville à adresse lisible
  (`/categorie/telephones/`, `/categorie/telephones/bamako/`, `/ville/bamako/`), titre et
  description propres (« Téléphones à Bamako »), liens entre catégories et villes ; ce sont
  elles que Google indexe, la recherche libre (`/recherche/`) ne l'est pas ; page sans
  annonce non indexée

## #10 — Gestion de mes annonces ✅ (fait le 2026-10-14)

Page « Mes annonces », modification, marquage vendu, suppression (statut
`removed`).

Critères d'acceptation :
- Un utilisateur ne peut agir que sur ses annonces (test 403)
- Une annonce vendue reste visible avec un bandeau
- Une annonce supprimée disparaît de la recherche
- Modifier le prix passe par `update_price` : baisser le prix déclenche la mention de
  baisse, le vendeur voit l'ancien prix dans le formulaire
- Le quartier et la distance de la ville sont modifiables
- Photos modifiables (ajout du 2026-10-14) : retirer une photo, en ajouter jusqu'à 6 (même
  service d'images et même réduction dans le navigateur qu'au #7) ; si la couverture est
  retirée, la photo suivante la remplace ; réordonnancement par glisser-déposer en V2
- Liens vers d'autres sites refusés dans le titre et la description, au dépôt comme à la
  modification (ajout du 2026-10-14 : d'autres sites d'annonces ne doivent pas détourner les
  acheteurs) ; message clair au vendeur

## #11 — Favoris ✅ (fait le 2026-10-14)

Bouton cœur en htmx sur la liste et la page annonce, page « Mes favoris ».
Le bouton envoie l'état voulu (mettre ou retirer), pas « inverser » : un double clic ne
change rien. Sans JavaScript, c'est un formulaire qui revient à la page d'origine. Pas de
cœur sur ses propres annonces. « Mes favoris » garde les annonces vendues (badge) et cache
les annonces retirées.

Critères d'acceptation :
- Bascule sans rechargement
- Redirection vers la connexion si non connecté
- Contrainte d'unicité testée

## #12 — Messagerie ✅ (fait le 2026-10-14, emails de nouveau message compris)

Conversation par couple (annonce, acheteur), envoi de message, liste des
conversations, polling htmx 10 s, compteur de non-lus.
« Écrire au vendeur » collé en bas de la page annonce (à la place de la barre de
navigation) ; la conversation n'est créée qu'au premier message, avec un premier message
proposé (« Bonjour, l'objet est-il toujours disponible ? ») et le rappel de prudence. Pas de
nouvelle conversation sur une annonce vendue ; une conversation commencée continue.
Rafraîchissement suspendu quand l'onglet est en arrière-plan (économie de données).
Ajout du 2026-10-14 : **email de nouveau message**, sinon un vendeur ne sait pas qu'on lui a
écrit tant qu'il n'ouvre pas Sugu. Un seul email par conversation tant que le destinataire ne
l'a pas ouverte (pas un email par message) ; l'email donne l'auteur, l'annonce et le lien vers
la conversation, pas le texte du message (vie privée, et un lien d'arnaque ne part pas depuis
l'adresse de Sugu) ; pas d'email non plus pendant un échange en direct (destinataire qui a
lu un message de la conversation depuis moins de 15 minutes) ; désactivable dans le profil ;
jamais vers un compte supprimé.

Critères d'acceptation :
- Un vendeur ne peut pas se contacter lui-même
- Un message est marqué lu à l'ouverture
- Le compteur est juste
- Tests d'intégration complets
- Email au premier message non lu d'une conversation, pas aux suivants (test)
- Pas d'email si l'avertissement est désactivé dans le profil ou si le compte est supprimé

## #13 — Profil et contact ✅ (fait le 2026-10-14)

Page profil (nom affiché, téléphone, ville), affichage du téléphone sur
l'annonce aux seuls connectés, suppression de compte avec anonymisation.
Ligne vendeur sur l'annonce (avatar, « Membre depuis oct. 2026 · 3 annonces », « Appeler »
ou « Se connecter pour voir le numéro »). Téléphone enregistré en chiffres, affiché par
paires (« +223 76 12 34 56 »). « Déconnecter mes autres appareils » depuis le profil.
Suppression confirmée par le mot de passe ; le correspondant garde la conversation mais ne
peut plus écrire à un compte supprimé.

Critères d'acceptation :
- Téléphone masqué aux visiteurs (test)
- Suppression de compte anonymise annonces et messages sans les détruire

## #14 — PWA ✅ (fait le 2026-10-14, bannière d'installation le 2026-10-15)

`manifest.json`, icônes, service worker cachant les fichiers statiques et une
page hors-ligne.
Manifeste `/manifest.webmanifest` (raccourcis « Déposer une annonce » et « Messages »),
icônes générées par `scripts/make_icons.py`, service worker `/sw.js` : les pages ne sont
jamais mises en cache (données personnelles), seulement la charte et la page hors-ligne.

Critères d'acceptation :
- Chrome mobile propose « Ajouter à l'écran d'accueil » (critères d'installation testés :
  nom, `start_url`, `display: standalone`, icônes PNG 192 et 512 ; à confirmer sur un vrai
  téléphone après la mise en production, #15, car l'installation exige HTTPS)
- La page hors-ligne s'affiche sans réseau (test Playwright `tests/e2e/test_pwa.py`, lancé
  sur `main` ; le navigateur intégré de Claude n'accepte pas les service workers)
- Audit Lighthouse PWA sans erreur bloquante (cette catégorie a disparu de Lighthouse 12 :
  remplacée par les critères d'installation ci-dessus)

Ajout du 2026-10-15 : **bannière « Installer l'application »** sur l'accueil, seulement dans
le navigateur (jamais dans l'application installée). Android et Chrome : bouton « Installer »
qui ouvre la vraie demande d'installation du navigateur, rien si le navigateur ne la propose
pas. iPhone et Safari (pas de bouton possible) : la marche à suivre (Partager, puis « Sur
l'écran d'accueil »). « Plus tard » la masque 30 jours (mémorisé dans le téléphone).

Critères ajoutés :
- La bannière n'apparaît ni dans l'application installée ni si le navigateur ne propose pas
  l'installation (hors iPhone)
- « Plus tard » la masque 30 jours

## #15 — Mise en production

`settings/prod.py` durci, Dockerfile, `compose.prod.yml`, Caddyfile,
`runbook.md`, DNS Cloudflare, premier déploiement, bucket R2.

Critères d'acceptation :
- https://sugu.ml répond
- `manage.py check --deploy` sans avertissement
- Admin sur une URL non devinable ; serveur conforme à la section Serveur de `docs/security.md`
- Un dépôt d'annonce avec photo fonctionne en prod
- Tag `v0.1.0`

Avancement (2026-10-15) : partie locale faite (décision du propriétaire : « local d'abord ») —
image et pile durcies, CSP, admin secrète, `check --deploy` testé, répétition générale de
la pile de production sur le poste (`compose.repetition.yml`) : HTTPS, coupure hors
Cloudflare, rôle PostgreSQL sans privilège, dépôt avec photo et emails vérifiés. Emails par
Brevo. Restent : choix du serveur et du domaine, Cloudflare, R2, Brevo en vrai, premier
déploiement, tag `v0.1.0`.

Ajout du 2026-10-15, référencement (sans publicité) : `robots.txt` (pages privées exclues),
`sitemap.xml` tenu à jour (accueil, catégories, villes, annonces en ligne), adresse
canonique sur chaque page, inscription à Google Search Console (par le propriétaire ;
balise de vérification par `GOOGLE_SITE_VERIFICATION`). Au passage à sugu.ml : redirection
301 de sugu.gardientv.tech pour garder le classement.

Changement du 2026-10-16 : **emails par Resend au lieu de Brevo** (le SMS de vérification du
compte Brevo n'arrivait pas au Mali). Rien ne change dans le code (`EMAIL_URL`) ; domaine
authentifié en région Irlande, clé limitée à l'envoi, page de confidentialité mise à jour.

**Tag `v0.1.0` le 2026-10-17** : dépôt d'annonce avec photo fait en production par le
propriétaire sur le serveur de test (confirmation d'adresse reçue par Resend). Restent pour
clore le ticket : domaine `sugu.ml`, Cloudflare, `check --deploy` sans avertissement (pages
légales, #17), Search Console (en pause jusqu'au passage à `sugu.ml`, décision du 2026-10-17 :
`gardientv.tech` ne sera pas gardé ; l'indexation du serveur de test n'est pas gênante).

## #16 — Tests de bout en bout ✅ (fait le 2026-10-14, sur `main`)

Les trois parcours Playwright et le job `e2e` dans la CI.
Le parcours messagerie vérifie aussi la pastille de non-lus et l'arrivée de la réponse sans
recharger ; le parcours favoris, la bascule sans rechargement. Lancement local à faire une
première fois après `uv run playwright install chromium`.

Critères d'acceptation :
- Les trois tests passent localement et sur `main`

## #17 — Exploitation et conformité

Script de sauvegarde + cron, UptimeRobot, Sentry, mentions légales, politique
de confidentialité, page « à propos ».

Précisions du 2026-10-15 :
- Sauvegarde quotidienne (`scripts/backup.sh`) : `pg_dump` au format custom, copie de 7 jours
  sur le serveur, envoi sur un bucket R2 privé et distinct de celui des photos
  (`manage.py sauvegarde_envoyer`) ; préfixes `quotidien/` (30 jours) et `mensuel/` (un an)
  avec règles de cycle de vie, le serveur n'efface rien dans le bucket. `check --deploy`
  signale un bucket non configuré (`sugu.W004`)
- Restauration (`scripts/restore.sh`) : d'abord dans une base à part, site en ligne, puis
  échange des bases ; l'ancienne est gardée sous `sugu_avant_<date>`
- Sentry côté serveur seulement, sans donnée personnelle (ni utilisateur, ni IP, ni corps des
  requêtes, ni variables locales, jetons des liens effacés) ; région EU
- Pages légales avec des emplacements « à compléter » : l'éditeur (particulier ou société)
  n'est pas encore décidé ; loi malienne n° 2013-015 et APDP ; `check --deploy` les signale
  (`sugu.W003`). Pied de page sur les pages de navigation, lien depuis l'inscription
- Comptes à créer par le propriétaire : Cloudflare R2, Sentry, UptimeRobot

Avancement (2026-10-15, serveur de test) : bucket R2 `sugu-backups` en service, première
sauvegarde envoyée et relue depuis le bucket (identique à la copie du serveur, `sugu.W004`
disparu) ; Sentry branché (région EU), message d'essai envoyé. Restent : moniteur UptimeRobot,
contenu des pages légales (`sugu.W003`), déclaration APDP.

Critères d'acceptation :
- Une sauvegarde apparaît dans R2
- Une restauration a été testée une fois
- Les pages légales sont liées dans le pied de page

**→ Minimum viable atteint, tag `v1.0.0`.**

---

## V2 — indispensable, indépendant du domaine (décision du 2026-10-17)

Règle du propriétaire : la V2 ne garde que ce qui est nécessaire et fonctionne sans `sugu.ml` ;
le reste va en V3. Numéros = issues GitHub (partagés avec les pull requests). Ordre de travail : #49 puis #48.

## #49 — Signalements et modération

Bouton « Signaler cette annonce » sur la page annonce (membre connecté, motif au choix :
arnaque, objet interdit, mauvaise catégorie, déjà vendue ou en double, autre ; précision
facultative), un signalement par membre et par annonce, jamais sur sa propre annonce. File des
signalements dans l'admin, regroupés par annonce ; retrait de l'annonce ou classement sans
suite ; le vendeur est prévenu par email quand son annonce est retirée. Limite d'annonces
déposées par jour et par compte contre le spam. Table `moderation_report` (`docs/database.md`).

Critères d'acceptation :
- Un membre signale une annonce en deux touches ; un second signalement du même membre est refusé
- Le vendeur ne peut pas signaler sa propre annonce ; un visiteur non connecté est invité à se connecter
- L'admin voit les annonces signalées, les plus signalées d'abord, et les traite en une action
- Au-delà de la limite quotidienne, le dépôt est refusé avec un message clair
- Tests « un autre utilisateur essaie » et limite de débit

## #48 — Réservation d'une annonce

Décision du 2026-10-11 : l'acheteur demande à
réserver depuis l'annonce, le vendeur accepte ou refuse depuis la conversation ;
une fois acceptée, l'annonce passe au statut `reserved` avec un badge « Réservée »,
reste visible, et revient à `published` si le vendeur annule ou après 7 jours.
Une seule réservation active par annonce. Sans acompte ni paiement. Préparé en V1
par le statut `reserved` et la table `listings_reservation` (voir `docs/database.md`).
Échéance affichée en texte calculé par le serveur (« Réservée encore 3 j »), pas de compte à
rebours animé (décision du 2026-10-14 : pas d'urgence artificielle, pas de JS permanent).

Critères d'acceptation :
- L'acheteur demande depuis l'annonce, le vendeur accepte ou refuse depuis la conversation
- Badge « Réservée » et échéance en texte ; retour automatique à `published` après 7 jours
- Une seule réservation acceptée par annonce (contrainte en base)
- Tests « un autre utilisateur essaie » sur chaque action

---

## V3 — facultatif, lié au volume d'annonces ou au domaine

- Prix anormaux (idée du 2026-10-14, à faire quand chaque sous-catégorie compte au moins une
  dizaine d'annonces) : prix très bas par rapport à la médiane des annonces similaires →
  signalement à la modération et rappel de prudence renforcé (arnaque) ; prix très élevé →
  simple conseil au vendeur au dépôt (« 5 fois la médiane, vérifiez »), jamais de blocage ni de
  déclassement caché ; tri par prix dans la recherche
- Annonces recopiées par d'autres sites : robots filtrés par Cloudflare (dépend du domaine) ;
  la surveillance des comptes qui déposent en masse est dans le #49
- **Sources de revenus** (liste du 2026-10-14, rien en V1 : le lancement ne vise que le volume
  d'annonces ; on commence quand il y a quelques centaines d'annonces actives), dans l'ordre :
  1. Mise en avant « À la une » pendant 7 jours (en tête de l'accueil et de la recherche, badge),
     payée par mobile money (Orange Money, Moov Money), activée à la main dans l'admin au début ;
     champ `boosted_until` sur l'annonce — première source de revenus
  2. Remontée payante : l'annonce repasse en tête comme si elle venait d'être publiée
  3. Dépôt payant dans quelques catégories à forte valeur (immobilier, véhicules, emploi), le
     reste gratuit ; filtre aussi le spam
  4. Comptes pro / boutiques sur abonnement : plus d'annonces, page boutique, statistiques de
     vues, badge « Pro »
  5. Sponsor local par catégorie (opérateur, banque, concessionnaire) : une image fixe et légère,
     jamais de régie publicitaire (poids de page, traçage)
  6. Badge « Vendeur vérifié » (téléphone vérifié par SMS), payant ou inclus dans le compte pro
  7. Plus tard, avec paiement intégré (ADR obligatoire) : paiement sécurisé avec commission
     (argent bloqué jusqu'à la remise) et livraison par des coursiers partenaires
- Inscription par numéro de téléphone (OTP SMS) — ADR à écrire ; coût par SMS, et les SMS de
  vérification arrivent mal au Mali (constaté avec Brevo le 2026-10-16)
- Déploiement sans coupure
- Redimensionnement asynchrone si le dépôt d'annonce devient lent
