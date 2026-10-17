# DOMINO app image: the built React frontend served by FastAPI (one origin), plus the MCP endpoint.
# Stage 1 builds the frontend; stage 2 installs the backend from uv.lock (exact versions).

FROM node:24-slim AS web
RUN corepack enable && corepack prepare pnpm@11.15.0 --activate
WORKDIR /web
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev
COPY --from=web /web/dist /app/frontend/dist
ENV PATH=/app/backend/.venv/bin:$PATH DOMINO_STATIC_DIR=/app/frontend/dist
EXPOSE 8000
# Build the world only if it is missing (a restart keeps the live demo), then serve.
# --proxy-headers so per-visitor rate limits see the real client IP behind Caddy.
CMD ["sh", "-c", "python -m domino.seed.ensure && exec uvicorn domino.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*"]
