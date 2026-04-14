# Dockerfile for avanagarde
FROM python:3.8-slim

WORKDIR /app

COPY run/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run/ .
COPY dos/rundos.sh .

EXPOSE 80

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "main:app"]
