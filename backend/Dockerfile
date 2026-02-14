FROM python:3.11-slim

# Install system dependencies for WeasyPrint in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy ONLY requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with pip cache
# This layer will only rebuild if requirements.txt changes
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p /app/logs

# Copy application code LAST
# This way code changes don't invalidate dependency layers
COPY . .

# Set environment variable for logs
ENV LOG_DIR=/app/logs

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
