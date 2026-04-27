# Dockerfile for avanagarde
FROM python:3.11-slim

WORKDIR /app

# System tools for Telethon (cryptg needs build-essential for C-extensions)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command if none is provided by rundos.sh
CMD ["python3", "main.py"]
