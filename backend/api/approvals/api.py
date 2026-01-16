from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .store import PendingAction, PendingActionStatus, get_pending_action_store

if TYPE_CHECKING:  # pragma: no cover
    from ..agents.executor_agent import ExecutorAgent
    from ..security.security_layer import AuditLogger


_audit: Optional["AuditLogger"] = None
_executor: Optional["ExecutorAgent"] = None

# Optional audit logging
try:
    from ..security.security_layer import AuditLogger

    _audit = AuditLogger()
except ImportError:  # pragma: no cover
    _audit = None

# Executor
try:
    from ..agents.executor_agent import ExecutorAgent

    _executor = ExecutorAgent()
except ImportError:  # pragma: no cover
    _executor = None


router = APIRouter(prefix="/api/approvals", tags=["Approvals"])


class ApproveRequest(BaseModel):
    execute: bool = Field(default=True, description="If true, execute immediately after approval")
    approved_by: Optional[str] = None


class RejectRequest(BaseModel):
    rejected_by: Optional[str] = None
    reason: Optional[str] = None


@router.get("/pending", response_model=list[PendingAction])
def list_pending(status: Optional[PendingActionStatus] = None):
    store = get_pending_action_store()
    return store.list(status=status)


@router.get("/{action_id}", response_model=PendingAction)
def get_one(action_id: str):
    store = get_pending_action_store()
    item = store.get(action_id)
    if not item:
        raise HTTPException(status_code=404, detail="Pending action not found")
    return item


@router.post("/{action_id}/approve")
async def approve(action_id: str, body: ApproveRequest):
    store = get_pending_action_store()

    try:
        item = store.approve(action_id, approved_by=body.approved_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pending action not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if _audit:
        _audit.log_agent_action(
            agent_name="hitl",
            action="pending_action_approved",
            intent="approval",
            result="success",
            user_id=item.user_id,
            session_id=item.session_id,
        )

    if not body.execute:
        return {"status": "approved", "action": item}

    if _executor is None:
        raise HTTPException(status_code=503, detail="Executor not available")

    try:
        result = await _executor.execute(item.action_plan, metadata={
            "user_id": item.user_id,
            "session_id": item.session_id,
            "thread_id": item.thread_id,
        })
        item2 = store.mark_executed(action_id, result=result)

        if _audit:
            _audit.log_agent_action(
                agent_name="executor",
                action="execute_approved_action",
                intent="execution",
                result="success",
                user_id=item.user_id,
                session_id=item.session_id,
            )

        return {"status": "executed", "action": item2}

    except Exception as exc:  # noqa: BLE001
        item2 = store.mark_failed(action_id, error=str(exc))
        if _audit:
            _audit.log_agent_action(
                agent_name="executor",
                action="execute_approved_action",
                intent="execution",
                result="error",
                user_id=item.user_id,
                session_id=item.session_id,
            )
        raise HTTPException(
            status_code=500,
            detail={"error": str(exc), "action": item2.model_dump(mode="json")},
        ) from exc


@router.post("/{action_id}/reject")
def reject(action_id: str, body: RejectRequest):
    store = get_pending_action_store()

    try:
        item = store.reject(action_id, rejected_by=body.rejected_by, reason=body.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pending action not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if _audit:
        _audit.log_agent_action(
            agent_name="hitl",
            action="pending_action_rejected",
            intent="approval",
            result="success",
            user_id=item.user_id,
            session_id=item.session_id,
        )

    return {"status": "rejected", "action": item}
