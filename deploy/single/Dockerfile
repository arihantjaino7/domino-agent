# DOMINO in ONE container: FalkorDB (the pinned, tested image) + the FastAPI app + the built frontend.
# For hosts that run a single Docker container (Hugging Face Spaces, Render, a plain `docker run`).
# Build from the repo root:  docker build -f deploy/single/Dockerfile -t domino-single .
# Run:                       docker run --rm -p 7860:7860 domino-single      -> http://localhost:7860

# ---- source ----
FROM scratch AS src
COPY . /src

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
# Published recordings for Replay mode: a visitor can watch a real Claude Code run with no API key.
COPY --from=src /src/demo/replays/ /app/demo/replays/
COPY --from=src /src/deploy/single/start.sh /usr/local/bin/domino-start
# Hosts such as Hugging Face run the container as uid 1000: everything the app writes must be writable.
RUN chmod +x /usr/local/bin/domino-start && mkdir -p /app/backend/runs /var/lib/falkordb/data \
    && chown -R 1000:1000 /app/backend/runs /var/lib/falkordb && chmod -R a+rX /opt/python /app
ENV PATH=/app/backend/.venv/bin:$PATH
USER 1000
EXPOSE 7860
ENTRYPOINT []
CMD ["/usr/local/bin/domino-start"]
