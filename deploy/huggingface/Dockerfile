# Hugging Face Space (Docker SDK) for DOMINO: the same image as deploy/single/Dockerfile, but the source is
# cloned from GitHub, so the Space needs only this file and README.md. Keep the two Dockerfiles in sync.
# To deploy a newer commit: Space -> Settings -> Factory rebuild.

# ---- source ----
FROM alpine:3.20 AS src
ARG REPO=https://github.com/arihantjaino7/domino-agent.git
ARG REF=main
RUN apk add --no-cache git && git clone --depth 1 --branch "$REF" "$REPO" /src

# ---- frontend ----
FROM node:24-slim AS web
RUN corepack enable && corepack prepare pnpm@11.15.0 --activate
WORKDIR /web
COPY --from=src /src/frontend/package.json /src/frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY --from=src /src/frontend/ ./
RUN pnpm build

# ---- app on the FalkorDB image ----
FROM falkordb/falkordb@sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_INSTALL_DIR=/opt/python PYTHONUNBUFFERED=1 \
    BROWSER=0 FALKORDB_HOST=127.0.0.1 FALKORDB_PORT=6379 RECORD_REPLAYS=false \
    DOMINO_STATIC_DIR=/app/frontend/dist PORT=7860
WORKDIR /app/backend
COPY --from=src /src/backend/pyproject.toml /src/backend/uv.lock /src/backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY --from=src /src/backend/ ./
RUN uv sync --frozen --no-dev
COPY --from=web /web/dist /app/frontend/dist
COPY --from=src /src/demo/replays/ /app/demo/replays/
COPY --from=src /src/deploy/single/start.sh /usr/local/bin/domino-start
RUN chmod +x /usr/local/bin/domino-start && mkdir -p /app/backend/runs /var/lib/falkordb/data \
    && chown -R 1000:1000 /app/backend/runs /var/lib/falkordb && chmod -R a+rX /opt/python /app
ENV PATH=/app/backend/.venv/bin:$PATH
USER 1000
EXPOSE 7860
ENTRYPOINT []
CMD ["/usr/local/bin/domino-start"]
