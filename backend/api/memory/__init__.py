"""
Memory Package
Hybrid semantic + keyword search for agent context retrieval.

Modules:
- hybrid_memory: OpenSearch-based vector memory with k-NN
"""

__version__ = "0.1.0"

from .hybrid_memory import (
    HybridMemorySystem,
    OpenSearchConfig,
    AzureOpenAIEmbeddings,
    OpenSearchIndexManager
)

__all__ = [
    "HybridMemorySystem",
    "OpenSearchConfig", 
    "AzureOpenAIEmbeddings",
    "OpenSearchIndexManager"
]
