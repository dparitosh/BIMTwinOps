"""
Scheduling Store — JSON-file-backed CRUD for 4D BIM schedule tasks.

Thread-safe, persisted to disk.  Swap for a database in production.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ScheduleTask(BaseModel):
    """A single schedule (4D) task."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str = Field(default="default")
    name: str
    start: str  # ISO date string e.g. "2026-01-15"
    end: str
    progress: int = Field(default=0, ge=0, le=100)
    status: str = Field(default="not-started")  # completed | in-progress | not-started | delayed
    db_ids: List[int] = Field(default_factory=list)
    category: Optional[str] = None  # Foundation, Structural, MEP, etc.
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)  # ids of predecessor tasks
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ScheduleProject(BaseModel):
    """Container for a set of schedule tasks (one project / one model)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = "Default Project"
    description: str = ""
    tasks: List[ScheduleTask] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

_DEFAULT_PERSISTENCE = Path(__file__).resolve().parent.parent.parent / "data" / "schedules.json"

# Seed data used when starting fresh
_SEED_TASKS: List[Dict[str, Any]] = [
    {"name": "Foundation", "start": "2026-01-01", "end": "2026-02-15", "progress": 100, "status": "completed",
     "db_ids": [1, 2, 3], "category": "Foundation"},
    {"name": "Structural Steel", "start": "2026-02-01", "end": "2026-04-30", "progress": 75, "status": "in-progress",
     "db_ids": [4, 5, 6, 7], "category": "Structural"},
    {"name": "MEP Rough-In", "start": "2026-03-15", "end": "2026-05-30", "progress": 50, "status": "in-progress",
     "db_ids": [8, 9, 10], "category": "MEP"},
    {"name": "Exterior Envelope", "start": "2026-04-01", "end": "2026-07-15", "progress": 25, "status": "in-progress",
     "db_ids": [11, 12, 13], "category": "Envelope"},
    {"name": "Interior Finishes", "start": "2026-06-01", "end": "2026-09-30", "progress": 0, "status": "not-started",
     "db_ids": [14, 15, 16], "category": "Finishes"},
    {"name": "Final MEP", "start": "2026-08-01", "end": "2026-10-15", "progress": 0, "status": "not-started",
     "db_ids": [17, 18], "category": "MEP"},
    {"name": "Commissioning", "start": "2026-10-01", "end": "2026-11-30", "progress": 0, "status": "not-started",
     "db_ids": [19, 20], "category": "Commissioning"},
]


class ScheduleStore:
    """Thread-safe JSON-file-backed schedule store."""

    def __init__(self, persistence_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self._path = persistence_path or _DEFAULT_PERSISTENCE
        self._projects: Dict[str, ScheduleProject] = {}
        self._load()

    # ---- persistence ----

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for pid, pdata in raw.items():
                    self._projects[pid] = ScheduleProject(**pdata)
            except Exception:
                self._projects = {}
        # If no projects exist → seed with defaults
        if not self._projects:
            self._seed()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {pid: p.model_dump() for pid, p in self._projects.items()}
        self._path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def _seed(self) -> None:
        proj = ScheduleProject(id="default", name="Default Project", description="Auto-seeded demo schedule")
        for td in _SEED_TASKS:
            proj.tasks.append(ScheduleTask(project_id="default", **td))
        self._projects["default"] = proj
        self._save()

    # ---- public API ----

    def list_projects(self) -> List[ScheduleProject]:
        with self._lock:
            return list(self._projects.values())

    def get_project(self, project_id: str) -> Optional[ScheduleProject]:
        with self._lock:
            return self._projects.get(project_id)

    def create_project(self, name: str, description: str = "") -> ScheduleProject:
        with self._lock:
            proj = ScheduleProject(name=name, description=description)
            self._projects[proj.id] = proj
            self._save()
            return proj

    def delete_project(self, project_id: str) -> bool:
        with self._lock:
            if project_id in self._projects:
                del self._projects[project_id]
                self._save()
                return True
            return False

    # ---- tasks ----

    def list_tasks(self, project_id: str = "default") -> List[ScheduleTask]:
        with self._lock:
            proj = self._projects.get(project_id)
            return list(proj.tasks) if proj else []

    def get_task(self, project_id: str, task_id: str) -> Optional[ScheduleTask]:
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj:
                return None
            for t in proj.tasks:
                if t.id == task_id:
                    return t
            return None

    def create_task(self, project_id: str, task: ScheduleTask) -> ScheduleTask:
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj:
                proj = ScheduleProject(id=project_id, name=project_id)
                self._projects[project_id] = proj
            task.project_id = project_id
            task.updated_at = datetime.now(timezone.utc).isoformat()
            proj.tasks.append(task)
            proj.updated_at = datetime.now(timezone.utc).isoformat()
            self._save()
            return task

    def update_task(self, project_id: str, task_id: str, updates: Dict[str, Any]) -> Optional[ScheduleTask]:
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj:
                return None
            for i, t in enumerate(proj.tasks):
                if t.id == task_id:
                    data = t.model_dump()
                    data.update(updates)
                    data["updated_at"] = datetime.now(timezone.utc).isoformat()
                    # Auto-derive status from progress if not explicitly set
                    if "progress" in updates and "status" not in updates:
                        prog = int(updates["progress"])
                        if prog >= 100:
                            data["status"] = "completed"
                        elif prog > 0:
                            data["status"] = "in-progress"
                        else:
                            data["status"] = "not-started"
                    proj.tasks[i] = ScheduleTask(**data)
                    proj.updated_at = datetime.now(timezone.utc).isoformat()
                    self._save()
                    return proj.tasks[i]
            return None

    def delete_task(self, project_id: str, task_id: str) -> bool:
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj:
                return False
            before = len(proj.tasks)
            proj.tasks = [t for t in proj.tasks if t.id != task_id]
            if len(proj.tasks) < before:
                proj.updated_at = datetime.now(timezone.utc).isoformat()
                self._save()
                return True
            return False

    def reorder_tasks(self, project_id: str, task_ids: List[str]) -> List[ScheduleTask]:
        """Reorder tasks by providing the full id list in desired order."""
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj:
                return []
            id_map = {t.id: t for t in proj.tasks}
            ordered = [id_map[tid] for tid in task_ids if tid in id_map]
            # append any tasks not in the list at the end
            remaining = [t for t in proj.tasks if t.id not in {tid for tid in task_ids}]
            proj.tasks = ordered + remaining
            proj.updated_at = datetime.now(timezone.utc).isoformat()
            self._save()
            return proj.tasks


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_store: Optional[ScheduleStore] = None
_store_lock = threading.Lock()


def get_schedule_store(path: Optional[Path] = None) -> ScheduleStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ScheduleStore(persistence_path=path)
    return _store
