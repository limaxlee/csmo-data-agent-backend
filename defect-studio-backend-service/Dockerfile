ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}

WORKDIR /app

# Trust the Samsung corporate CA chain (proxy-internal mirrors).
COPY build-ca/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
# pip ships its own certifi bundle; point it at the system store (which now
# includes the corporate CA) so proxied HTTPS works during build.
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "src.container.app:app", "--host", "0.0.0.0", "--port", "8080"]

