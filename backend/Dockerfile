# Backend Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --upgrade pip

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Command for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Install production dependencies only
RUN pip install --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-dev -r requirements.txt

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY . .
RUN chown -R appuser:appuser /app

# Create logs directory
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]