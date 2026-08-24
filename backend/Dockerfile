FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system workflix && adduser --system --ingroup workflix workflix
RUN mkdir -p /app/uploads && chown workflix:workflix /app/uploads

COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --no-cache-dir .

USER workflix

EXPOSE 8000

CMD ["sh", "-c", "if [ \"${WORKFLIX_PROCESS:-api}\" = \"worker\" ]; then exec python -m app.worker; else alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000; fi"]
