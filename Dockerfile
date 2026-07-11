FROM python:3.11-slim

ARG SUPERCRONIC_VERSION=v0.2.33
ARG TARGETARCH
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && curl -fsSLo /usr/local/bin/supercronic \
       "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}" \
    && chmod +x /usr/local/bin/supercronic \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 etl
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src src
COPY config config
COPY scheduler/crontab /etc/korean-rental-etl/crontab

RUN pip install --no-cache-dir . \
    && patchright install --with-deps chromium \
    && mkdir -p /var/lib/korean-rental-etl /var/log/korean-rental-etl \
    && chown -R etl:etl /app /var/lib/korean-rental-etl /var/log/korean-rental-etl /ms-playwright

USER etl
HEALTHCHECK CMD ["etl-runner", "healthcheck"]
ENTRYPOINT ["supercronic", "-passthrough-logs", "/etc/korean-rental-etl/crontab"]
