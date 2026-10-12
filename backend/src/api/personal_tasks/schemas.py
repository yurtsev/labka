from datetime import date, datetime, time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints


class TaskRequest(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    due_date: date
    due_time: time | None = None


class TaskDoneRequest(BaseModel):
    is_done: bool


class TaskResponse(BaseModel):
    id: UUID
    title: str
    due_date: date
    due_time: time | None
    is_done: bool
    created_at: datetime


class TasksResponse(BaseModel):
    items: list[TaskResponse]
