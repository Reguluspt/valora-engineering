FROM python:3.12-slim

ARG VCS_REF=unversioned
LABEL org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/Reguluspt/valora-engineering"

WORKDIR /opt/valora

ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=5

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
COPY worker/pyproject.toml worker/pyproject.toml
COPY worker/worker worker/worker

RUN pip install --no-cache-dir ./backend ./worker

CMD ["python", "-m", "worker.main"]
