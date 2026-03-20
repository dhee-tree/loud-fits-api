# ============================================================
# Stage 1: Builder — compile dependencies into a virtual env
# ============================================================
FROM python:3.13-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ============================================================
# Stage 2: Runtime — lean production image
# ============================================================
FROM python:3.13-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 1. Install SYSTEM RUNTIME dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# 3. Copy project files
COPY . /app/

# 4. Security: Create a non-root user
RUN addgroup --system django && \
    adduser --system --ingroup django django && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app

# 5. Make entrypoint executable
RUN chmod +x /app/scripts/entrypoint/entrypoint.sh

# Switch to non-root user
USER django

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint/entrypoint.sh"]
CMD ["gunicorn", "loud_fits_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
