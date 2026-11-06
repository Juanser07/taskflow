"""Esquemas Pydantic: validan lo que entra y definen lo que sale de la API."""
from datetime import date, datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Priority, Role, TaskStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Usuarios y autenticación ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=6, max_length=72)


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Proyectos ----------
class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = None


class ProjectOut(ORMModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    my_role: Optional[Role] = None


class MemberAdd(BaseModel):
    email: EmailStr
    role: Role = Role.member


class MemberOut(BaseModel):
    user: UserOut
    role: Role
    joined_at: datetime


class ProjectStats(BaseModel):
    project_id: int
    total: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    overdue: int
    progress_pct: float


# ---------- Tareas ----------
class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: Priority = Priority.medium
    due_date: Optional[date] = None
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    due_date: Optional[date] = None
    assignee_id: Optional[int] = None


class TaskOut(ORMModel):
    id: int
    project_id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: Priority
    due_date: Optional[date]
    assignee: Optional[UserOut]
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0


# ---------- Comentarios ----------
class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentOut(ORMModel):
    id: int
    task_id: int
    author: UserOut
    content: str
    created_at: datetime
