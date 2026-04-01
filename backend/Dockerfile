FROM python:3.11-slim

WORKDIR /app

# Install system packages needed for diagnostics (ping, traceroute)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    iputils-ping \
    traceroute \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# emergentintegrations is hosted on a custom PyPI index
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

COPY . .

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
