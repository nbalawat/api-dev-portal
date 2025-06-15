# Multi-stage Dockerfile for FastAPI Developer Portal

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser docker/ ./docker/

# Make scripts executable
RUN chmod +x ./docker/scripts/*.sh

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/docker/scripts/entrypoint.sh"]

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage (for development builds)
FROM production as development

# Switch back to root to install development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    less \
    && rm -rf /var/lib/apt/lists/*

# Switch back to app user
USER appuser

# Override command for development (with reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Test stage (for running tests in containerized environment)
FROM production as test

# Switch to root to install test dependencies and copy test files
USER root

# Install additional test dependencies if needed
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy test files and scripts
COPY --chown=appuser:appuser tests/ ./tests/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser pytest.ini ./

# Create test reports directory
RUN mkdir -p /app/reports && \
    chown -R appuser:appuser /app/reports

# Switch back to app user
USER appuser

# Default test command
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=app", "--cov-report=html:/app/reports/coverage", "--junitxml=/app/reports/junit.xml"]