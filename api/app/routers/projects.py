"""Proyectos, miembros y estadísticas."""
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_membership, require_owner
from ..models import Priority, Project, ProjectMember, Role, Task, TaskStatus, User
from ..schemas import (
    MemberAdd,
    MemberOut,
    ProjectCreate,
    ProjectOut,
    ProjectStats,
    ProjectUpdate,
)

router = APIRouter(prefix="/api/projects", tags=["Proyectos"])


def _project_out(project: Project, role: Role) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    out.my_role = role
    return out


@router.get("", response_model=List[ProjectOut])
def list_my_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.created_at)
    ).all()
    return [_project_out(project, role) for project, role in rows]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    project = Project(name=data.name, description=data.description, owner_id=user.id)
    project.members.append(ProjectMember(user_id=user.id, role=Role.owner))
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_out(project, Role.owner)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project, membership = get_membership(db, project_id, user)
    return _project_out(project, membership.role)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project, membership = get_membership(db, project_id, user)
    require_owner(membership)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _project_out(project, membership.role)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project, membership = get_membership(db, project_id, user)
    require_owner(membership)
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Miembros ----------
@router.get("/{project_id}/members", response_model=List[MemberOut])
def list_members(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project, _ = get_membership(db, project_id, user)
    return [MemberOut(user=m.user, role=m.role, joined_at=m.joined_at) for m in project.members]


@router.post("/{project_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: int,
    data: MemberAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project, membership = get_membership(db, project_id, user)
    require_owner(membership)
    new_user = db.scalar(select(User).where(User.email == data.email.lower()))
    if new_user is None:
        raise HTTPException(status_code=404, detail="No existe un usuario con ese correo")
    if db.get(ProjectMember, {"project_id": project.id, "user_id": new_user.id}):
        raise HTTPException(status_code=409, detail="El usuario ya es miembro del proyecto")
    member = ProjectMember(project_id=project.id, user_id=new_user.id, role=data.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberOut(user=member.user, role=member.role, joined_at=member.joined_at)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project, membership = get_membership(db, project_id, user)
    require_owner(membership)
    if user_id == project.owner_id:
        raise HTTPException(status_code=400, detail="No se puede quitar al dueño del proyecto")
    member = db.get(ProjectMember, {"project_id": project.id, "user_id": user_id})
    if member is None:
        raise HTTPException(status_code=404, detail="El usuario no es miembro del proyecto")
    # Las tareas que tenía asignadas quedan sin responsable
    for task in project.tasks:
        if task.assignee_id == user_id:
            task.assignee_id = None
    db.delete(member)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Estadísticas ----------
@router.get("/{project_id}/stats", response_model=ProjectStats)
def project_stats(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project, _ = get_membership(db, project_id, user)
    tasks = db.scalars(select(Task).where(Task.project_id == project.id)).all()
    today = date.today()

    by_status = {s.value: 0 for s in TaskStatus}
    by_priority = {p.value: 0 for p in Priority}
    overdue = 0
    for task in tasks:
        by_status[task.status.value] += 1
        by_priority[task.priority.value] += 1
        if task.due_date and task.due_date < today and task.status != TaskStatus.done:
            overdue += 1

    total = len(tasks)
    progress = round(by_status["done"] * 100 / total, 1) if total else 0.0
    return ProjectStats(
        project_id=project.id,
        total=total,
        by_status=by_status,
        by_priority=by_priority,
        overdue=overdue,
        progress_pct=progress,
    )
