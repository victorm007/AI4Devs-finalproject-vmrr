# Imagen de la aplicación (readme, sección 2.4.1): Python 3.12 + Django 5.2 + Gunicorn.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Primero las dependencias, para aprovechar la caché de Docker
COPY requirements.txt requirements-dev.txt ./
# INSTALAR_DEV=true en desarrollo (pytest, ruff y djLint dentro del contenedor); false en producción
ARG INSTALAR_DEV=false
RUN pip install -r requirements.txt \
 && if [ "$INSTALAR_DEV" = "true" ]; then pip install -r requirements-dev.txt; fi

# Usuario sin privilegios: el proceso nunca corre como root
ARG APP_UID=1000
RUN useradd --create-home --uid "$APP_UID" django \
 && mkdir -p /app/staticfiles && chown django /app/staticfiles

COPY --chown=django . .
USER django

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
