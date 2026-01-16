from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PendingActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class PendingAction(BaseModel):
    """A queued action plan awaiting (or having completed) human approval."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    status: PendingActionStatus = PendingActionStatus.PENDING

    # Core payload
    action_plan: Dict[str, Any] = Field(default_factory=dict)

    # Optional attribution / correlation
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    thread_id: Optional[str] = None

    # Review metadata
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Execution metadata
    executed_at: Optional[datetime] = None
    execution_result: Optional[Any] = None
    execution_error: Optional[str] = None


class PendingActionStore:
    """Thread-safe store for pending actions.

    Note: This is a development-friendly implementation.
    For production, replace with Redis/DB.
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self._items: Dict[str, PendingAction] = {}
        self._path = persistence_path
        if self._path:
            self._load_from_disk()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _load_from_disk(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            if not raw.strip():
                return
            data = json.loads(raw)
            if isinstance(data, list):
                items = [PendingAction.model_validate(x) for x in data]
            elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                items = [PendingAction.model_validate(x) for x in data["items"]]
            else:
                return
            self._items = {i.id: i for i in items}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Fail-open: don't block API startup on persistence issues
            self._items = {}

    def _save_to_disk(self) -> None:
        if not self._path:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = [i.model_dump(mode="json") for i in self._items.values()]
            self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            # Fail-open
            return

    def create(
        self,
        action_plan: Dict[str, Any],
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> PendingAction:
        with self._lock:
            item = PendingAction(
                action_plan=action_plan,
                user_id=user_id,
                session_id=session_id,
                thread_id=thread_id,
            )
            self._items[item.id] = item
            self._save_to_disk()
            return item

    def list(self, status: Optional[PendingActionStatus] = None) -> List[PendingAction]:
        with self._lock:
            items = list(self._items.values())
            if status:
                items = [i for i in items if i.status == status]
            # newest first
            items.sort(key=lambda x: x.created_at, reverse=True)
            return items

    def get(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            return self._items.get(action_id)

    def approve(self, action_id: str, *, approved_by: Optional[str] = None) -> PendingAction:
        with self._lock:
            item = self._require(action_id)
            if item.status not in (PendingActionStatus.PENDING, PendingActionStatus.APPROVED):
                raise ValueError(f"Cannot approve action in status {item.status}")
            item.status = PendingActionStatus.APPROVED
            item.approved_by = approved_by
            item.approved_at = self._now()
            item.updated_at = self._now()
            self._save_to_disk()
            return item

    def reject(
        self,
        action_id: str,
        *,
        rejected_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> PendingAction:
        with self._lock:
            item = self._require(action_id)
            if item.status not in (PendingActionStatus.PENDING, PendingActionStatus.REJECTED):
                raise ValueError(f"Cannot reject action in status {item.status}")
            item.status = PendingActionStatus.REJECTED
            item.rejected_by = rejected_by
            item.rejected_at = self._now()
            item.rejection_reason = reason
            item.updated_at = self._now()
            self._save_to_disk()
            return item

    def mark_executed(self, action_id: str, *, result: Any) -> PendingAction:
        with self._lock:
            item = self._require(action_id)
            item.status = PendingActionStatus.EXECUTED
            item.executed_at = self._now()
            item.execution_result = result
            item.execution_error = None
            item.updated_at = self._now()
            self._save_to_disk()
            return item

    def mark_failed(self, action_id: str, *, error: str) -> PendingAction:
        with self._lock:
            item = self._require(action_id)
            item.status = PendingActionStatus.FAILED
            item.executed_at = self._now()
            item.execution_error = error
            item.updated_at = self._now()
            self._save_to_disk()
            return item

    def _require(self, action_id: str) -> PendingAction:
        item = self._items.get(action_id)
        if not item:
            raise KeyError(f"Pending action not found: {action_id}")
        return item


def get_pending_action_store() -> PendingActionStore:
    """Global singleton store used by the API and agents."""

    # Function attribute singleton to avoid module-level globals.
    instance: Optional[PendingActionStore] = getattr(get_pending_action_store, "_instance", None)
    if instance is None:
        base_dir = Path(__file__).resolve().parent
        persistence = base_dir / "pending_actions.json"
        instance = PendingActionStore(persistence_path=persistence)
        setattr(get_pending_action_store, "_instance", instance)
    return instance
