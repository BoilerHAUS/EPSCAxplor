FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
# Operator CLIs (create_user, create_api_key) — no registration endpoint in
# Phase 3, so these are run against the deployed image. Shipping them here lets
# `docker exec`/Dokploy Terminal use the container's own DATABASE_URL without a
# bind mount.
COPY scripts/ ./scripts/

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
