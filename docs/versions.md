# Versions de référence — Sugu

Vérifiées le **2026-10-11** (PyPI, GitHub, registre Docker). Les versions
exactes installées sont figées dans `uv.lock` ; ce fichier sert de référence
humaine et trace les choix.

## Runtime et infrastructure

| Composant       | Version retenue | Dernière connue | Où c'est fixé                      | Remarque |
|-----------------|-----------------|-----------------|------------------------------------|----------|
| Python          | 3.14 (3.14.7)   | 3.14.7 ; 3.15.0 sortie le 2026-10-09 | `.python-version`, `pyproject.toml`, `Dockerfile` | Django 6.1 supporte 3.12, 3.13 et 3.14 uniquement. Passer à 3.15 quand Django l'annoncera (6.2, avril 2027) |
| Django          | 6.1.2           | 6.1.2 (2026-10-06) | `pyproject.toml`                 | Support courant jusqu'en avril 2027 ; 6.2 LTS attendu en avril 2027 |
| PostgreSQL      | 18.6            | 18.6 ; 19 encore en bêta | `compose.yml`, `compose.prod.yml`, `ci.yml` | Image 18+ : volume monté sur `/var/lib/postgresql` |
| Caddy           | 2.11.7          | 2.11.7          | `compose.prod.yml`                 | |
| uv              | 0.13.0          | 0.13.0 (2026-10-09) | `Dockerfile`, `ci.yml`           | Version récente : si problème, revenir à 0.12.x |
| Tailwind CSS    | 4.3.3           | 4.3.3           | `Dockerfile`, `scripts/install-tailwind.sh` | v4 : configuration en CSS, pas de `tailwind.config.js` |
| htmx            | 2.0.11          | 2.0.11          | `static/js/htmx.min.js` (vendu)    | Mettre à jour à la main, fichier commité |

## Dépendances Python (`pyproject.toml`)

| Paquet             | Version |
|--------------------|---------|
| django             | 6.1.2   |
| django-allauth     | 65.19.7 |
| django-environ     | 0.14.0  |
| django-storages    | 1.14.6  |
| django-htmx        | 1.29.0  |
| whitenoise         | 6.12.0  |
| psycopg[binary]    | 3.3.6   |
| pillow             | 12.3.0  |
| gunicorn           | 26.2.0  |
| argon2-cffi        | 25.1.0  |
| pytest             | 9.1.1   |
| pytest-django      | 4.14.0  |
| pytest-cov         | 7.1.0   |
| factory-boy        | 3.3.3   |
| playwright         | 1.63.0  |
| pytest-playwright  | 0.10.0  |
| ruff               | 0.17.0 (2026-10-09, épinglé en exact pour que pre-commit et la CI soient identiques) |
| pre-commit         | 4.6.2   |

## Actions GitHub (`.github/workflows/ci.yml`)

| Action              | Version |
|---------------------|---------|
| actions/checkout    | v7      |
| astral-sh/setup-uv  | v10     |

## Politique de mise à jour

1. **Dependabot** (`.github/dependabot.yml`) ouvre des PR hebdomadaires. Les
   mises à jour mineures et correctives des paquets Python sont groupées.
2. Une PR de mise à jour se fusionne quand la CI est verte, après lecture des
   notes de version pour les changements majeurs.
3. **Délai de prudence** : pour les briques critiques en production (Django,
   PostgreSQL, uv, psycopg), attendre au moins deux semaines après une
   version majeure ou mineure avant de l'adopter. Les outils de développement
   (ruff, pytest) peuvent suivre immédiatement.
4. **Versions majeures** (Django 7, PostgreSQL 19, Tailwind 5) : jamais via
   Dependabot seul. Lire le guide de migration, écrire un ADR si le changement
   touche l'architecture, tester en staging.
5. Mettre à jour ce fichier à chaque montée de version significative.

## Ce qui a été volontairement écarté

- **Python 3.15** : sorti il y a deux jours, pas encore supporté par Django.
- **PostgreSQL 19** : encore en bêta.
- **Django 6.0** : fin de support courant depuis août 2026 ; 6.1 est la
  version à jour.
