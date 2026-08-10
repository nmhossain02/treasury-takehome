FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN apt-get update \
    && apt-get install --no-install-recommends -y tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app

WORKDIR /build
COPY packages/ocr ./packages/ocr
COPY apps/api ./apps/api
RUN pip install --no-cache-dir ./packages/ocr ./apps/api \
    && rm -rf /build

WORKDIR /app
USER app
EXPOSE 8080
CMD ["sh", "-c", "uvicorn label_verifier.main:app --host 0.0.0.0 --port ${PORT}"]
