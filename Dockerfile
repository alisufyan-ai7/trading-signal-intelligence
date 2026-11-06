FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY web ./web
COPY config ./config

RUN pip install --no-cache-dir -e ".[app,accounts]"

ENV PORT=8000
ENV TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json

EXPOSE 8000

# Uvicorn default access logs include the complete OAuth callback query string.
# Railway HTTP proxy telemetry still records methods, sanitized paths and statuses.
# Suppress application request-line logs; keep application errors and health checks.
CMD ["sh", "-c", "uvicorn trading_signal_intelligence.product.cloud_app:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
