FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY jev ./jev
ARG INSTALL_LAYA=1
ARG LAYA_VERSION=0.3.5
ARG TORCH_CPU_VERSION=2.9.1+cpu
RUN if [ "$INSTALL_LAYA" = "1" ]; then \
      pip install --no-cache-dir --prefix=/install --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_CPU_VERSION}"; \
      pip install --no-cache-dir --prefix=/install --no-deps \
        . "laya==${LAYA_VERSION}" "transformers>=4.48.0" "safetensors>=0.4.0" \
        "huggingface_hub>=0.20.0" "numpy>=1.20" PyYAML \
        filelock fsspec httpx anyio certifi httpcore h11 tqdm typing_extensions \
        regex tokenizers requests packaging pyyaml click sympy networkx jinja2 idna urllib3 charset-normalizer; \
    else \
      pip install --no-cache-dir --prefix=/install .; \
    fi

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
