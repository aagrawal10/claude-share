# Multi-stage build for production Flask app
FROM python:3.12-slim as builder

# Set build arguments and environment
ARG PIPENV_VENV_IN_PROJECT=1
ARG PIPENV_IGNORE_VIRTUALENVS=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY Pipfile Pipfile.lock ./

# Generate requirements.txt from Pipfile and install dependencies
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir --upgrade pip && \
    pipenv requirements > requirements.txt && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/app/.venv/bin:$PATH"
ENV FLASK_ENV=production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy entrypoint script and make executable
COPY --chown=appuser:appuser entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories and set permissions
RUN mkdir -p ./claude_sessions && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)"

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Default command
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
