# syntax=docker/dockerfile:1.6

# ---- Build stage ----
# For reproducible builds, pin to a digest: python:3.13-slim@sha256:<digest>
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ---- Runtime stage ----
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SIDECAR_DATA_DIR=/data \
    PYTHONPATH=/install/lib/python3.13/site-packages \
    PATH=/install/bin:$PATH

# ca-certificates for TLS to OpenRouter. Everything else: no.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r -g 1000 sidecar \
    && useradd -r -u 1000 -g sidecar -d /app -s /usr/sbin/nologin sidecar \
    && mkdir -p /app /data \
    && chown sidecar:sidecar /app /data

COPY --from=builder /install /install
COPY --chown=sidecar:sidecar tools/ /app/tools/
COPY --chown=sidecar:sidecar src/ /app/src/

USER sidecar
WORKDIR /app

EXPOSE 8080
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health',timeout=3).status==200 else 1)"

CMD ["python", "tools/server.py"]
