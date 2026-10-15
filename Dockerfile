FROM python:3.14-slim AS base

# Réglages de production partout dans l'image : manage.py prend sinon ceux de développement.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/opt/venv \
    DJANGO_SETTINGS_MODULE=config.settings.prod PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
WORKDIR /app

# Dépendances d'abord, pour profiter du cache Docker
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Tailwind CSS v4 standalone (pas de Node), vérifié par son empreinte publiée (sha256sums.txt)
ADD --checksum=sha256:dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a \
    https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-linux-x64 \
    /usr/local/bin/tailwindcss
RUN chmod +x /usr/local/bin/tailwindcss

COPY . .
# Fichiers statiques avec leur manifeste (noms hachés) ; valeurs factices, rien n'est contacté.
# input.css est la source Tailwind (@import "tailwindcss") : seul app.css est servi.
RUN tailwindcss -i static/css/input.css -o static/css/app.css --minify \
 && SECRET_KEY=build ALLOWED_HOSTS=build ADMIN_URL=build-only-not-used/ \
    DATABASE_URL=sqlite:////tmp/build.db EMAIL_URL=smtp://build \
    python manage.py collectstatic --noinput --ignore input.css

# Utilisateur sans privilège ; /app/media existe pour que le volume des photos lui appartienne.
RUN useradd --create-home app && mkdir -p /app/media && chown -R app:app /app
USER app
EXPOSE 8000
# Migrations puis Gunicorn. Pas de journal d'accès : les adresses de confirmation d'email et
# de mot de passe oublié contiennent des jetons (docs/security.md, « Surveillance »).
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 30"]
