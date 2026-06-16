# ── Build stage 1: dependencies ──
FROM python:3.12-slim AS deps
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc gfortran libopenblas-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Build stage 2: data migration ──
FROM deps AS data-builder
WORKDIR /app
RUN pip install --user --no-cache-dir pandas openpyxl
COPY data/source/ ./data/source/
COPY data/schema.sql ./data/
COPY data/migrate_data.py ./data/
COPY app/bridge_db.py ./app/
RUN python -m data.migrate_data
# Verify
RUN python -c "from app.bridge_db import query; r=query('SELECT COUNT(*) as c FROM bridges'); print(f'Bridges: {r[0][\"c\"]}')"

# ── Runtime stage ──
FROM python:3.12-slim
WORKDIR /app

COPY --from=deps /root/.local /root/.local
ENV PATH="/root/.local/bin:$PATH"

# Copy built database from data builder
COPY --from=data-builder /app/data/cargo_bridge.db ./data/
COPY --from=data-builder /app/data/schema.sql ./data/

# Copy application code
COPY app/ ./app/
COPY data/ ./data/
COPY spider/ ./spider/
COPY bootstrap.py .

EXPOSE 9876
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9876/health')"

CMD ["python", "-c", "from bootstrap import ensure_ready; ensure_ready(); import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=9876)"]
