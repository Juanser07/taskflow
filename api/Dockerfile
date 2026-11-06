# Contenedor "api": FastAPI + SQLAlchemy sobre Python 3.12
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1) Dependencias primero: Docker reutiliza esta capa si requirements.txt no cambia
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2) Código de la aplicación, ejecutado con un usuario sin privilegios
RUN useradd --create-home appuser
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
