# syntax=docker/dockerfile:1.7
# ---------- Builder stage: install deps into a separate layer ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Install uv (fast Python package manager).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy ONLY dependency manifests first so this layer is cached when only
# source code changes.
COPY pyproject.toml uv.lock ./

# Install runtime deps into the system Python (no virtualenv in container).
RUN uv pip install --system --no-cache -r uv.lock

# ---------- Runtime stage: slim image with just the app ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Create non-root user for the app.
RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

# Copy installed Python packages from builder.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code.
COPY --chown=app:app main.py database.py ./
COPY --chown=app:app templates ./templates
COPY --chown=app:app static ./static

# Persist DB outside the image via a mounted volume.
RUN mkdir -p /app/data && chown -R app:app /app/data
ENV SCOREBOARD_DB=/app/data/scoreboard.db

USER app

EXPOSE 8000

# Simple healthcheck against the home page.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]