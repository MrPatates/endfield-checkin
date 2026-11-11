# python:3.14-alpine (multi-arch index), pinned for reproducible builds.
FROM docker.io/library/python@sha256:8c9a3bf2d6dea60d60a2ae2a07c2b2fb1e7d8daed64b146b6792c74ae0d62ac4

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="Endfield Check-in" \
      org.opencontainers.image.description="Automatic SKPORT daily check-in for Arknights: Endfield, with a web UI" \
      org.opencontainers.image.source="https://github.com/MrPatates/endfield-checkin" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.version="$APP_VERSION"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/endfield-checkin \
    DATA_DIR=/config \
    WEBUI_PORT=8080 \
    PUID=99 \
    PGID=100

COPY app/endfield_checkin /opt/endfield-checkin/endfield_checkin
RUN python -m compileall -q /opt/endfield-checkin \
    && python -c "import endfield_checkin.web" \
    && mkdir -p /config

VOLUME /config
EXPOSE 8080
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD ["python", "-m", "endfield_checkin.healthcheck"]
# Starts as root only to fix /config ownership, then switches to PUID:PGID.
ENTRYPOINT ["python", "-m", "endfield_checkin"]
