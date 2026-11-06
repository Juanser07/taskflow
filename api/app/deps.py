"""Dependencias compartidas: usuario autenticado y control de acceso a proyectos."""
from typing import Tuple

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Project, ProjectMember, Role, Task, User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def get_membership(db: Session, project_id: int, user: User) -> Tuple[Project, ProjectMember]:
    """Devuelve el proyecto si el usuario es miembro. Si no, 404 (no revela que existe)."""
    membership = db.get(ProjectMember, {"project_id": project_id, "user_id": user.id})
    if membership is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return membership.project, membership


def require_owner(membership: ProjectMember) -> None:
    if membership.role != Role.owner:
        raise HTTPException(status_code=403, detail="Solo el dueño del proyecto puede hacer esto")


def get_task_for_member(db: Session, task_id: int, user: User) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    get_membership(db, task.project_id, user)  # 404 si no pertenece al proyecto
    return task
