# Sugu — instructions pour Claude Code

Lis d'abord le contexte du projet (règles, stack, conventions, décisions) :

@CONTEXT.md

## Comment travailler ici

- Une session = un ticket de `docs/tickets.md` (ou une issue GitHub). Commence par
  relire le ticket et ses critères d'acceptation ; propose un plan en 5 points
  maximum et attends l'accord avant d'écrire du code.
- Travaille sur une branche `feat/<n°>-<slug>` (ou `fix/`, `docs/`, `chore/`),
  jamais directement sur `main`.
- Chaque fonctionnalité arrive avec ses tests ; une vue qui modifie ou lit une
  donnée privée a un test « un autre utilisateur essaie » (403 ou 404).
- Avant de proposer un commit : `uv run ruff format .`, `uv run ruff check .`,
  `uv run pytest`. Un commit ne part pas avec un test rouge.
- Messages de commit en Conventional Commits, en français
  (`feat(listings): ajoute la recherche plein texte`).
- Pour une tâche d'interface, lis aussi `design/README.md` et le composant
  concerné dans `design/components/<Composant>/`.
- Pour une tâche touchant au modèle de données, lis `docs/database.md` et mets-le
  à jour dans la même PR.
- Règles de sécurité : `docs/security.md`. En cas de doute sur une permission,
  refuse l'accès et demande.

## Ce que tu ne fais pas sans demander

- Ajouter une dépendance (justifie-la ; un changement de stack passe par un ADR
  dans `docs/adr/`).
- Modifier une migration déjà commitée.
- Toucher à `compose.prod.yml`, au `Dockerfile`, à la CI ou à `.env.example`.
- Lancer une commande qui écrit sur une base autre que la base locale.
- Committer `.env`, un secret, ou un fichier généré (`static/css/app.css`, `staticfiles/`).

## Commandes utiles

```bash
uv sync                                   # dépendances
docker compose up -d db                   # PostgreSQL 18 local
uv run python manage.py migrate
uv run python manage.py runserver
./tailwindcss -i static/css/input.css -o static/css/app.css --watch
uv run pytest                             # unitaires + intégration
uv run pytest tests/e2e -o addopts="" --base-url http://localhost:8000
uv run ruff check . && uv run ruff format .
```

## En fin de session

Mets à jour la section « État d'avancement » de `CONTEXT.md` : dernière tâche
terminée, tâche en cours, points ouverts.
