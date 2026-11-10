# TaskFlow

Gestor colaborativo de proyectos y tareas tipo **Kanban**, construido como proyecto del módulo
**Énfasis Profesional I: Integración Continua** (Politécnico Grancolombiano).

| Entrega | Semana | Alcance | Estado |
|---|---|---|---|
| 1 | 3 | Proyecto en GitHub + contenedores Docker comunicados entre sí | ✅ |
| 2 | 5 | Jenkins como servidor de integración continua | ⏳ |
| 3 | 7–8 | Integración con Travis CI y Codeship + documentación final | ⏳ |

## Arquitectura

```
navegador ──:8080──▶  web (Nginx)  ──frontend-net──▶  api (FastAPI)  ──backend-net──▶  db (PostgreSQL)
                      frontend +                       lógica de negocio                  datos
                      proxy /api                        + JWT                              (volumen pgdata)
```

| Contenedor | Imagen | Redes | Puerto |
|---|---|---|---|
| `taskflow-web` | `nginx:1.27-alpine` + frontend | frontend-net | **8080** → 80 (único expuesto) |
| `taskflow-api` | `python:3.12-slim` + FastAPI | frontend-net, backend-net | 8000 (interno) |
| `taskflow-db` | `postgres:16-alpine` | backend-net (`internal: true`) | 5432 (interno) |

`web` **no** puede comunicarse con `db`: no comparten red. Solo `api` está en ambas.

## Tecnologías

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, JWT (PyJWT), bcrypt
- **Base de datos:** PostgreSQL 16 (relacional)
- **Frontend:** HTML, CSS y JavaScript sin frameworks, servido por Nginx
- **Contenedores:** Docker y Docker Compose
- **Pruebas:** pytest + TestClient (SQLite en memoria)
- **Control de versiones:** Git y GitHub (`main`, `develop`, `feature/*`)

## Cómo ejecutarlo

Requisitos: Git y Docker Desktop (Windows / macOS) o Docker Engine + Compose v2 (Linux).
No hace falta instalar Python, PostgreSQL ni Nginx: las imágenes se construyen en el equipo.

### Windows (PowerShell)

```powershell
git clone https://github.com/camtorrado/taskflow.git
cd taskflow
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

### macOS / Linux

```bash
git clone https://github.com/camtorrado/taskflow.git
cd taskflow
cp .env.example .env
docker compose up --build -d
docker compose ps
```

El comando `docker compose up --build -d` construye las imágenes e inicia
los tres servicios en segundo plano. Al ejecutar `docker compose ps`,
los servicios `db` y `api` deben aparecer como `healthy`.

> Los datos no viajan con el repositorio: una instalación nueva arranca con los datos de ejemplo.
> Si el puerto 8080 está ocupado, cambia `WEB_PORT` en `.env`.

- Aplicación: http://localhost:8080 (usuario demo `ana@taskflow.dev` / `taskflow123`)
- Documentación interactiva de la API (Swagger): http://localhost:8080/api/docs
- Salud API → BD: http://localhost:8080/api/health

## Verificar la comunicación entre contenedores

```bash
# api → db (misma red backend-net): funciona
docker compose exec api python -c "import socket; print(socket.create_connection(('db', 5432), 3))"

# web → api (misma red frontend-net): funciona
docker compose exec web wget -qO- http://api:8000/api/health

# web → db (redes distintas): falla con "bad address 'db'"
docker compose exec web ping -c 2 db

# Inspeccionar las redes
docker network inspect taskflow-frontend-net taskflow-backend-net
```

## Pruebas

```bash
docker compose exec api python -m pytest -v
```

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register` | Registrar usuario |
| POST | `/api/auth/login` | Iniciar sesión (devuelve JWT) |
| GET | `/api/auth/me` | Usuario actual |
| GET/POST | `/api/projects` | Listar / crear proyectos |
| GET/PATCH/DELETE | `/api/projects/{id}` | Ver / editar / eliminar proyecto |
| GET/POST | `/api/projects/{id}/members` | Miembros del proyecto |
| GET | `/api/projects/{id}/stats` | Avance, tareas por estado y vencidas |
| GET/POST | `/api/projects/{id}/tasks` | Tareas (filtros: `status_filter`, `priority`, `assignee_id`) |
| GET/PATCH/DELETE | `/api/tasks/{id}` | Ver / mover / eliminar tarea |
| GET/POST | `/api/tasks/{id}/comments` | Comentarios |
| GET | `/api/health` | Estado de la API y de la conexión a la BD |

## Comandos útiles

```bash
docker compose logs -f api        # ver logs de la API
docker compose down               # detener (los datos se conservan en el volumen)
docker compose down -v            # detener y BORRAR los datos
```
