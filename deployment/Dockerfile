FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 fazztv

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=fazztv:fazztv . .

# Create necessary directories
RUN mkdir -p /app/data /app/cache /app/logs && \
    chown -R fazztv:fazztv /app

# Switch to non-root user
USER fazztv

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import fazztv; print('healthy')" || exit 1

# Run the application
CMD ["python", "-m", "fazztv.main"]