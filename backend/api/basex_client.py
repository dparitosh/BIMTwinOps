"""
BaseX Client Service
Provides interface for interacting with BaseX XML Database for bSDD document storage
"""
import logging
import os
from typing import Optional, Any, List, Dict, Union
from datetime import datetime

# Try different import patterns common for this library
try:
    from BaseXClient import BaseXClient
except ImportError:
    try:
        from basexclient import BaseXClient
    except ImportError:
        BaseXClient = None

logger = logging.getLogger(__name__)

class BaseXService:
    """
    Service for interacting with BaseX XML Database.
    Handles connection management, document storage, and querying.
    """
    
    def __init__(
        self, 
        host: Optional[str] = None, 
        port: Optional[int] = None, 
        username: Optional[str] = None, 
        password: Optional[str] = None,
        db_name: Optional[str] = None
    ):
        """
        Initialize BaseX Service
        
        Args:
            host: BaseX server host (from BASEX_HOST env var)
            port: BaseX server port (from BASEX_PORT env var)
            username: BaseX username (from BASEX_USER env var)
            password: BaseX password (from BASEX_PASSWORD env var)
            db_name: Default database name (from BASEX_DB_NAME env var)
        """
        from .config import cfg
        self.host = host or cfg.BASEX_HOST
        self.port = port or cfg.BASEX_PORT
        self.username = username or cfg.BASEX_USER
        self.password = password or cfg.BASEX_PASSWORD
        self.db_name = db_name or cfg.BASEX_DB_NAME
        self.session = None

    def connect(self):
        """Establish connection to BaseX server"""
        if BaseXClient is None:
            raise ImportError("BaseXClient library not installed. Please install 'BaseXClient'.")
            
        try:
            self.session = BaseXClient(self.host, self.port, self.username, self.password)
            logger.info(f"Connected to BaseX at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to BaseX: {e}")
            raise

    def close(self):
        """Close connection"""
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                logger.warning(f"Error closing BaseX session: {e}")
            finally:
                self.session = None

    def execute_command(self, command: str) -> str:
        """
        Execute a BaseX command
        
        Args:
            command: Command string (e.g., "OPEN dbname", "INFO")
            
        Returns:
            Command output as string
        """
        if not self.session:
            self.connect()
            
        try:
            # BaseXClient.execute returns the output
            return self.session.execute(command)
        except Exception as e:
            logger.error(f"BaseX command failed: {command}. Error: {e}")
            # If error is connection related, try to reconnect once
            if "connection" in str(e).lower() or "broken" in str(e).lower():
                logger.info("Attempting reconnection...")
                self.connect()
                return self.session.execute(command)
            raise

    def execute_xquery(self, query: str) -> str:
        """
        Execute an XQuery
        
        Args:
            query: XQuery string
            
        Returns:
            Query result as string
        """
        return self.execute_command(f"XQUERY {query}")

    def ensure_database(self):
        """Ensure the target database exists"""
        try:
            self.execute_command(f"OPEN {self.db_name}")
        except Exception:
            logger.info(f"Database {self.db_name} not found, creating...")
            self.execute_command(f"CREATE DB {self.db_name}")

    def store_document(self, path: str, content: Union[str, bytes], run_add: bool = True):
        """
        Store a document in the database
        
        Args:
            path: Path/filename in the database
            content: XML or JSON content
            run_add: If True, executes ADD command. If False, assumes content is passed via other means or streams.
        """
        self.ensure_database()
        
        # Determine format (handling JSON/XML)
        # BaseX ADD command: ADD [TO path] input
        
        # Ensure content is string for command
        content_str = content
        if isinstance(content, bytes):
            content_str = content.decode('utf-8')
            
        # Using simple ADD command for small documents
        # wrapper for proper quoting/escaping might be needed for large content
        # For robustness, usually better to use specialized input streams or specific client methods
        # tailored for content upload. But standard client mainly does `execute`.
        
        # Caution: Passing content in command line string is risky for large data or special chars.
        # Ideally, we should use `session.add(path, input)` if the client library supports it.
        # The official BaseXClient python example usually shows `session.add(path, input)`.
        
        if hasattr(self.session, 'add'):
            self.session.add(path, content_str)
        else:
            # Fallback logic if needed, or raise erro
            logger.warning("BaseXClient session missing 'add' method. Using ADD command fallback.")
            # Note: This is fragile for special characters. 
            self.execute_command(f"ADD TO {path} {content_str}")

    def get_document(self, path: str) -> str:
        """Retrieve a document"""
        self.ensure_database()
        query = f"doc('{self.db_name}/{path}')"
        return self.execute_xquery(query)

    def store_versioned_document(self, doc_id: str, version: str, content: str, content_type: str = "xml") -> str:
        """
        Store a versioned document.
        Path strategy: {content_type}/{doc_id}/{version}.{ext}
        """
        ext = "xml" if content_type == "xml" else "json"
        
        # Sanitize path components
        safe_id = "".join(c for c in doc_id if c.isalnum() or c in "-_")
        safe_ver = "".join(c for c in version if c.isalnum() or c in ".-_")
        
        path = f"{content_type}/{safe_id}/{safe_ver}.{ext}"
        self.store_document(path, content)
        self.log_audit("store_version", f"Stored version {version} of {doc_id} at {path}")
        return path

    def init_audit_log(self):
        """Initialize audit log if not present"""
        try:
            # Check if audit.xml exists
            self.execute_xquery(f"doc('{self.db_name}/audit.xml')")
        except Exception:
             # Create it
             self.store_document("audit.xml", "<audit></audit>")

    def log_audit(self, action: str, details: str):
        """Append entry to audit log"""
        timestamp = datetime.now().isoformat()
        # Minimal escaping for XML content
        details = str(details).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        insert_query = f"""
        let $audit := doc('{self.db_name}/audit.xml')/audit
        return insert node 
        <entry>
            <timestamp>{timestamp}</timestamp>
            <action>{action}</action>
            <details>{details}</details>
        </entry>
        as last into $audit
        """
        try:
            self.execute_xquery(insert_query)
        except Exception as e:
            logger.warning(f"Failed to log audit (attempt 1): {e}")
            if "doc" in str(e) or "empty" in str(e):
                try:
                    self.init_audit_log()
                    self.execute_xquery(insert_query)
                except Exception as e2:
                    logger.error(f"Failed to recover audit log: {e2}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
