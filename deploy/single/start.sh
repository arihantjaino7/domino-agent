#!/bin/sh
# One container, two processes: FalkorDB on localhost only, then the DOMINO app on $PORT (default 7860).
# Used by deploy/single/Dockerfile and deploy/huggingface/Dockerfile.
set -e

DATA="${FALKORDB_DATA_PATH:-/var/lib/falkordb/data}"
mkdir -p "$DATA"

# A public demo must never leave the MCP endpoint open: the tools change the shared live world.
# Without a key from the host's secrets, a random one is generated, so /mcp is effectively closed.
# MCP_OPEN=true opens /mcp to anyone with the URL (any Claude Code can connect without a key). The REST API is
# open in the same way, and buying still needs a click on Approve in the war room.
if [ "$MCP_OPEN" = "true" ]; then
  unset MCP_API_KEY
  echo "MCP_OPEN=true: /mcp needs no key."
elif [ -z "$MCP_API_KEY" ]; then
  MCP_API_KEY="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  export MCP_API_KEY
  echo "MCP_API_KEY not set: /mcp is closed (random key). Set it as a secret to use Claude Code against this server."
fi

# The MCP Host-header check must accept the public name. Render and Hugging Face tell the container what it is.
if [ -z "$DOMINO_PUBLIC_HOST" ]; then
  DOMINO_PUBLIC_HOST="${RENDER_EXTERNAL_HOSTNAME:-$SPACE_HOST}"
  export DOMINO_PUBLIC_HOST
fi

# FalkorDB listens only inside the container. FALKORDB_ARGS comes from the base image
# (MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000, the settings the spike passed with).
# shellcheck disable=SC2086
redis-server --protected-mode yes --bind 127.0.0.1 --port 6379 --dir "$DATA" --daemonize yes \
  --logfile "$DATA/falkordb.log" --loadmodule "$FALKORDB_BIN_PATH/falkordb.so" $FALKORDB_ARGS

i=0
until redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 60 ]; then echo "FalkorDB did not start"; cat "$DATA/falkordb.log"; exit 1; fi
  sleep 0.5
done
echo "FalkorDB ready"

cd /app/backend
# Build the demo world if it is missing (a restart keeps it), then serve the app and the built frontend.
python -m domino.seed.ensure
exec uvicorn domino.api.main:app --host 0.0.0.0 --port "${PORT:-7860}" --proxy-headers --forwarded-allow-ips='*'
