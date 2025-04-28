# Platform-agnostic Docker support with UV integration
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    MCP_MEMORY_CHROMA_PATH=/app/chroma_db \
    MCP_MEMORY_BACKUPS_PATH=/app/backups \
    PYTHONPATH=/app

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy essential files
COPY requirements.txt .
COPY setup.py .
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .
COPY scripts/install_uv.py .

# Install UV
RUN python install_uv.py

# Create directories for data persistence
RUN mkdir -p /app/chroma_db /app/backups

# Copy source code
COPY src/ /app/src/
COPY uv_wrapper.py memory_wrapper_uv.py ./

# Install the package with UV
RUN python -m uv pip install -e .

# Configure stdio for MCP communication
RUN chmod a+rw /dev/stdin /dev/stdout /dev/stderr

# Add volume mount points for data persistence
VOLUME ["/app/chroma_db", "/app/backups"]

# Expose the port (if needed)
EXPOSE 8000

# Run the memory service using UV
ENTRYPOINT ["python", "-u", "uv_wrapper.py"]
