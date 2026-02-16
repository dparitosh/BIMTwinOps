"""
Scheduling API — REST endpoints for 4D BIM schedule management.

Mounted at /api/schedules
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .store import ScheduleTask, ScheduleProject, get_schedule_store

router = APIRouter(prefix="/api/schedules", tags=["Scheduling"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    name: str
    start: str
    end: str
    progress: int = 0
    status: str = "not-started"
    db_ids: List[int] = Field(default_factory=list)
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class UpdateTaskRequest(BaseModel):
    name: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    progress: Optional[int] = None
    status: Optional[str] = None
    db_ids: Optional[List[int]] = None
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    dependencies: Optional[List[str]] = None


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


class ReorderRequest(BaseModel):
    task_ids: List[str]


# ---------------------------------------------------------------------------
# Project endpoints
# ---------------------------------------------------------------------------

@router.get("/projects", response_model=List[ScheduleProject])
def list_projects():
    """List all schedule projects."""
    return get_schedule_store().list_projects()


@router.get("/projects/{project_id}", response_model=ScheduleProject)
def get_project(project_id: str):
    """Get a single project with its tasks."""
    proj = get_schedule_store().get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.post("/projects", response_model=ScheduleProject, status_code=201)
def create_project(body: CreateProjectRequest):
    """Create a new schedule project."""
    return get_schedule_store().create_project(name=body.name, description=body.description)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    """Delete a schedule project and all its tasks."""
    ok = get_schedule_store().delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/tasks", response_model=List[ScheduleTask])
def list_tasks(project_id: str):
    """List all tasks in a project."""
    store = get_schedule_store()
    proj = store.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj.tasks


@router.get("/projects/{project_id}/tasks/{task_id}", response_model=ScheduleTask)
def get_task(project_id: str, task_id: str):
    """Get a single task."""
    task = get_schedule_store().get_task(project_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/projects/{project_id}/tasks", response_model=ScheduleTask, status_code=201)
def create_task(project_id: str, body: CreateTaskRequest):
    """Create a new task in a project."""
    task = ScheduleTask(**body.model_dump())
    return get_schedule_store().create_task(project_id, task)


@router.patch("/projects/{project_id}/tasks/{task_id}", response_model=ScheduleTask)
def update_task(project_id: str, task_id: str, body: UpdateTaskRequest):
    """Update an existing task (partial update)."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    task = get_schedule_store().update_task(project_id, task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task(project_id: str, task_id: str):
    """Delete a task."""
    ok = get_schedule_store().delete_task(project_id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@router.post("/projects/{project_id}/tasks/reorder", response_model=List[ScheduleTask])
def reorder_tasks(project_id: str, body: ReorderRequest):
    """Reorder tasks by providing the full list of task IDs in desired order."""
    return get_schedule_store().reorder_tasks(project_id, body.task_ids)


# ---------------------------------------------------------------------------
# Convenience: default project shorthand
# ---------------------------------------------------------------------------

@router.get("/tasks", response_model=List[ScheduleTask])
def list_default_tasks():
    """Shorthand: list tasks in the default project."""
    return get_schedule_store().list_tasks("default")


@router.post("/tasks", response_model=ScheduleTask, status_code=201)
def create_default_task(body: CreateTaskRequest):
    """Shorthand: create a task in the default project."""
    task = ScheduleTask(**body.model_dump())
    return get_schedule_store().create_task("default", task)


@router.patch("/tasks/{task_id}", response_model=ScheduleTask)
def update_default_task(task_id: str, body: UpdateTaskRequest):
    """Shorthand: update a task in the default project."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    task = get_schedule_store().update_task("default", task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}")
def delete_default_task(task_id: str):
    """Shorthand: delete a task in the default project."""
    ok = get_schedule_store().delete_task("default", task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}
