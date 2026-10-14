# Sugu

Site de petites annonces généraliste entre particuliers, conçu pour les
connexions lentes et l'usage mobile. Installable comme application (PWA).

## Fonctionnalités (V1)

- Dépôt d'annonces avec photos (jusqu'à 6, redimensionnées en WebP)
- Recherche par mots-clés, catégorie, ville et fourchette de prix
- Comptes utilisateurs avec numéro de téléphone de contact
- Messagerie entre acheteur et vendeur
- Favoris
- Aucun paiement intégré : le vendeur indique les modes de règlement acceptés
  (paiement à la livraison, mobile money)

## Stack

Python 3.14 · Django 6.1 · htmx 2 · Tailwind CSS 4 (binaire standalone, sans Node) ·
PostgreSQL 18 · Cloudflare R2 (photos) · Docker · Caddy 2.11 · GitHub Actions

Versions exactes et politique de mise à jour : `docs/versions.md`.

Voir `docs/design.md` et `docs/adr/` pour les décisions d'architecture.

## Prérequis

- Docker et Docker Compose
- [uv](https://docs.astral.sh/uv/) (gestion des dépendances Python)
- Le binaire Tailwind CSS : `scripts/install-tailwind.sh` (`./tailwindcss`, ou `./tailwindcss.exe`
  sous Windows avec Git Bash)

## Installation

```bash
git clone https://github.com/<toi>/sugu.git
cd sugu
cp .env.example .env          # les valeurs locales sont déjà bonnes
uv sync                       # installe Python 3.14 et les dépendances
uv run pre-commit install     # ruff avant chaque commit
docker compose up -d db       # démarre PostgreSQL 18
uv run python manage.py migrate
uv run python manage.py seed  # catégories, villes et annonces de démo (idempotent)
uv run python manage.py createsuperuser
```

## Lancement en local

```bash
./tailwindcss -i static/css/input.css -o static/css/app.css --watch &
uv run python manage.py runserver
```

Site : http://localhost:8000 — Admin : http://localhost:8000/admin — Sonde : http://localhost:8000/sante/

## Tests

```bash
uv run pytest                 # unitaires + intégration
uv run pytest tests/e2e       # bout en bout (Playwright, nécessite le serveur)
uv run ruff check . && uv run ruff format --check .
```

## Déploiement

Voir `docs/runbook.md`.

## Documentation

- `CONTEXT.md` — résumé pour les sessions de travail avec l'IA
- `CLAUDE.md` / `AGENTS.md` — lus automatiquement par Claude Code et les éditeurs agentiques ; renvoient à `CONTEXT.md`
- `docs/design.md` — conception
- `docs/database.md` — schéma de données
- `docs/tests.md` — stratégie de tests
- `docs/git-workflow.md` — branches, commits, pull requests
- `docs/runbook.md` — exploitation (déploiement, sauvegardes, incidents)
- `docs/versions.md` — versions retenues, date de vérification, politique de mise à jour
- `docs/design-system.md` — charte graphique et bibliothèque de composants (`design/`)
- `docs/security.md` — modèle de menace et règles de sécurité
- `docs/tickets.md` — découpage en tâches jusqu'au minimum viable
- `docs/ia-rituels.md` — méthode de travail avec l'IA et prompts prêts à l'emploi
- `docs/adr/` — décisions d'architecture
