import tempfile
import unittest
from pathlib import Path
import sys

# Ensure `api.*` imports work when run via unittest discovery from repo root.
BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.approvals.store import PendingActionStatus, PendingActionStore
from api.agents.executor_agent import ExecutorAgent


class PendingActionStoreTests(unittest.TestCase):
    def test_create_and_transition(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pending.json"
            store = PendingActionStore(persistence_path=path)

            plan = {"action_type": "delete", "tool": "update_properties", "requires_confirmation": True, "parameters": {}}
            item1 = store.create(plan, user_id="u1", session_id="s1", thread_id="t1")
            self.assertEqual(item1.status, PendingActionStatus.PENDING)

            item1 = store.approve(item1.id, approved_by="admin")
            self.assertEqual(item1.status, PendingActionStatus.APPROVED)

            item2 = store.create(plan, user_id="u1", session_id="s1", thread_id="t1")
            item2 = store.reject(item2.id, rejected_by="admin", reason="no")
            self.assertEqual(item2.status, PendingActionStatus.REJECTED)

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pending.json"
            store1 = PendingActionStore(persistence_path=path)
            item = store1.create({"action_type": "update", "tool": "update_properties", "parameters": {}}, user_id="u")

            store2 = PendingActionStore(persistence_path=path)
            loaded = store2.get(item.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.id, item.id)


class ExecutorFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_executor_fallback_without_mcp(self):
        ex = ExecutorAgent()
        # Prevent test from initializing/spawning MCP servers.
        ex._get_mcp_host = None
        res = await ex.execute({"action_type": "update", "tool": "update_properties", "parameters": {"uri": "x", "properties": {"a": 1}}})
        self.assertTrue(isinstance(res, list) and len(res) >= 1)
        self.assertEqual(res[0].get("status"), "success")


if __name__ == "__main__":
    unittest.main()
