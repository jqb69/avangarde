# Dockerfile for avanagarde
FROM python:3.8-slim

WORKDIR /app

COPY run/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run/ .

EXPOSE 80

CMD ["python", "main.py"]
