# Dockerfile for avanagarde
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Paths are relative to the ROOT of the repo because context is "."
COPY run/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from the run folder into the container root
COPY run/ .

CMD ["python3", "main.py"]
