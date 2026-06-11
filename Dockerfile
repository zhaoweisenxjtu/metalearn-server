FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e ".[server,knowledge]"

# Copy source
COPY src/ ./src/

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run server
CMD ["python", "-m", "src.adapters.http_api.server"]
