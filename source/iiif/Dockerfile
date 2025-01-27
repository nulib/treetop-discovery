FROM python:3.10-slim

# Install system dependencies required for building
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manifest_fetcher.py .

CMD ["python", "manifest_fetcher.py"]