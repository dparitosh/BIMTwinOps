"""
Router Agent: Advanced Intent Classification
Enhanced with NeMo Guardrails and structured output.

This module extends the basic router with:
1. Structured JSON output (Azure OpenAI JSON mode)
2. Input validation (NeMo Guardrails integration ready)
3. Confidence scoring
4. Context-aware routing

Intent Categories:
- query: Read-only data retrieval
- action: State modification (CRUD)
- planning: Multi-step workflows
- unknown: Clarification needed

Confidence Thresholds:
- High (>0.8): Route immediately
- Medium (0.5-0.8): Route with warning
- Low (<0.5): Request clarification

Design Pattern: Chain of Responsibility
Router → Validator → Classifier → Router Logic
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Intent Classification Schema
# ============================================================================

class IntentType(str, Enum):
    """Supported intent types"""
    QUERY = "query"
    ACTION = "action"
    PLANNING = "planning"
    UNKNOWN = "unknown"


class IntentClassification(BaseModel):
    """
    Structured output from router agent
    
    Pydantic model for JSON schema validation and parsing.
    Used with Azure OpenAI JSON mode for guaranteed structure.
    """
    intent: IntentType = Field(
        description="Classified user intent"
    )
    reasoning: str = Field(
        description="Step-by-step reasoning for classification"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Key terms that influenced classification"
    )
    suggested_agent: str = Field(
        description="Recommended specialist agent"
    )
    requires_clarification: bool = Field(
        default=False,
        description="Whether user input needs clarification"
    )
    clarification_questions: Optional[List[str]] = Field(
        default=None,
        description="Questions to ask if clarification needed"
    )


# ============================================================================
# Input Validation (NeMo Guardrails Integration Point)
# ============================================================================

class InputValidator:
    """
    Input validation and safety checks
    
    Integration point for NeMo Guardrails or similar frameworks.
    Currently implements basic checks; can be extended with:
    - Toxicity detection
    - PII detection
    - Jailbreak prevention
    - Domain scope validation
    """
    
    @staticmethod
    def validate(user_input: str) -> Dict[str, Any]:
        """
        Validate user input for safety and scope
        
        Args:
            user_input: Raw user message
        
        Returns:
            Dict with validation results
        """
        # Basic validation
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Length checks
        if len(user_input.strip()) == 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Empty input")
        
        if len(user_input) > 2000:
            validation_result["warnings"].append("Input exceeds recommended length")
        
        # TODO: Add NeMo Guardrails integration
        # from guardrails import Guard
        # guard = Guard.from_rail_file("rails/router_rails.co")
        # guard_result = guard.validate(user_input)
        
        return validation_result


# ============================================================================
# Enhanced Router Agent
# ============================================================================

class EnhancedRouterAgent:
    """
    Advanced router with structured output and validation
    
    Improvements over basic router:
    1. JSON mode for reliable parsing
    2. Confidence thresholds
    3. Input validation
    4. Context awareness
    5. Clarification logic
    
    Usage:
        router = EnhancedRouterAgent()
        classification = await router.classify("Show me all walls")
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.8
    LOW_CONFIDENCE = 0.5
    
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.3
    ):
        """
        Initialize enhanced router
        
        Args:
            model: Azure OpenAI deployment name
            temperature: Sampling temperature (lower = more deterministic)
        """
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", model),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            temperature=temperature,
            model_kwargs={"response_format": {"type": "json_object"}}  # JSON mode
        )
        
        self.validator = InputValidator()
        self.parser = JsonOutputParser(pydantic_object=IntentClassification)
        
        # Create classification prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._create_system_prompt()),
            ("human", "{input}")
        ])
        
        self.chain = self.prompt | self.llm | self.parser
    
    def _create_system_prompt(self) -> str:
        """Create detailed system prompt for classification"""
        return """You are an advanced Router Agent for a BIM/AEC Intelligent Application.

Your role: Analyze user requests and classify them into precise intent categories.

# Intent Categories

## 1. QUERY (Read-Only Retrieval)
Information lookup without state modification:
- "Show me all walls with fire rating > 60"
- "What properties does this door have?"
- "Find bSDD definitions for IfcWall"
- "List spaces on Level 2"
- "Search for HVAC components"

Keywords: show, list, find, search, what, get, retrieve, display

## 2. ACTION (State Modification)
Operations that create, update, or delete data:
- "Create a new space named Conference Room A"
- "Update wall fire rating to 90 minutes"
- "Import IFC file from path X"
- "Segment this point cloud"
- "Delete duplicate elements"

Keywords: create, update, delete, import, export, modify, segment

## 3. PLANNING (Multi-Step Workflows)
Complex tasks requiring orchestration:
- "Optimize HVAC layout for energy efficiency"
- "Generate fire safety compliance report"
- "Plan renovation sequence for Building A"
- "Schedule installation tasks"
- "Analyze clash detection results"

Keywords: optimize, generate, plan, analyze, schedule, coordinate

## 4. UNKNOWN (Unclear/Out-of-Scope)
Requests that are ambiguous or outside BIM/AEC domain:
- Unclear intent
- Missing context
- Non-AEC topics
- Requires clarification

# Classification Process

1. **Identify Keywords**: Extract key action verbs and domain terms
2. **Determine Operation**: Read vs Write vs Multi-step
3. **Assess Confidence**: How certain are you?
4. **Check Scope**: Is it BIM/AEC related?
5. **Suggest Agent**: Which specialist should handle this?

# Output Format (JSON)

You MUST respond with valid JSON matching this schema:

{
    "intent": "query" | "action" | "planning" | "unknown",
    "reasoning": "Step-by-step explanation of classification",
    "confidence": 0.0 to 1.0,
    "keywords": ["keyword1", "keyword2"],
    "suggested_agent": "query_agent" | "action_agent" | "planning_agent" | "unknown_agent",
    "requires_clarification": true | false,
    "clarification_questions": ["Question 1?", "Question 2?"] or null
}

# Confidence Guidelines

- **0.9-1.0**: Very clear intent, obvious keywords
- **0.7-0.9**: Clear intent, minor ambiguity
- **0.5-0.7**: Moderate ambiguity, context needed
- **0.0-0.5**: High ambiguity, requires clarification

# Clarification Criteria

Set `requires_clarification: true` when:
- Confidence < 0.5
- Critical information missing
- Ambiguous pronouns ("it", "that", "this")
- Multiple possible intents

Think carefully and respond ONLY with valid JSON."""
    
    async def classify(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentClassification:
        """
        Classify user intent with confidence scoring
        
        Args:
            user_input: User's message
            context: Optional conversation context
        
        Returns:
            IntentClassification with routing decision
        
        Raises:
            ValueError: If input validation fails
        """
        logger.info(f"Classifying intent for: {user_input[:100]}...")
        
        # Validate input
        validation = self.validator.validate(user_input)
        if not validation["is_valid"]:
            raise ValueError(f"Invalid input: {validation['errors']}")
        
        # Add context to input if provided
        full_input = user_input
        if context:
            full_input = f"Context: {context}\n\nUser: {user_input}"
        
        try:
            # Run classification
            result = await self.chain.ainvoke({"input": full_input})
            
            # Convert dict to Pydantic model
            classification = IntentClassification(**result)
            
            logger.info(
                f"Classified as {classification.intent} "
                f"(confidence: {classification.confidence:.2f})"
            )
            
            # Check confidence threshold
            if classification.confidence < self.LOW_CONFIDENCE:
                classification.requires_clarification = True
                if not classification.clarification_questions:
                    classification.clarification_questions = [
                        "Could you provide more details about what you'd like to do?",
                        "What specific information or action are you looking for?"
                    ]
            
            return classification
            
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            
            # Fallback to unknown
            return IntentClassification(
                intent=IntentType.UNKNOWN,
                reasoning=f"Classification error: {str(e)}",
                confidence=0.0,
                keywords=[],
                suggested_agent="unknown_agent",
                requires_clarification=True,
                clarification_questions=[
                    "I had trouble understanding your request. Could you rephrase it?"
                ]
            )
    
    def should_route(self, classification: IntentClassification) -> bool:
        """
        Determine if classification is confident enough to route
        
        Args:
            classification: Intent classification result
        
        Returns:
            True if should route to specialist agent, False if needs clarification
        """
        return (
            classification.confidence >= self.LOW_CONFIDENCE
            and not classification.requires_clarification
            and classification.intent != IntentType.UNKNOWN
        )


# ============================================================================
# Router Metrics & Logging
# ============================================================================

class RouterMetrics:
    """
    Track router performance metrics
    
    Useful for monitoring and optimization:
    - Intent distribution
    - Confidence scores
    - Classification time
    - Error rates
    """
    
    def __init__(self):
        self.classifications = []
        self.errors = 0
    
    def log_classification(
        self,
        user_input: str,
        classification: IntentClassification,
        duration_ms: float
    ):
        """Record classification for analytics"""
        self.classifications.append({
            "timestamp": datetime.now().isoformat(),
            "input_length": len(user_input),
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "duration_ms": duration_ms,
            "clarification_needed": classification.requires_clarification
        })
    
    def log_error(self, error: Exception):
        """Record classification error"""
        self.errors += 1
        logger.error(f"Router error: {str(error)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        if not self.classifications:
            return {"total": 0, "errors": self.errors}
        
        intents = [c["intent"] for c in self.classifications]
        confidences = [c["confidence"] for c in self.classifications]
        durations = [c["duration_ms"] for c in self.classifications]
        
        return {
            "total": len(self.classifications),
            "errors": self.errors,
            "intent_distribution": {
                intent: intents.count(intent) for intent in set(intents)
            },
            "avg_confidence": sum(confidences) / len(confidences),
            "avg_duration_ms": sum(durations) / len(durations),
            "clarification_rate": sum(
                1 for c in self.classifications if c["clarification_needed"]
            ) / len(self.classifications)
        }


# ============================================================================
# Testing
# ============================================================================

async def test_router():
    """Test enhanced router with sample inputs"""
    import os
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://your-endpoint.openai.azure.com"
    os.environ["AZURE_OPENAI_API_KEY"] = "your-key"
    
    router = EnhancedRouterAgent()
    metrics = RouterMetrics()
    
    test_cases = [
        "Show me all walls with fire rating > 60",
        "Create a new space named Conference Room A",
        "Generate a compliance report for fire safety",
        "What's the weather like?",  # Out of scope
        "it needs to be updated",  # Ambiguous
    ]
    
    for test_input in test_cases:
        print(f"\n{'='*60}")
        print(f"Input: {test_input}")
        print(f"{'='*60}")
        
        try:
            start = datetime.now()
            classification = await router.classify(test_input)
            duration = (datetime.now() - start).total_seconds() * 1000
            
            print(f"Intent: {classification.intent.value}")
            print(f"Confidence: {classification.confidence:.2f}")
            print(f"Reasoning: {classification.reasoning}")
            print(f"Keywords: {classification.keywords}")
            print(f"Suggested Agent: {classification.suggested_agent}")
            
            if classification.requires_clarification:
                print(f"Clarification Needed:")
                for q in classification.clarification_questions or []:
                    print(f"  - {q}")
            
            metrics.log_classification(test_input, classification, duration)
            
        except Exception as e:
            print(f"Error: {str(e)}")
            metrics.log_error(e)
    
    print(f"\n{'='*60}")
    print("METRICS")
    print(f"{'='*60}")
    print(metrics.get_stats())


if __name__ == "__main__":
    import asyncio
    import os
    asyncio.run(test_router())
