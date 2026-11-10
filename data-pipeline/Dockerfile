# Immagine della pipeline dati: il pacchetto f1-pipeline installato e il
# dataset di esempio, pronta per `docker compose run --rm pipeline <sottocomando> ...`.
# Il dataset completo e il formato intermedio entrano come volumi (/data).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    F1_RAW_DIR=/data/raw \
    F1_SAMPLE_DIR=/app/sample \
    F1_PROCESSED_DIR=/data/processed

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install .

# Dataset di esempio (stagioni 2022-2024, pochi MB): l'unico dato nell'immagine.
COPY sample ./sample

ENTRYPOINT ["f1-pipeline"]
