FROM python:3.11-slim

WORKDIR /app

# Installer Docker CLI pour interagir avec les conteneurs
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 13492

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "13492"]
