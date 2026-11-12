FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import pymupdf, pymupdf4llm; print(pymupdf.VersionBind)"
COPY app.py .

# Dossiers d'ou les documents peuvent etre lus par chemin (separes par ":")
ENV PDF_TEXTE_DOSSIERS=/data
EXPOSE 8000
USER nobody
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "900", "app:app"]
