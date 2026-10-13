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

## #3 — Modèle utilisateur et authentification

Créer `accounts.User` (email, display_name, phone, city), configurer allauth
(inscription, connexion, déconnexion, mot de passe oublié par email).

Critères d'acceptation :
- Inscription et connexion fonctionnent
- Tests d'intégration sur les trois flux
- `AUTH_USER_MODEL` fixé dès la première migration
- Limitation de débit sur connexion et inscription (voir `docs/security.md`)

## #4 — Base HTML, Tailwind et htmx

`base.html` mobile-first, navigation, messages flash, htmx servi localement,
binaire Tailwind, `input.css`, pages 404 et 500.

Critères d'acceptation :
- Page d'accueil < 50 Ko hors images
- Tailwind compilé sans Node
- `django-htmx` installé et un exemple de partial fonctionnel

## #5 — Catégories, villes et données de démo

Modèles `Category` (deux niveaux) et `City`, admin, commande `seed` avec
~20 catégories et les principales villes.

Critères d'acceptation :
- `manage.py seed` est idempotent
- Les catégories s'affichent sur l'accueil
- Tests unitaires sur le slug et la hiérarchie

## #6 — Modèles Listing et Photo

Modèles, statuts, contraintes, index, trigger PostgreSQL pour `search_vector`,
admin.

Critères d'acceptation :
- Migrations commitées
- Tests des transitions de statut
- `docs/database.md` à jour

## #7 — Dépôt d'annonce avec photos

Formulaire multipart, validation, service de redimensionnement WebP
(1200 px + 400 px), stockage local en dev et R2 en prod via `django-storages`.

Critères d'acceptation :
- Une annonce avec 3 photos est créée en moins de 5 s
- Les originaux ne sont pas conservés ; un fichier qui n'est pas une image est rejeté ; EXIF retiré
- Tests unitaires du service d'images avec une image générée en mémoire

## #8 — Liste, page annonce et pagination

Accueil avec les dernières annonces, page détail, bouton « voir plus » en htmx,
images avec dimensions fixes.

Critères d'acceptation :
- Pagination à 20
- Le partial htmx est renvoyé si `HX-Request`
- Test d'intégration pour les deux cas
- Aucun saut de mise en page au chargement des images

## #9 — Recherche et filtres

Recherche plein texte (`french`), filtres catégorie / ville / prix, formulaire
GET conservant les paramètres.

Critères d'acceptation :
- « velo » trouve « Vélo de course »
- Les filtres se combinent
- L'URL est partageable
- Tests d'intégration sur 5 scénarios

## #10 — Gestion de mes annonces

Page « Mes annonces », modification, marquage vendu, suppression (statut
`removed`).

Critères d'acceptation :
- Un utilisateur ne peut agir que sur ses annonces (test 403)
- Une annonce vendue reste visible avec un bandeau
- Une annonce supprimée disparaît de la recherche

## #11 — Favoris

Bouton cœur en htmx sur la liste et la page annonce, page « Mes favoris ».

Critères d'acceptation :
- Bascule sans rechargement
- Redirection vers la connexion si non connecté
- Contrainte d'unicité testée

## #12 — Messagerie

Conversation par couple (annonce, acheteur), envoi de message, liste des
conversations, polling htmx 10 s, compteur de non-lus.

Critères d'acceptation :
- Un vendeur ne peut pas se contacter lui-même
- Un message est marqué lu à l'ouverture
- Le compteur est juste
- Tests d'intégration complets

## #13 — Profil et contact

Page profil (nom affiché, téléphone, ville), affichage du téléphone sur
l'annonce aux seuls connectés, suppression de compte avec anonymisation.

Critères d'acceptation :
- Téléphone masqué aux visiteurs (test)
- Suppression de compte anonymise annonces et messages sans les détruire

## #14 — PWA

`manifest.json`, icônes, service worker cachant les fichiers statiques et une
page hors-ligne.

Critères d'acceptation :
- Chrome mobile propose « Ajouter à l'écran d'accueil »
- La page hors-ligne s'affiche sans réseau
- Audit Lighthouse PWA sans erreur bloquante

## #15 — Mise en production

`settings/prod.py` durci, Dockerfile, `compose.prod.yml`, Caddyfile,
`runbook.md`, DNS Cloudflare, premier déploiement, bucket R2.

Critères d'acceptation :
- https://sugu.ml répond
- `manage.py check --deploy` sans avertissement
- Admin sur une URL non devinable ; serveur conforme à la section Serveur de `docs/security.md`
- Un dépôt d'annonce avec photo fonctionne en prod
- Tag `v0.1.0`

## #16 — Tests de bout en bout

Les trois parcours Playwright et le job `e2e` dans la CI.

Critères d'acceptation :
- Les trois tests passent localement et sur `main`

## #17 — Exploitation et conformité

Script de sauvegarde + cron, UptimeRobot, Sentry, mentions légales, politique
de confidentialité, page « à propos ».

Critères d'acceptation :
- Une sauvegarde apparaît dans R2
- Une restauration a été testée une fois
- Les pages légales sont liées dans le pied de page

**→ Minimum viable atteint, tag `v1.0.0`.**

---

## Après le minimum viable (V2, à prioriser selon les retours)

- **Réservation d'une annonce** (décision du 2026-10-11) : l'acheteur demande à
  réserver depuis l'annonce, le vendeur accepte ou refuse depuis la conversation ;
  une fois acceptée, l'annonce passe au statut `reserved` avec un badge « Réservée »,
  reste visible, et revient à `published` si le vendeur annule ou après 7 jours.
  Une seule réservation active par annonce. Sans acompte ni paiement. Préparé en V1
  par le statut `reserved` et la table `listings_reservation` (voir `docs/database.md`).
- Modération : signalements, file de modération dans l'admin
- Annonces mises en avant (payantes) — première source de revenus
- Inscription par numéro de téléphone (OTP SMS) — ADR à écrire
- Déploiement sans coupure
- Redimensionnement asynchrone si le dépôt d'annonce devient lent
