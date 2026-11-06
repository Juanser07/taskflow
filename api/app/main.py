"""Punto de entrada de la API TaskFlow."""
import logging
import socket
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from . import __version__
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .routers import auth, projects, tasks
from .seed import seed

logger = logging.getLogger("uvicorn.error")


def init_db(retries: int = 10, delay: float = 2.0) -> None:
    """Crea las tablas. Reintenta por si el contenedor de la base aún está arrancando."""
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Base de datos lista (%s)", engine.dialect.name)
            return
        except OperationalError:
            logger.warning("BD no disponible (intento %s/%s), reintentando...", attempt, retries)
            time.sleep(delay)
    raise RuntimeError("No se pudo conectar a la base de datos")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.seed_data:
        with SessionLocal() as db:
            if seed(db):
                logger.info("Datos de ejemplo cargados")
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Gestor colaborativo de proyectos y tareas (Kanban). Proyecto de Integración Continua.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/api/health", tags=["Salud"])
def health(db: Session = Depends(get_db)):
    """Verifica que la API está viva y que puede hablar con la base de datos."""
    info = {
        "status": "ok",
        "service": "taskflow-api",
        "version": __version__,
        "container": socket.gethostname(),
        "database": {"engine": engine.dialect.name, "host": engine.url.host},
    }
    try:
        db.execute(text("SELECT 1"))
        info["database"]["status"] = "ok"
        return info
    except Exception as exc:  # noqa: BLE001
        info["status"] = "degraded"
        info["database"]["status"] = "error"
        info["database"]["detail"] = str(exc.__class__.__name__)
        return JSONResponse(status_code=503, content=info)
