# Meme distribution que l'image python-dev (Ubuntu 22.04) : meme Ghostscript
# 9.55, donc memes PDF produits qu'avant la separation.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ghostscript python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY app.py .
ENV PDF_GS_DOSSIERS=/data
EXPOSE 8000
USER nobody
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "3700", "app:app"]
