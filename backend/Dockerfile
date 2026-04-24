FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps:
#   - libpq: psycopg runtime
#   - build-essential: wheels for some libs (reportlab etc.)
#   - libjpeg/zlib/freetype: Pillow
#   - libpango/cairo/gdk-pixbuf + shared-mime-info: WeasyPrint (HTML→PDF for
#     contract docgen authored via Tiptap)
#   - libreoffice-core/writer: .docx → PDF headless conversion for the
#     parallel lawyer-authored template path (docxtpl + soffice)
#   - fonts-dejavu/fonts-noto/fonts-liberation: glyph coverage for
#     Cyrillic + Latin + Uzbek + Word-compatible metrics (Liberation
#     Serif/Sans stand in for Times New Roman / Arial so .docx templates
#     render with consistent spacing)
#   - curl: healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libreoffice-core \
    libreoffice-writer \
    fonts-dejavu \
    fonts-noto \
    fonts-liberation \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dev deps by default; prod image overrides CMD and can reinstall.
COPY requirements/ ./requirements/
RUN pip install -r requirements/dev.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
