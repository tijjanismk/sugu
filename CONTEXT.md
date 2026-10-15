# CONTEXT.md — à fournir à l'IA au début de chaque session

## Le projet en trois lignes

Sugu est un site de petites annonces généraliste entre particuliers (type
Leboncoin) pour l'Afrique de l'Ouest francophone. Priorités : légèreté sur
connexion lente, usage mobile, maintenabilité par un développeur seul.

## Stack (ne pas remettre en cause sans ADR)

- Python 3.14, Django 6.1, pages HTML rendues côté serveur (partials de template natifs de Django 6 pour htmx)
- htmx 2 pour l'interactivité (pas de framework JS, pas de React/Vue)
- Tailwind CSS 4 via binaire standalone (pas de Node dans le projet, configuration dans `static/css/input.css`)
- PostgreSQL 18, recherche plein texte native (pas d'Elasticsearch)
- Photos : Cloudflare R2 via django-storages, redimensionnées avec Pillow
- Authentification : django-allauth (email + mot de passe)
- Tests : pytest-django, factory-boy, Playwright
- Qualité : ruff (lint + format), pre-commit, Dependabot pour les mises à jour
- Versions figées dans `uv.lock` ; versions de référence dans `docs/versions.md`
- Déploiement : Docker, Caddy 2.11, VPS Hetzner, Cloudflare devant
- Pas de Celery, pas de Redis, pas de Go en V1 (voir ADR 0001)
- Emails : réglage `MAILERS` de Django 6.1 (console en dev, locmem en test, SMTP depuis `EMAIL_URL` en prod)

## Interface

- La charte graphique est dans `design/README.md` ; les tokens dans `design/tokens.json`
  (`design/tokens.css` généré) ; les composants dans `design/components/` (classes `sg-…`).
- Deux thèmes, clair et sombre, via `data-theme` ; aucune couleur en dur dans les gabarits.
- Règles clés : prix en `indigo` lu en premier ; `sun` réservé à « Déposer une annonce » ;
  44 px minimum pour tout élément tactile ; pas d'ombre sur les cartes ; Lucide en SVG inliné, pas d'émoji.
- Pour toute tâche d'interface, fournir `design/README.md` en plus de ce fichier.

## Organisation du code

- `config/` : réglages Django découpés base / dev / test / prod
- `apps/<domaine>/` : core, accounts, listings, messaging, favorites
- La logique métier va dans `services.py`, pas dans les vues ni les modèles
- Les vues htmx renvoient des partials dans `templates/<app>/partials/`
- Pas de requête SQL brute sauf justification en commentaire

## Conventions

- Français pour la documentation, les commits, les commentaires et l'interface
- Anglais pour le code (noms de variables, fonctions, modèles, URL names)
- Commits : Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`)
- Une branche par tâche, une pull request par branche, même en solo
- Chaque fonctionnalité arrive avec ses tests ; une PR sans test est incomplète
- Longueur de ligne 100, formatage ruff, imports triés par ruff
- Jamais de secret dans le code : tout passe par les variables d'environnement
- Les migrations Django sont commitées et jamais modifiées après merge
- Sécurité : règles dans `docs/security.md` ; toute vue qui modifie ou lit une donnée privée
  vérifie le propriétaire et a un test « un autre utilisateur essaie »

## Décisions clés (résumé des ADR)

- 0001 : Django + htmx, un seul langage ; Go réservé à un futur service isolé
- Le paiement n'est pas intégré ; le modèle `Listing` a un champ
  `payment_methods` pour le préparer
- Inscription par email ; l'inscription par numéro de téléphone (OTP SMS) est
  un candidat ADR futur
- Réservation d'annonce (l'acheteur demande, le vendeur accepte) : décidée pour la V2 ;
  en V1 on prévoit seulement le statut `reserved`, rien d'autre

## Ce que l'IA doit faire dans une session

1. Lire ce fichier, puis `docs/design.md` si la tâche touche à l'architecture
2. Proposer un plan court avant d'écrire du code
3. Écrire le code ET les tests
4. Signaler toute décision qui mériterait un ADR
5. Ne pas ajouter de dépendance sans la justifier

## État d'avancement

<!-- Mettre à jour à la fin de chaque session -->
- Dernière tâche terminée : #14 PWA (`apps/core/pwa.py` : manifeste, `/sw.js` à la racine
  qui ne met jamais une page en cache, page `/hors-ligne/` identique pour tous, icônes par
  `scripts/make_icons.py` ; test hors-ligne dans `tests/e2e/test_pwa.py`)
- Aussi fait : #16 Tests de bout en bout (trois parcours dans `tests/e2e`, verts sur `main` ;
  pas encore lancés sur le poste : Chromium de Playwright non téléchargé)
- Retours du 2026-10-15 sur le serveur de test : photo entière sur les cartes (#8, miniature
  non recadrée, `manage.py regenerer_miniatures`) ; email confirmé obligatoire pour déposer
  et écrire à un vendeur (#3, `VERIFIED_EMAIL_REQUIRED`) ; emails encore capturés par
  Mailpit sur le serveur : Brevo à configurer par le propriétaire
- Référencement (2026-10-15, sans publicité) : `robots.txt`, `sitemap.xml`, adresse
  canonique (#15) ; pages `/categorie/<slug>/[<ville>/]` et `/ville/<slug>/` (#9) ; Open
  Graph et schema.org `Product` sur la page annonce (#8) ; Search Console à faire par le
  propriétaire (runbook, « Référencement »)
- Ajout au #14 (2026-10-15) : bannière « Installer l'application » sur l'accueil
  (`static/js/install.js`), seulement dans le navigateur ; « Plus tard » = 30 jours
- Ajout au #3 : connexion avec Google (ADR 0002, allauth `socialaccount`), bouton en tête
  des pages de connexion et d'inscription, masqué sans `GOOGLE_CLIENT_ID` ; identifiants
  OAuth à créer par le propriétaire dans la console Google (runbook, étape 10)
- Ajout au #12 : email de nouveau message (`apps/messaging/notifications.py`), au premier
  non lu d'une conversation, pas pendant un échange en direct, sans le texte du message,
  désactivable au profil ; envoi dans la requête (pas de file en V1)
- #15 Mise en production : en ligne depuis le 2026-10-15 sur le KVM 2 Hostinger, à côté de
  GardienTV, à https://sugu.gardientv.tech (runbook, « Serveur partagé ») ; emails capturés
  par Mailpit en attendant Brevo ; tag `v0.1.0` après le dépôt d'essai du propriétaire
- Tâche en cours : #17 Exploitation et conformité — sauvegardes (`scripts/backup.sh`,
  `scripts/restore.sh`, copie sur le serveur + bucket R2), Sentry sans donnée personnelle,
  pages légales liées dans le pied de page. Côté propriétaire : comptes Cloudflare R2,
  Sentry et UptimeRobot, identité de l'éditeur et déclaration APDP (runbook)
- Points ouverts : le Dockerfile et compose.prod.yml n'ont pas encore été construits en vrai
  (ticket #15) ; le job `e2e` n'a pas encore tourné sur `main` (ticket #16) ; sur le poste de
  dev, un PostgreSQL Windows occupe déjà le port 5432 (lancer la base Docker sur un autre
  port) ; `EMAIL_URL` obligatoire en production (#15) pour les emails ;
  installation PWA à confirmer sur un vrai téléphone en HTTPS (#15) ; le navigateur intégré
  de Claude refuse les service workers (vérifier dans Chrome) ; ajouts de design des #8 à
  #17 (dont l'icône d'application, le pied de page et les pages légales) à reporter dans l'artefact de design ; pas de synonymes dans la
  recherche ; photos HEIC refusées sans JavaScript ; idées V2 notées le 2026-10-14 : prix
  anormaux, annonces recopiées par d'autres sites ; revenus : aucun en V1, liste ordonnée des
  sources rangée dans la section V2 de `docs/tickets.md` (mise en avant par mobile money
  d'abord, une fois quelques centaines d'annonces actives)
