# Multi-stage Dockerfile for production and testing

# #################################
# Base stage - shared dependencies
# #################################

FROM python:3.12.8-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# #################################
# Dev stage - for devcontainer
# #################################

FROM base AS photographer-dev

# Install dev system tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    vim \
    nano \
    bash-completion \
    procps \
    htop \
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install test dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Install development tools
RUN pip install --no-cache-dir \
    black==24.10.0 \
    ruff==0.8.4 \
    mypy==1.13.0 \
    ipython==8.31.0 \
    pytest-cov==6.0.0

# Copy application code
COPY main.py config.py database.py models.py exceptions.py ./
COPY routers/ ./routers/

# Copy test files
COPY pytest.ini conftest.py ./
COPY test_*.py ./

# Configure git (for container usage)
RUN git config --system --add safe.directory /app

# Keep as root for flexibility (VSCode handles user remapping)
# Development tools work better with root in container

# Default command
CMD ["bash"]

# #################################
# Production stage
# #################################

FROM base AS production

# Copy application code
COPY main.py config.py database.py models.py exceptions.py ./
COPY routers/ ./routers/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/health')"

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

# #################################
# Test stage - withtest dependencies
# #################################

FROM base AS test

# Install test dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy application code
COPY main.py config.py database.py models.py exceptions.py ./
COPY routers/ ./routers/

# Copy test files
COPY pytest.ini .
COPY conftest.py .
COPY test_*.py ./

# Copy startup script
COPY start-uvicorn.sh /app/
RUN chmod +x /app/start-uvicorn.sh

# Create non-root user
RUN useradd -m -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command for tests
CMD ["pytest", "-v"]