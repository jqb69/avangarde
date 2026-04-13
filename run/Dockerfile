# Dockerfile for avanagarde
FROM python:3.8-slim

WORKDIR /app

COPY run/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run/ .
COPY dos/rundos.sh .

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "4"]
