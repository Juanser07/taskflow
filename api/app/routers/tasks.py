"""Tareas de un proyecto (tablero Kanban) y sus comentarios."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_membership, get_task_for_member
from ..models import Comment, Priority, ProjectMember, Task, TaskStatus, User
from ..schemas import CommentCreate, CommentOut, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(tags=["Tareas"])


def _task_out(task: Task) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.comment_count = len(task.comments)
    return out


def _check_assignee(db: Session, project_id: int, assignee_id: Optional[int]) -> None:
    if assignee_id is None:
        return
    if db.get(ProjectMember, {"project_id": project_id, "user_id": assignee_id}) is None:
        raise HTTPException(status_code=400, detail="El responsable debe ser miembro del proyecto")


@router.get("/api/projects/{project_id}/tasks", response_model=List[TaskOut])
def list_tasks(
    project_id: int,
    status_filter: Optional[TaskStatus] = None,
    priority: Optional[Priority] = None,
    assignee_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista las tareas del proyecto. Filtros opcionales: `status_filter`, `priority`, `assignee_id`."""
    get_membership(db, project_id, user)
    query = select(Task).where(Task.project_id == project_id)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if priority:
        query = query.where(Task.priority == priority)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    tasks = db.scalars(query.order_by(Task.created_at)).all()
    return [_task_out(t) for t in tasks]


@router.post(
    "/api/projects/{project_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED
)
def create_task(
    project_id: int,
    data: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_membership(db, project_id, user)
    _check_assignee(db, project_id, data.assignee_id)
    task = Task(project_id=project_id, created_by_id=user.id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_out(task)


@router.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _task_out(get_task_for_member(db, task_id, user))


@router.patch("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    data: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = get_task_for_member(db, task_id, user)
    changes = data.model_dump(exclude_unset=True)
    if "assignee_id" in changes:
        _check_assignee(db, task.project_id, changes["assignee_id"])
    for field, value in changes.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return _task_out(task)


@router.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = get_task_for_member(db, task_id, user)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Comentarios ----------
@router.get("/api/tasks/{task_id}/comments", response_model=List[CommentOut], tags=["Comentarios"])
def list_comments(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_task_for_member(db, task_id, user).comments


@router.post(
    "/api/tasks/{task_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Comentarios"],
)
def add_comment(
    task_id: int,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = get_task_for_member(db, task_id, user)
    comment = Comment(task_id=task.id, author_id=user.id, content=data.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
