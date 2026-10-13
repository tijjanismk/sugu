FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/opt/venv
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
WORKDIR /app

# Dépendances d'abord, pour profiter du cache Docker
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Tailwind CSS v4 standalone (pas de Node)
ARG TAILWIND_VERSION=v4.3.3
ADD https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-x64 /usr/local/bin/tailwindcss
RUN chmod +x /usr/local/bin/tailwindcss

COPY . .
RUN tailwindcss -i static/css/input.css -o static/css/app.css --minify \
 && SECRET_KEY=build DATABASE_URL=sqlite:///tmp/build.db \
    /opt/venv/bin/python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["/opt/venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
