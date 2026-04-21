FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps:
#   - libpq: psycopg runtime
#   - build-essential: wheels for some libs (reportlab etc.)
#   - libjpeg/zlib/freetype: Pillow
#   - curl: healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dev deps by default; prod image overrides CMD and can reinstall.
COPY requirements/ ./requirements/
RUN pip install -r requirements/dev.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
