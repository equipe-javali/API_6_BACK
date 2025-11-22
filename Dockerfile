FROM python:3.11-slim
WORKDIR /app

# pacotes do sistema necessários:
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY req.txt .

# upgrade pip, setuptools, wheel e criar wheels para acelerar installs
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r req.txt || true
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r req.txt

COPY . .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]