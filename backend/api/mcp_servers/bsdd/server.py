"""
MCP Server: bSDD (buildingSMART Data Dictionary)
Provides bSDD API access as MCP tools for AI agents.

This server wraps the existing BSDDClient to provide standardized
tool interfaces for:
- Searching dictionaries
- Retrieving dictionary details
- Fetching classes and their properties
- Property lookups

Includes rate limiting to comply with bSDD API usage policies.

Tools:
1. search_dictionaries - Search for bSDD dictionaries
2. get_dictionary - Get full dictionary details
3. get_classes - Retrieve classes from a dictionary
4. get_properties - Fetch properties for a class

References:
- bSDD API: https://api.bsdd.buildingsmart.org/
- bSDD GraphQL: https://api.bsdd.buildingsmart.org/graphql
- bSDD Documentation: https://github.com/buildingSMART/bSDD
"""

from typing import Any, Dict, List, Optional
import logging
import json
from datetime import datetime, timedelta
from collections import deque

# MCP imports
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Import existing bSDD client
from ...bsdd_client import BSDDClient, BSDDEnvironment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple rate limiter to respect bSDD API usage limits
    
    Implements token bucket algorithm:
    - Max 60 requests per minute (production limit)
    - Requests consume tokens
    - Tokens refill over time
    """
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def allow_request(self) -> bool:
        """
        Check if a request is allowed under rate limit
        
        Returns:
            True if request allowed, False if rate limited
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.time_window)
        
        # Remove old requests outside time window
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def get_wait_time(self) -> float:
        """
        Get wait time in seconds before next request allowed
        
        Returns:
            Wait time in seconds, or 0 if request allowed now
        """
        if not self.requests:
            return 0.0
        
        now = datetime.now()
        oldest = self.requests[0]
        wait_until = oldest + timedelta(seconds=self.time_window)
        
        if now >= wait_until:
            return 0.0
        
        return (wait_until - now).total_seconds()


class BSDDMCPServer:
    """
    MCP Server for bSDD API operations
    
    Wraps the existing BSDDClient to provide standardized MCP tools
    with rate limiting and error handling.
    """
    
    def __init__(
        self,
        environment: str = "production",
        auth_token: Optional[str] = None,
        rate_limit: int = 60
    ):
        """
        Initialize bSDD MCP Server
        
        Args:
            environment: 'production' or 'test'
            auth_token: Optional OAuth2 token
            rate_limit: Maximum requests per minute
        """
        env = (BSDDEnvironment.PRODUCTION if environment == "production" 
               else BSDDEnvironment.TEST)
        
        self.client = BSDDClient(environment=env, auth_token=auth_token)
        self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=60)
        self.server = Server("bsdd-mcp-server")
        
        # Register tool handlers
        self._register_tools()
    
    def _check_rate_limit(self) -> Dict[str, Any]:
        """
        Check rate limit before making request
        
        Returns:
            Error dict if rate limited, None if allowed
        """
        if not self.rate_limiter.allow_request():
            wait_time = self.rate_limiter.get_wait_time()
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "wait_seconds": round(wait_time, 2),
                "message": f"Please wait {wait_time:.1f} seconds before next request"
            }
        return None
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available bSDD tools"""
            return [
                Tool(
                    name="search_dictionaries",
                    description=(
                        "Search for bSDD dictionaries by name, organization, or language. "
                        "Returns list of available dictionaries with metadata. "
                        "Use this to discover which standardized building dictionaries are available."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_text": {
                                "type": "string",
                                "description": "Search text (matches name, organization, or code)",
                                "default": ""
                            },
                            "language_code": {
                                "type": "string",
                                "description": "Filter by language code (e.g., 'en-GB', 'nl-NL')",
                                "default": None
                            },
                            "status": {
                                "type": "string",
                                "enum": ["Active", "Inactive", "Preview", "all"],
                                "description": "Filter by dictionary status",
                                "default": "Active"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results to return",
                                "default": 20
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_dictionary",
                    description=(
                        "Retrieve complete details for a specific bSDD dictionary by URI. "
                        "Returns dictionary metadata, class count, property count, and relationships. "
                        "Use this after finding a dictionary to get its full specification."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "description": "URI of the dictionary to retrieve"
                            },
                            "include_classes": {
                                "type": "boolean",
                                "description": "Include list of classes in response",
                                "default": False
                            },
                            "language_code": {
                                "type": "string",
                                "description": "Preferred language for descriptions",
                                "default": "en-GB"
                            }
                        },
                        "required": ["uri"]
                    }
                ),
                Tool(
                    name="get_classes",
                    description=(
                        "Retrieve classes (classifications) from a bSDD dictionary. "
                        "Returns class definitions with properties, IFC mappings, and relationships. "
                        "Use this to explore building component classifications."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dictionary_uri": {
                                "type": "string",
                                "description": "URI of the dictionary containing the classes"
                            },
                            "search_text": {
                                "type": "string",
                                "description": "Optional search filter for class names",
                                "default": ""
                            },
                            "related_ifc_entity": {
                                "type": "string",
                                "description": "Filter by IFC entity (e.g., 'IfcWall', 'IfcDoor')",
                                "default": None
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum classes to return",
                                "default": 50
                            },
                            "include_properties": {
                                "type": "boolean",
                                "description": "Include class properties in response",
                                "default": True
                            }
                        },
                        "required": ["dictionary_uri"]
                    }
                ),
                Tool(
                    name="get_properties",
                    description=(
                        "Retrieve properties for a specific bSDD class. "
                        "Returns property definitions with data types, units, and allowed values. "
                        "Use this to understand standardized property specifications."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dictionary_uri": {
                                "type": "string",
                                "description": "URI of the dictionary containing the class"
                            },
                            "class_uri": {
                                "type": "string",
                                "description": "URI of the class to get properties for"
                            },
                            "language_code": {
                                "type": "string",
                                "description": "Preferred language for property descriptions",
                                "default": "en-GB"
                            },
                            "include_allowed_values": {
                                "type": "boolean",
                                "description": "Include allowed/enumerated values for properties",
                                "default": True
                            }
                        },
                        "required": ["dictionary_uri", "class_uri"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool invocations"""
            
            # Check rate limit
            rate_limit_error = self._check_rate_limit()
            if rate_limit_error:
                return [TextContent(
                    type="text",
                    text=json.dumps(rate_limit_error, indent=2)
                )]
            
            try:
                if name == "search_dictionaries":
                    result = await self._search_dictionaries(**arguments)
                elif name == "get_dictionary":
                    result = await self._get_dictionary(**arguments)
                elif name == "get_classes":
                    result = await self._get_classes(**arguments)
                elif name == "get_properties":
                    result = await self._get_properties(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Error executing {name}: {str(e)}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    async def _search_dictionaries(
        self,
        search_text: str = "",
        language_code: Optional[str] = None,
        status: str = "Active",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for bSDD dictionaries"""
        
        try:
            dictionaries = self.client.get_dictionaries()

            # Basic substring filtering (client fetches full list)
            search_norm = (search_text or "").strip().lower()
            if search_norm:
                dictionaries = [
                    d
                    for d in dictionaries
                    if search_norm in (d.name or "").lower()
                    or search_norm in (d.organization_code or "").lower()
                    or search_norm in (d.uri or "").lower()
                ]

            # Filter by language if requested
            if language_code:
                dictionaries = [d for d in dictionaries if d.language_code == language_code]
            
            # Filter by status
            if status != "all":
                dictionaries = [d for d in dictionaries if d.status == status]
            
            # Limit results
            dictionaries = dictionaries[:limit]
            
            # Convert to JSON-serializable format
            results = [
                {
                    "uri": d.uri,
                    "name": d.name,
                    "version": d.version,
                    "organization": d.organization_code,
                    "status": d.status,
                    "language": d.language_code,
                    "license": d.license,
                    "release_date": d.release_date,
                    "more_info": d.more_info_url
                }
                for d in dictionaries
            ]
            
            return {
                "success": True,
                "count": len(results),
                "dictionaries": results,
                "filters": {
                    "search_text": search_text,
                    "language_code": language_code,
                    "status": status
                }
            }
            
        except Exception as e:
            logger.error(f"Dictionary search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "dictionaries": []
            }
    
    async def _get_dictionary(
        self,
        uri: str,
        include_classes: bool = False,
        language_code: str = "en-GB"
    ) -> Dict[str, Any]:
        """Get dictionary details"""
        
        try:
            dictionaries = self.client.get_dictionaries()
            dictionary = next((d for d in dictionaries if d.uri == uri), None)
            if dictionary is None:
                raise ValueError(f"Dictionary not found: {uri}")
            
            result = {
                "success": True,
                "uri": dictionary.uri,
                "name": dictionary.name,
                "version": dictionary.version,
                "organization": dictionary.organization_code,
                "status": dictionary.status,
                "language": dictionary.language_code,
                "license": dictionary.license,
                "release_date": dictionary.release_date,
                "more_info": dictionary.more_info_url
            }
            
            if include_classes:
                # Get class list (sample only to avoid large responses)
                classes = self.client.search_classes(
                    dictionary_uri=uri,
                    search_text=None,
                    related_ifc_entity=None,
                    language_code=language_code,
                )
                result["class_count"] = len(classes)
                result["sample_classes"] = [
                    {"uri": c.uri, "code": c.code, "name": c.name}
                    for c in classes[:10]
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Get dictionary failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_classes(
        self,
        dictionary_uri: str,
        search_text: str = "",
        related_ifc_entity: Optional[str] = None,
        limit: int = 50,
        include_properties: bool = True
    ) -> Dict[str, Any]:
        """Get classes from dictionary"""
        
        try:
            classes = self.client.search_classes(
                dictionary_uri=dictionary_uri,
                search_text=(search_text or None),
                related_ifc_entity=related_ifc_entity,
                language_code="en-GB",
            )

            # Limit results
            classes = classes[:limit]
            
            # Filter by IFC entity if specified
            if related_ifc_entity:
                classes = [
                    c for c in classes 
                    if related_ifc_entity in (c.related_ifc_entities or [])
                ]
            
            # Optionally fetch detailed property payloads for a small subset to
            # avoid large/slow responses.
            detail_uris = set()
            if include_properties:
                detail_uris = {c.uri for c in classes[: min(len(classes), 10)]}

            results = []
            for cls in classes:
                if include_properties and cls.uri in detail_uris:
                    cls = self.client.get_class_details(
                        dictionary_uri=dictionary_uri,
                        class_uri=cls.uri,
                        include_properties=True,
                        include_relations=False,
                        include_children=False,
                    )
                class_data = {
                    "uri": cls.uri,
                    "code": cls.code,
                    "name": cls.name,
                    "definition": cls.definition,
                    "class_type": cls.class_type,
                    "related_ifc_entities": cls.related_ifc_entities,
                    "synonyms": cls.synonyms,
                    "parent_class": cls.parent_class_uri
                }
                
                if include_properties and cls.properties:
                    class_data["properties"] = cls.properties[:20]  # Limit properties
                    class_data["property_count"] = len(cls.properties)
                
                results.append(class_data)
            
            return {
                "success": True,
                "count": len(results),
                "classes": results,
                "filters": {
                    "dictionary_uri": dictionary_uri,
                    "search_text": search_text,
                    "related_ifc_entity": related_ifc_entity
                }
            }
            
        except Exception as e:
            logger.error(f"Get classes failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "classes": []
            }
    
    async def _get_properties(
        self,
        dictionary_uri: str,
        class_uri: str,
        language_code: str = "en-GB",
        include_allowed_values: bool = True
    ) -> Dict[str, Any]:
        """Get properties for a class"""
        
        try:
            # Get class with properties
            cls = self.client.get_class_details(
                dictionary_uri=dictionary_uri,
                class_uri=class_uri,
                include_properties=True,
                include_relations=False,
                include_children=False,
            )
            
            properties = []
            for prop_dict in (cls.properties or []):
                prop_data = {
                    "uri": prop_dict.get("uri"),
                    "code": prop_dict.get("code"),
                    "name": prop_dict.get("name"),
                    "definition": prop_dict.get("definition"),
                    "data_type": prop_dict.get("dataType"),
                    "units": prop_dict.get("units", []),
                    "physical_quantity": prop_dict.get("physicalQuantity")
                }
                
                if include_allowed_values and "allowedValues" in prop_dict:
                    prop_data["allowed_values"] = prop_dict["allowedValues"]
                
                properties.append(prop_data)
            
            return {
                "success": True,
                "class_uri": class_uri,
                "class_name": cls.name,
                "property_count": len(properties),
                "properties": properties
            }
            
        except Exception as e:
            logger.error(f"Get properties failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "properties": []
            }


async def main():
    """Run the bSDD MCP server"""
    import os
    
    # Get configuration from environment
    environment = os.getenv("BSDD_ENVIRONMENT", "production")
    auth_token = os.getenv("BSDD_AUTH_TOKEN", None)
    rate_limit = int(os.getenv("BSDD_RATE_LIMIT", "60"))
    
    # Create and run server
    server_instance = BSDDMCPServer(
        environment=environment,
        auth_token=auth_token,
        rate_limit=rate_limit
    )
    
    # Run stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            server_instance.server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
