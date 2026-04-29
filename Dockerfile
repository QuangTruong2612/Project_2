# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps cho một số package C/Cython (chromadb, PyMuPDF, sentence-transformers, ...)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài deps trước để tận dụng cache layer
COPY requirements.txt setup.py README.md ./
COPY src/__init__.py src/__init__.py

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy source code
COPY src ./src

EXPOSE 8000

# Healthcheck dùng /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
