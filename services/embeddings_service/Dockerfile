FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/ /app/src/
COPY requirements-base.txt /app/
COPY services/embeddings_service/ /app/service/
RUN touch /app/service/__init__.py

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements-base.txt

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8002"]
