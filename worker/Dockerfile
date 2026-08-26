FROM python:3.12-slim

WORKDIR /opt/valora

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
COPY worker/pyproject.toml worker/pyproject.toml
COPY worker/worker worker/worker

RUN pip install --no-cache-dir ./backend ./worker

CMD ["python", "-m", "worker.main"]
