# syntax=docker/dockerfile:1
# Renderer base: Debian 13 (trixie) with a frozen signed snapshot and the
# exact tool chain used by the shared-weekly Word export pipeline.
FROM python:3.14.7-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS renderer-base

WORKDIR /app
ENV KINDERGARTEN_DATA_DIR=/data

# Replace default Debian mirrors with a single frozen, HTTPS, signed snapshot.
# Release validity checking is disabled only for this snapshot repository.
RUN rm -f /etc/apt/sources.list \
    /etc/apt/sources.list.d/*.list \
    /etc/apt/sources.list.d/*.sources
COPY docker/render/debian.sources /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libreoffice-writer \
    poppler-utils \
    fontconfig \
    fonts-noto-cjk \
    gcc \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# Share Python dependencies between test and production images.
FROM renderer-base AS python-deps
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r requirements.txt
ENV USER=kindergarten

FROM python-deps AS render-test
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY templates/ templates/
COPY tests/ tests/
COPY scripts/ scripts/
COPY pytest.ini .
COPY specs/ specs/
RUN python -m scripts.render_environment
CMD ["python", "-m", "pytest", "tests/", "-m", "real_render", "-q"]

# Default published target contains application and explicit operations tools only.
FROM python-deps AS production
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY templates/ templates/
COPY scripts/render_environment.py scripts/weekly_layout_catalog.py scripts/weekly_cloud_fixture.py scripts/
RUN mkdir -p exports && python -m scripts.render_environment
EXPOSE 8080
CMD ["python", "-m", "app.main"]
