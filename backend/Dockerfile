# ── 生产构建：多阶段，预构建 DB，无 XLSX ──

# Stage 1: Python 依赖
FROM python:3.12-slim AS deps
WORKDIR /app
ARG PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_EXTRA_INDEX=https://pypi.org/simple
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends gcc gfortran libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt \
    -i ${PIP_INDEX} --extra-index-url ${PIP_EXTRA_INDEX} --trusted-host mirrors.aliyun.com

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app

COPY --from=deps /root/.local /root/.local
ENV PATH="/root/.local/bin:$PATH"

# 预构建的 bridge DB（数据源 XLSX 不进镜像）
COPY data/cargo_bridge.db ./data/
COPY data/schema.sql ./data/
COPY app/ ./app/
COPY spider/ ./spider/
COPY bootstrap.py .

EXPOSE 19876
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:19876/health')"

CMD ["python", "-c", "from bootstrap import ensure_ready; ensure_ready(); import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=19876)"]
