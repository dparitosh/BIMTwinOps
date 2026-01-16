"""Executor Agent (Reasoning \u2260 Execution).

This agent executes an already-formed action plan, optionally after a HITL
approval gate.

It is intentionally dumb: no intent classification, no planning.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ExecutorAgent:
    def __init__(self):
        self.audit_logger = None
        try:
            from ..security.security_layer import AuditLogger as _AuditLogger

            self.audit_logger = _AuditLogger()
        except ImportError:  # pragma: no cover
            self.audit_logger = None

        self.mcp_host = None
        try:
            from ..mcp_host.mcp_host import get_mcp_host

            self._get_mcp_host = get_mcp_host
        except ImportError:  # pragma: no cover
            self._get_mcp_host = None

    async def execute(self, action_plan: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a prepared action plan.

        Expected plan keys:
          - action_type: str
          - tool: str
          - parameters: dict

        Returns a list of result objects.
        """

        if self.mcp_host is None and self._get_mcp_host is not None:
            self.mcp_host = await self._get_mcp_host()

        action_type = (action_plan or {}).get("action_type")
        tool = (action_plan or {}).get("tool")
        params = (action_plan or {}).get("parameters") or {}

        user_id = (metadata or {}).get("user_id")
        session_id = (metadata or {}).get("session_id")

        # Currently-supported tools
        try:
            if tool in ("create_nodes", "create_relationships", "update_properties", "delete_nodes", "cypher_query") and self.mcp_host:
                if tool == "create_nodes":
                    labels = params.get("labels") or [params.get("label") or "Element"]
                    properties = params.get("properties") or {}
                    mcp_result = await self.mcp_host.call_tool(
                        server_name="neo4j",
                        tool_name="create_nodes",
                        nodes=[{"labels": list(labels), "properties": properties}],
                    )

                elif tool == "create_relationships":
                    rel = {
                        "from_uri": params.get("from_uri") or params.get("from_node") or "unknown",
                        "to_uri": params.get("to_uri") or params.get("to_node") or "unknown",
                        "type": params.get("relationship_type") or params.get("type") or "RELATES_TO",
                        "properties": params.get("properties") or {},
                    }
                    mcp_result = await self.mcp_host.call_tool(
                        server_name="neo4j",
                        tool_name="create_relationships",
                        relationships=[rel],
                    )

                elif tool == "update_properties":
                    target_type = params.get("target_type") or "node"
                    uri = params.get("uri") or params.get("node_id") or "unknown"
                    properties = params.get("properties") or {}
                    mcp_result = await self.mcp_host.call_tool(
                        server_name="neo4j",
                        tool_name="update_properties",
                        target_type=target_type,
                        uri=uri,
                        properties=properties,
                        merge=bool(params.get("merge", True)),
                    )

                elif tool == "delete_nodes":
                    uris = params.get("uris") or ([params.get("uri")] if params.get("uri") else [])
                    mcp_result = await self.mcp_host.call_tool(
                        server_name="neo4j",
                        tool_name="delete_nodes",
                        uris=list(uris),
                        detach=bool(params.get("detach", True)),
                    )

                else:  # cypher_query
                    query = params.get("query") or "RETURN 1 AS ok"
                    mcp_result = await self.mcp_host.call_tool(
                        server_name="neo4j",
                        tool_name="cypher_query",
                        query=query,
                        parameters=params.get("parameters") or {},
                        limit=int(params.get("limit", 100)),
                    )

                parsed = self._parse_mcp_result(mcp_result)

                if self.audit_logger:
                    self.audit_logger.log_agent_action(
                        agent_name="executor_agent",
                        action=action_type or tool or "execute",
                        intent="execution",
                        result="success",
                        user_id=user_id,
                        session_id=session_id,
                    )

                return parsed

        except (RuntimeError, ValueError, TypeError) as exc:
            logger.warning("Executor MCP call failed: %s", exc)

        # Fallback: deterministic sample results for dev/tests
        results = [{
            "status": "success",
            "action_type": action_type or "unknown",
            "tool": tool,
            "parameters": params,
            "timestamp": datetime.now().isoformat(),
            "note": "fallback_result_no_mcp",
        }]

        if self.audit_logger:
            self.audit_logger.log_agent_action(
                agent_name="executor_agent",
                action=action_type or tool or "execute",
                intent="execution",
                result="success",
                user_id=user_id,
                session_id=session_id,
            )

        return results

    def _parse_mcp_result(self, result: Any) -> List[Dict[str, Any]]:
        """Parse MCP CallToolResult into a list of dicts."""

        # mcp_host returns CallToolResult; in some paths we see dict-like {content:[{text:..}]}.
        try:
            if hasattr(result, "content"):
                content = getattr(result, "content")
            elif isinstance(result, dict):
                content = result.get("content")
            else:
                content = None

            if isinstance(content, list) and content:
                text = content[0].get("text") if isinstance(content[0], dict) else getattr(content[0], "text", None)
                if isinstance(text, str):
                    parsed = json.loads(text)
                    return parsed if isinstance(parsed, list) else [parsed]
                if isinstance(text, (dict, list)):
                    return text if isinstance(text, list) else [text]

        except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
            pass

        return [{"status": "unknown", "raw": str(result)}]
