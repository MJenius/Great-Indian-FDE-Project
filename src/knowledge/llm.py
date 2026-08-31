"""
LLM abstraction and structured extraction layer with strict deterministic fallback.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class LLMExtractionResult(BaseModel):
    parsed_intent: Optional[str] = None
    extracted_entities: Dict[str, Any] = {}
    confidence: float = 0.0


class KnowledgeLLM:
    """
    Optional LLM abstraction for unstructured text interpretation.
    Enforces deterministic validation against structured canonical rules.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def interpret_semantic_query(self, query: str, candidate_rules: List[Any]) -> LLMExtractionResult:
        # In offline/deterministic mode, returns empty result allowing deterministic rules to govern
        return LLMExtractionResult(confidence=0.0)
