FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8081

RUN addgroup --system app \
    && adduser --system --ingroup app --home /app app

WORKDIR /build
COPY apps/cola-mock ./apps/cola-mock
COPY tools/data/public_cola_common.py tools/data/build_public_cola_index.py ./tools/data/
COPY fixtures/public-cola/records.lock.json ./fixtures/public-cola/records.lock.json
RUN pip install --no-cache-dir ./apps/cola-mock \
    && mkdir -p /app/data \
    && python tools/data/build_public_cola_index.py \
        --lock fixtures/public-cola/records.lock.json \
        --output /app/data/public-cola.sqlite3 \
    && chmod 0444 /app/data/public-cola.sqlite3 \
    && rm -rf /build

WORKDIR /app
ENV COLA_INDEX_PATH=/app/data/public-cola.sqlite3
USER app
EXPOSE 8081
CMD ["sh", "-c", "uvicorn cola_mock.main:app --host 0.0.0.0 --port ${PORT}"]
