FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY web ./web
COPY config ./config

RUN pip install --no-cache-dir -e ".[app]"

ENV PORT=8000
ENV TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json

EXPOSE 8000

CMD ["sh", "-c", "uvicorn trading_signal_intelligence.product.cloud_app:app --host 0.0.0.0 --port ${PORT}"]
