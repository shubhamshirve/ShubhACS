FROM python:3.11-slim

LABEL maintainer="ACS Server" description="TR-069/TR-369 ACS Backend"

# Install only required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    traceroute \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app/backend

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir speedtest-cli --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ 2>/dev/null || true

# Copy source code
COPY . .

EXPOSE 8001

# Single worker to minimize RAM; increase if resources allow
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--loop", "uvloop"]
