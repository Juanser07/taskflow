"""Datos de ejemplo para la demo (solo se cargan si la base está vacía)."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Comment, Priority, Project, ProjectMember, Role, Task, TaskStatus, User
from .security import hash_password

DEMO_PASSWORD = "taskflow123"


def seed(db: Session) -> bool:
    if db.scalar(select(User).limit(1)) is not None:
        return False

    ana = User(email="ana@taskflow.dev", full_name="Ana Gómez", password_hash=hash_password(DEMO_PASSWORD))
    luis = User(email="luis@taskflow.dev", full_name="Luis Pérez", password_hash=hash_password(DEMO_PASSWORD))
    db.add_all([ana, luis])
    db.flush()

    project = Project(
        name="Proyecto Integración Continua",
        description="Plan de trabajo del módulo: Docker, Jenkins, Travis CI y Codeship.",
        owner_id=ana.id,
    )
    project.members = [
        ProjectMember(user_id=ana.id, role=Role.owner),
        ProjectMember(user_id=luis.id, role=Role.member),
    ]
    db.add(project)
    db.flush()

    today = date.today()
    tasks = [
        ("Crear repositorio en GitHub", TaskStatus.done, Priority.high, today - timedelta(days=14), ana),
        ("Dockerizar API y base de datos", TaskStatus.done, Priority.high, today - timedelta(days=2), luis),
        ("Documento Entrega 1", TaskStatus.in_progress, Priority.high, today + timedelta(days=3), ana),
        ("Escribir pruebas unitarias", TaskStatus.in_progress, Priority.medium, today + timedelta(days=5), luis),
        ("Instalar y configurar Jenkins", TaskStatus.todo, Priority.medium, today + timedelta(days=14), luis),
        ("Configurar Travis CI", TaskStatus.todo, Priority.low, today + timedelta(days=28), None),
        ("Revisar alternativa a Codeship", TaskStatus.todo, Priority.low, today - timedelta(days=1), ana),
    ]
    for title, status, priority, due, assignee in tasks:
        db.add(
            Task(
                project_id=project.id,
                title=title,
                status=status,
                priority=priority,
                due_date=due,
                assignee_id=assignee.id if assignee else None,
                created_by_id=ana.id,
            )
        )
    db.flush()

    first = db.scalar(select(Task).where(Task.title == "Dockerizar API y base de datos"))
    db.add(Comment(task_id=first.id, author_id=luis.id, content="Listo: api y db se comunican por backend-net."))
    db.add(Comment(task_id=first.id, author_id=ana.id, content="¡Excelente! Agrego las capturas al documento."))
    db.commit()
    return True
