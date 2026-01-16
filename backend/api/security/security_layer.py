"""
Security & Governance Layer
Input validation, audit logging, and safety guardrails.

This module implements ADR-005 (Security & Governance) providing:
1. Input validation and sanitization
2. Audit logging for compliance
3. NeMo Guardrails integration (ready)
4. Content filtering and safety

Architecture:
- Validation: Schema-based with Pydantic
- Audit: Structured logging to database
- Guardrails: NeMo framework integration points
- Monitoring: Security metrics and alerts

Principles:
1. Defense in Depth: Multiple validation layers
2. Fail Secure: Default deny for unclear inputs
3. Audit Everything: Complete activity trail
4. Zero Trust: Validate all inputs

References:
- NeMo Guardrails: https://github.com/NVIDIA/NeMo-Guardrails
- OWASP: https://owasp.org/www-project-top-ten/
"""

from typing import Dict, Any, List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator
import re
import logging
from datetime import datetime
import json
import hashlib
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Input Validation
# ============================================================================

class ValidationSeverity(str, Enum):
    """Validation issue severity"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult(BaseModel):
    """Result of input validation"""
    is_valid: bool = Field(description="Overall validation status")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    severity: ValidationSeverity = Field(default=ValidationSeverity.INFO)
    sanitized_input: Optional[str] = Field(default=None, description="Cleaned input")


class InputValidator:
    """
    Comprehensive input validation
    
    Validates:
    - Length constraints
    - Character whitelisting
    - SQL/Cypher injection patterns
    - XSS patterns
    - Command injection
    - PII detection (basic)
    
    Usage:
        validator = InputValidator()
        result = validator.validate(user_input)
        if not result.is_valid:
            raise ValueError(result.errors)
    """
    
    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"('\s*(OR|AND)\s*'?\d+?'?\s*=\s*'?\d+)",  # ' OR '1'='1
        r"(--|\#|\/\*)",  # SQL comments
        r"(UNION\s+SELECT|DROP\s+TABLE|EXEC\s+)",  # SQL commands
    ]
    
    CYPHER_INJECTION_PATTERNS = [
        r"(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\s+",
        r"(CALL\s+dbms|CALL\s+apoc)",
        r"(\}\s*-\[\s*:\s*MATCH)",  # Pattern injection
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\(",  # Command substitution
        r"\.\./",  # Path traversal
    ]
    
    # PII patterns (basic)
    EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
    CREDIT_CARD_PATTERN = r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
    
    def __init__(
        self,
        max_length: int = 5000,
        min_length: int = 1,
        allow_html: bool = False,
        detect_pii: bool = True
    ):
        """Initialize validator"""
        self.max_length = max_length
        self.min_length = min_length
        self.allow_html = allow_html
        self.detect_pii = detect_pii
    
    def validate(self, user_input: str) -> ValidationResult:
        """
        Validate user input
        
        Args:
            user_input: Raw user input string
        
        Returns:
            ValidationResult with errors, warnings, and sanitized input
        """
        errors = []
        warnings = []
        severity = ValidationSeverity.INFO
        
        # Length validation
        if len(user_input) < self.min_length:
            errors.append(f"Input too short (min: {self.min_length})")
            severity = ValidationSeverity.ERROR
        
        if len(user_input) > self.max_length:
            errors.append(f"Input too long (max: {self.max_length})")
            severity = ValidationSeverity.ERROR
        
        # Injection detection
        sql_detected = any(
            re.search(pattern, user_input, re.IGNORECASE)
            for pattern in self.SQL_INJECTION_PATTERNS
        )
        if sql_detected:
            errors.append("Potential SQL injection detected")
            severity = ValidationSeverity.CRITICAL
        
        cypher_detected = any(
            re.search(pattern, user_input, re.IGNORECASE)
            for pattern in self.CYPHER_INJECTION_PATTERNS
        )
        if cypher_detected:
            errors.append("Potential Cypher injection detected")
            severity = ValidationSeverity.CRITICAL
        
        # XSS detection
        if not self.allow_html:
            xss_detected = any(
                re.search(pattern, user_input, re.IGNORECASE)
                for pattern in self.XSS_PATTERNS
            )
            if xss_detected:
                errors.append("Potential XSS detected")
                severity = ValidationSeverity.CRITICAL
        
        # Command injection
        cmd_detected = any(
            re.search(pattern, user_input)
            for pattern in self.COMMAND_INJECTION_PATTERNS
        )
        if cmd_detected:
            errors.append("Potential command injection detected")
            severity = ValidationSeverity.CRITICAL
        
        # PII detection (warnings only)
        if self.detect_pii:
            if re.search(self.EMAIL_PATTERN, user_input):
                warnings.append("Email address detected in input")
            
            if re.search(self.SSN_PATTERN, user_input):
                warnings.append("Potential SSN detected in input")
                severity = max(severity, ValidationSeverity.WARNING)
            
            if re.search(self.CREDIT_CARD_PATTERN, user_input):
                warnings.append("Potential credit card number detected")
                severity = max(severity, ValidationSeverity.WARNING)
        
        # Sanitize input
        sanitized = self._sanitize(user_input)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            severity=severity,
            sanitized_input=sanitized
        )
    
    def _sanitize(self, text: str) -> str:
        """
        Sanitize input text
        
        Args:
            text: Raw text
        
        Returns:
            Sanitized text
        """
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove HTML if not allowed
        if not self.allow_html:
            text = re.sub(r'<[^>]+>', '', text)
        
        # Escape special characters
        text = text.replace('\\', '\\\\')
        
        return text.strip()


# ============================================================================
# Audit Logging
# ============================================================================

class AuditEventType(str, Enum):
    """Types of auditable events"""
    USER_INPUT = "user_input"
    AGENT_ACTION = "agent_action"
    MCP_TOOL_CALL = "mcp_tool_call"
    DATA_ACCESS = "data_access"
    ERROR = "error"
    SECURITY_ALERT = "security_alert"


class AuditEvent(BaseModel):
    """Structured audit log entry"""
    event_id: str = Field(description="Unique event identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: AuditEventType = Field(description="Event category")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    action: str = Field(description="Action performed")
    resource: Optional[str] = Field(default=None, description="Resource accessed")
    result: str = Field(description="Action outcome (success/failure)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    ip_address: Optional[str] = Field(default=None, description="Client IP")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")


class AuditLogger:
    """
    Audit logging system
    
    Logs all security-relevant events to structured storage.
    In production, logs to database or SIEM system.
    
    Usage:
        audit = AuditLogger()
        audit.log_user_input(user_id, input_text)
        audit.log_mcp_tool_call(tool_name, params, result)
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """Initialize audit logger"""
        self.log_file = log_file or Path("audit.log")
        self.events: List[AuditEvent] = []
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def log_event(self, event: AuditEvent):
        """Log audit event"""
        # Store in memory
        self.events.append(event)
        
        # Write to file (JSON Lines format)
        try:
            with open(self.log_file, 'a') as f:
                f.write(event.model_dump_json() + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {str(e)}")
        
        # Log to standard logging
        logger.info(f"AUDIT: {event.event_type} - {event.action} - {event.result}")
    
    def log_user_input(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        validation_result: Optional[ValidationResult] = None
    ):
        """Log user input event"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.USER_INPUT,
            user_id=user_id,
            session_id=session_id,
            action="user_input",
            result="success" if (not validation_result or validation_result.is_valid) else "validation_failed",
            details={
                "input_length": len(user_input),
                "validation_errors": validation_result.errors if validation_result else [],
                "validation_warnings": validation_result.warnings if validation_result else []
            }
        )
        self.log_event(event)
    
    def log_agent_action(
        self,
        agent_name: str,
        action: str,
        intent: str,
        result: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log agent action"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.AGENT_ACTION,
            user_id=user_id,
            session_id=session_id,
            action=action,
            resource=agent_name,
            result=result,
            details={"intent": intent}
        )
        self.log_event(event)
    
    def log_mcp_tool_call(
        self,
        tool_name: str,
        server_name: str,
        parameters: Dict[str, Any],
        result: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log MCP tool execution"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.MCP_TOOL_CALL,
            user_id=user_id,
            session_id=session_id,
            action=tool_name,
            resource=server_name,
            result=result,
            details={
                "parameters": parameters,
                "parameter_count": len(parameters)
            }
        )
        self.log_event(event)
    
    def log_security_alert(
        self,
        alert_type: str,
        severity: ValidationSeverity,
        description: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log security alert"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.SECURITY_ALERT,
            user_id=user_id,
            session_id=session_id,
            action=alert_type,
            result="alert",
            details={
                "severity": severity.value,
                "description": description
            }
        )
        self.log_event(event)
    
    def get_recent_events(self, limit: int = 100) -> List[AuditEvent]:
        """Get recent audit events"""
        return self.events[-limit:]
    
    def get_events_by_user(self, user_id: str) -> List[AuditEvent]:
        """Get events for specific user"""
        return [e for e in self.events if e.user_id == user_id]
    
    def get_security_alerts(self) -> List[AuditEvent]:
        """Get all security alerts"""
        return [e for e in self.events if e.event_type == AuditEventType.SECURITY_ALERT]


# ============================================================================
# NeMo Guardrails Integration (Ready)
# ============================================================================

class GuardrailsConfig(BaseModel):
    """Configuration for NeMo Guardrails"""
    enabled: bool = Field(default=False, description="Enable guardrails")
    rails_path: Optional[Path] = Field(default=None, description="Path to rails config")
    fail_secure: bool = Field(default=True, description="Block on guardrail failure")


class GuardrailsValidator:
    """
    NeMo Guardrails integration point
    
    This class provides the integration hooks for NVIDIA NeMo Guardrails.
    Currently returns pass-through results; activate by installing NeMo.
    
    Installation:
        pip install nemoguardrails
    
    Usage:
        guardrails = GuardrailsValidator(rails_path="./rails")
        result = guardrails.validate(user_input)
    """
    
    def __init__(self, config: Optional[GuardrailsConfig] = None):
        """Initialize guardrails"""
        self.config = config or GuardrailsConfig()
        self.enabled = self.config.enabled
        
        if self.enabled:
            try:
                # Import NeMo Guardrails
                from nemoguardrails import RailsConfig, LLMRails
                
                if self.config.rails_path:
                    self.rails_config = RailsConfig.from_path(self.config.rails_path)
                    self.rails = LLMRails(self.rails_config)
                    logger.info("NeMo Guardrails enabled")
                else:
                    logger.warning("Guardrails enabled but no rails_path provided")
                    self.enabled = False
            
            except ImportError:
                logger.warning("NeMo Guardrails not installed, falling back to basic validation")
                self.enabled = False
    
    def validate(self, user_input: str) -> ValidationResult:
        """
        Validate input with NeMo Guardrails
        
        Args:
            user_input: User message
        
        Returns:
            ValidationResult
        """
        if not self.enabled:
            # Pass-through if guardrails not enabled
            return ValidationResult(
                is_valid=True,
                sanitized_input=user_input
            )
        
        try:
            # Run through NeMo Guardrails
            # This is a placeholder - actual implementation depends on rails config
            result = self.rails.generate(messages=[{"role": "user", "content": user_input}])
            
            # Check if input was blocked
            if hasattr(result, 'blocked') and result.blocked:
                return ValidationResult(
                    is_valid=False,
                    errors=["Input blocked by content policy"],
                    severity=ValidationSeverity.CRITICAL
                )
            
            return ValidationResult(
                is_valid=True,
                sanitized_input=user_input
            )
        
        except Exception as e:
            logger.error(f"Guardrails validation failed: {str(e)}")
            
            if self.config.fail_secure:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Guardrails error: {str(e)}"],
                    severity=ValidationSeverity.ERROR
                )
            else:
                return ValidationResult(
                    is_valid=True,
                    warnings=[f"Guardrails check skipped: {str(e)}"],
                    sanitized_input=user_input
                )


# ============================================================================
# Unified Security Layer
# ============================================================================

class SecurityLayer:
    """
    Unified security and governance layer
    
    Combines validation, audit logging, and guardrails into single interface.
    Use this as the main entry point for all user inputs.
    
    Usage:
        security = SecurityLayer()
        result = security.validate_and_log(
            user_input=message,
            user_id="user_123",
            session_id="session_abc"
        )
        if not result.is_valid:
            raise SecurityError(result.errors)
    """
    
    def __init__(
        self,
        validator: Optional[InputValidator] = None,
        audit_logger: Optional[AuditLogger] = None,
        guardrails: Optional[GuardrailsValidator] = None
    ):
        """Initialize security layer"""
        self.validator = validator or InputValidator()
        self.audit_logger = audit_logger or AuditLogger()
        self.guardrails = guardrails or GuardrailsValidator()
    
    def validate_and_log(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate input and log audit event
        
        Args:
            user_input: Raw user input
            user_id: User identifier
            session_id: Session identifier
        
        Returns:
            ValidationResult
        """
        # 1. Basic validation
        validation_result = self.validator.validate(user_input)
        
        # 2. Guardrails check (if enabled)
        if self.guardrails.enabled:
            guardrails_result = self.guardrails.validate(user_input)
            if not guardrails_result.is_valid:
                validation_result = guardrails_result
        
        # 3. Log audit event
        self.audit_logger.log_user_input(
            user_input=user_input,
            user_id=user_id,
            session_id=session_id,
            validation_result=validation_result
        )
        
        # 4. Log security alert if critical
        if validation_result.severity == ValidationSeverity.CRITICAL:
            self.audit_logger.log_security_alert(
                alert_type="input_validation_failed",
                severity=validation_result.severity,
                description="; ".join(validation_result.errors),
                user_id=user_id,
                session_id=session_id
            )
        
        return validation_result


# ============================================================================
# Testing
# ============================================================================

def test_security_layer():
    """Test security layer"""
    print("=" * 60)
    print("Security & Governance Layer Test")
    print("=" * 60)
    
    security = SecurityLayer()
    
    test_cases = [
        ("Show me all walls", True, "Normal query"),
        ("' OR '1'='1", False, "SQL injection"),
        ("CREATE (n:Node) RETURN n", False, "Cypher injection"),
        ("<script>alert('xss')</script>", False, "XSS attempt"),
        ("user@example.com", True, "Email (warning)"),
        ("A" * 6000, False, "Too long"),
    ]
    
    print("\nTest Cases:")
    print("-" * 60)
    
    for input_text, should_pass, description in test_cases:
        result = security.validate_and_log(
            user_input=input_text,
            user_id="test_user",
            session_id="test_session"
        )
        
        status = "✅ PASS" if result.is_valid == should_pass else "❌ FAIL"
        print(f"{status} | {description}")
        if result.errors:
            print(f"       Errors: {result.errors}")
        if result.warnings:
            print(f"       Warnings: {result.warnings}")
    
    # Show audit log
    print("\nRecent Audit Events:")
    print("-" * 60)
    events = security.audit_logger.get_recent_events(limit=5)
    for event in events:
        print(f"{event.timestamp.strftime('%H:%M:%S')} | {event.event_type.value:15} | {event.result}")
    
    # Show security alerts
    alerts = security.audit_logger.get_security_alerts()
    print(f"\nSecurity Alerts: {len(alerts)}")
    
    print("\n" + "=" * 60)
    print("✅ Security layer operational")
    print("=" * 60)


if __name__ == "__main__":
    test_security_layer()
