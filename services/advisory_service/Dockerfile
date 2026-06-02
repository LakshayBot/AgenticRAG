FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (curl required for healthcheck)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared source library (config, schemas, services used by all Python microservices)
COPY src/ /app/src/

# Copy advisory router as the entrypoint app
COPY services/advisory_service/ /app/service/
RUN touch /app/service/__init__.py

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    pydantic==2.10.5 \
    pydantic-settings==2.7.1 \
    sqlalchemy==2.0.37 \
    psycopg2-binary==2.9.10 \
    httpx==0.28.1 \
    opensearch-py==2.7.1 \
    redis==5.2.1 \
    numpy==1.26.4

EXPOSE 8005

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8005/api/v1/advisories/health || exit 1

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "2"]
