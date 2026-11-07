# Separate isolated cron worker. NEVER use as the live VowSig application image.
FROM postgres:18-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv age ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/vowsig-backup-venv \
    && /opt/vowsig-backup-venv/bin/pip install --no-cache-dir 'boto3>=1.35,<2'

WORKDIR /app
COPY ops/pg_recovery/backup.py /app/backup.py
COPY config/tls/railway-postgres-root-ca-20261104.pem /app/config/tls/railway-postgres-root-ca-20261104.pem
RUN chmod 0444 /app/config/tls/railway-postgres-root-ca-20261104.pem \
    && useradd --create-home --uid 10001 vowsigbackup \
    && mkdir -p /tmp/vowsigbackup \
    && chown vowsigbackup:vowsigbackup /tmp/vowsigbackup
USER vowsigbackup
ENV TMPDIR=/tmp/vowsigbackup
CMD ["/opt/vowsig-backup-venv/bin/python", "/app/backup.py"]
