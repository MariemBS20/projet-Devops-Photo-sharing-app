# Multi-stage Dockerfile for Photo of Day gRPC Service

# #################################
# Base stage - shared dependencies
# #################################

FROM gitlab-registry.imt-atlantique.fr/devops-lab/shared/python:3.12.8-slim AS base

WORKDIR /app

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

# Generate protobuf files
COPY proto/ ./proto/
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=. \
    --grpc_python_out=. \
    ./proto/photo_of_day.proto

# #################################
# Dev stage - for development
# #################################

FROM base AS photo-of-day-dev

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

# Install development tools
RUN pip install --no-cache-dir \
    black==24.10.0 \
    ruff==0.8.4 \
    mypy==1.13.0 \
    ipython==8.31.0

# Copy application code (SANS database.py et models.py)
COPY grpc_server.py config.py clients.py photo_of_day_pb2.py photo_of_day_pb2_grpc.py  ./

# Copy startup script
COPY start-grpc.sh /app/
RUN chmod +x /app/start-grpc.sh

# Configure git
RUN git config --system --add safe.directory /app

# Expose gRPC port
EXPOSE 50052

# Default command
CMD ["/app/start-grpc.sh"]

# #################################
# Production stage
# #################################

FROM base AS production

# Copy application code (SANS database.py et models.py)
COPY grpc_server.py config.py clients.py ./

# Copy startup script
COPY start-grpc.sh /app/
RUN chmod +x /app/start-grpc.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose gRPC port
EXPOSE 50052

# Health check (gRPC doesn't have HTTP, so we check if process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python grpc_server.py" || exit 1

# Run the gRPC server
CMD ["/app/start-grpc.sh"]

# #################################
# Test stage - with test dependencies
# #################################

FROM base AS test

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest==8.3.4 \
    pytest-asyncio==0.24.0 \
    pytest-cov==6.0.0

# Copy application code (SANS database.py et models.py)
COPY grpc_server.py config.py clients.py ./



# Copy startup script
COPY start-grpc.sh /app/
RUN chmod +x /app/start-grpc.sh

# Create non-root user
RUN useradd -m -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command for tests
CMD ["pytest", "-v"]