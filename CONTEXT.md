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
- Dernière tâche terminée : #12 Messagerie (app `apps/messaging`, « Écrire au vendeur » sur
  l'annonce, conversation créée au premier message, envoi htmx ou formulaire classique,
  rafraîchissement htmx 10 s via `static/js/conversation.js` (pas de `hx-on` : future CSP),
  lecture à l'ouverture, pastille de non-lus dans la navigation, boîte `/messages/`)
- Tâche en cours : aucune ; prochaine : #13 Profil et contact
- Points ouverts : le Dockerfile et compose.prod.yml n'ont pas encore été construits en vrai
  (ticket #15) ; le job `e2e` n'a pas encore tourné sur `main` (ticket #16) ; sur le poste de
  dev, un PostgreSQL Windows occupe déjà le port 5432 (lancer la base Docker sur un autre
  port) ; pas encore d'avertissement par email d'un nouveau message ;
  ajouts de design des #8 à #12 à reporter dans l'artefact de design ; pas de synonymes dans la
  recherche ; photos HEIC refusées sans JavaScript ; idées V2 notées le 2026-10-14 : prix
  anormaux, annonces recopiées par d'autres sites ; revenus : aucun en V1, liste ordonnée des
  sources rangée dans la section V2 de `docs/tickets.md` (mise en avant par mobile money
  d'abord, une fois quelques centaines d'annonces actives)
