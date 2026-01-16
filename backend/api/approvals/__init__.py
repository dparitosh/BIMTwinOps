"""Human-in-the-loop approvals.

This package provides a minimal approval queue for actions that require human
confirmation before execution.

Current implementation is an in-memory store with optional JSON persistence.
"""

from .store import PendingAction, PendingActionStatus, get_pending_action_store
