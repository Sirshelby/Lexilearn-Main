FROM python:3.12-slim

# uv installs exactly what's in uv.lock, same as Vercel and CI do.
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

# Don't run as root inside the container
RUN useradd --create-home --uid 1000 lexi && chown -R lexi /app
USER lexi

EXPOSE 8000

# Migrations run on start so a fresh database is always ready. With several
# replicas, move this into a one-off release job instead (see docs).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*'"]
