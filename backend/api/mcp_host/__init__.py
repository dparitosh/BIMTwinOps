"""
MCP Server Infrastructure Package

This package contains MCP (Model Context Protocol) server implementations
for various backend services.

MCP Servers:
- neo4j: Graph database operations
- basex: Document storage and versioning
- bsdd: buildingSMART Data Dictionary integration
- opensearch: Hybrid semantic search

Each server exposes tools that can be called by AI agents through the MCP Host.
"""

__version__ = "0.1.0"
