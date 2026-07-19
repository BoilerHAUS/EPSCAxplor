FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build provenance: the deploy workflow passes the commit SHA so /health can
# report which build is live, and the deploy poll can confirm it shipped (#75).
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA

COPY src/ ./src/
# Operator CLIs (create_user, create_api_key) — no registration endpoint in
# Phase 3, so these are run against the deployed image. Shipping them here lets
# `docker exec`/Dokploy Terminal use the container's own DATABASE_URL without a
# bind mount.
COPY scripts/ ./scripts/

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
