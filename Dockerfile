FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY jev ./jev
ARG INSTALL_LAYA=1
RUN if [ "$INSTALL_LAYA" = "1" ]; then pip install --no-cache-dir --prefix=/install '.[laya]'; else pip install --no-cache-dir --prefix=/install .; fi

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JEV_CONFIG=/app/config/jev.yaml \
    HF_HOME=/models

RUN addgroup --system jev && adduser --system --ingroup jev jev
RUN mkdir -p /models && chown jev:jev /models
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=jev:jev jev /app/jev
COPY --chown=jev:jev config /app/config

USER jev
EXPOSE 8080 8081
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["jev", "health", "--url", "http://127.0.0.1:8080/health"]
ENTRYPOINT ["jev"]
CMD ["serve"]
