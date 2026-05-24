FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared source code
COPY src/ /app/src/
COPY pyproject.toml /app/

# Copy service-specific files
COPY services/search_service/ /app/service/
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
    redis==5.2.1 \
    opensearch-py==2.7.1 \
    numpy==1.26.4

# Expose service port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the service
CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8003"]
