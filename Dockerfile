FROM python:3.12-slim

# Injected by CI: docker build --build-arg VERSION=0.3.0 .
# Falls back to "dev" for local builds so the image is always labelled.
ARG VERSION=dev

LABEL org.opencontainers.image.title="openlca-mcp" \
      org.opencontainers.image.description="MCP server for Life Cycle Assessment with openLCA — 24 tools for calculations, contributions, inventory, Sankey, and more." \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/SDAI-institute/openlca-mcp" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Ernest Boakye Danquah <dernestbanksch@gmail.com>"

WORKDIR /app

# Install dependencies first (layer cached unless requirements change)
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir \
    -r requirements.txt \
    "uvicorn>=0.23.0" \
    "starlette>=0.27.0" \
    "opentelemetry-sdk>=1.24.0" \
    "opentelemetry-exporter-otlp-proto-http>=1.24.0"

# Copy source
COPY src/ ./src/

# Non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp /app
USER mcp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "src.server"]
