# Multi-stage Dockerfile for photo-service

# ##################################
# Base stage - shared dependencies
# ##################################
# #################################
# Base stage - shared dependencies
# #################################




FROM python:3.12.8-slim AS base

WORKDIR /app

# Mandatory for APT_CACHE variable (see Dockerfile doc)
ARG APT_CACHE

# Configure APT proxy if APT_CACHE is set
RUN if [ -n "$APT_CACHE" ]; then \
      echo "Acquire::http::Proxy \"$APT_CACHE\";" > /etc/apt/apt.conf.d/01proxy; \
      echo "Acquire::http::Proxy \"$APT_CACHE\";" > /etc/apt/apt.conf; \
    fi
# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ##################################
# Proto generation stage
# ##################################

FROM base AS proto-gen

# Copy proto file
COPY proto/tags.proto ./proto/

# Generate Python gRPC code
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=. \
    --grpc_python_out=. \
    ./proto/tags.proto


# ##################################
# Development stage
# ##################################

FROM base AS photo-dev

# Install dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl vim nano bash-completion \
    && rm -rf /var/lib/apt/lists/*

# Install test dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy startup script
COPY start-uvicorn.sh /app/
RUN chmod +x /app/start-uvicorn.sh

# Install dev tools
RUN pip install --no-cache-dir \
    black==24.10.0 \
    ruff==0.8.4 \
    mypy==1.13.0 \
    ipython==8.31.0

# Configure git
RUN git config --system --add safe.directory /app

CMD ["bash"]

# ##################################
# Production stage
# ##################################

FROM base AS production

# Copy application code
COPY main.py config.py database.py models.py exceptions.py clients.py tags_pb2.py tags_pb2_grpc.py  photo_of_day_pb2.py photo_of_day_pb2_grpc.py /
COPY routers/ ./routers/

# Copy proto directory
COPY proto/ ./proto/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/health')"

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]


# ##################################
# Test stage
# ##################################

FROM base AS test

# Install test dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy application code
COPY main.py config.py database.py models.py exceptions.py clients.py ./
COPY routers/ ./routers/

# Copy proto
COPY proto/ ./proto/

# Copy generated proto code
COPY --from=proto-gen /app/tags_pb2.py /app/tags_pb2_grpc.py ./

# Copy test files
COPY pytest.ini conftest.py ./
COPY test_*.py ./

# Create non-root user
RUN useradd -m -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command for tests
CMD ["pytest", "-v"]
