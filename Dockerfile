# Imagen única para la API, el dashboard, el listener de Gmail y las tareas
# de mantenimiento. Cada servicio de docker-compose.yml cambia el comando.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/app/data/salida

# tesseract-ocr: OCR de CVs escaneados (HU-15).
# curl: healthchecks de los contenedores.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt constraints.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt -c constraints.txt

COPY . .

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data/salida \
    && chown -R app:app /app/data

USER app

EXPOSE 8000 8501

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
