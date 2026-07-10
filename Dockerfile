# Multi-stage build for Jarvix NoLLM Web

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy source files (old and new)
COPY curious_mind.py app.py ./
COPY jarvix/ ./jarvix/

# Verify Python files are valid
RUN python -m py_compile curious_mind.py app.py jarvix/__init__.py

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r curiousmind && useradd -r -g curiousmind curiousmind

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/curiousmind/.local

# Copy application files from builder
COPY --from=builder /app/curious_mind.py /app/app.py ./
COPY --from=builder /app/jarvix ./jarvix

# Copy templates (HTML frontend)
COPY templates ./templates

# Create a volume mount point for persistent memory (data directory)
RUN mkdir -p /app/data && chown curiousmind:curiousmind /app/data

# Set environment variables
ENV PATH=/home/curiousmind/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:$PYTHONPATH

# Switch to non-root user
USER curiousmind

# Expose port for web interface
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=2 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health').read()" || exit 1

# Run the Flask app from /app directory
CMD ["python", "-m", "flask", "--app", "app", "run", "--host", "0.0.0.0"]
