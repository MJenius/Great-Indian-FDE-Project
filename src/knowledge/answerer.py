"""
Orchestrator for the Knowledge Policy Engine.
Routes questions, resolves governing policies, deterministically evaluates rules, and outputs answers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from .document_loader import DocumentLoader
from .evaluator import PolicyEvaluator
from .models import KnowledgeAnswer, PolicyRule
from .policy_resolver import PolicyResolver
from .policy_rules import build_canonical_policy_rules
from .router import QuestionRouter


class KnowledgeEngine:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir
        self.rules: List[PolicyRule] = build_canonical_policy_rules()

    def answer_question(self, qid: str, question_text: str) -> KnowledgeAnswer:
        # 1. Parse & route question
        interp = QuestionRouter.parse_question(qid, question_text)

        # 2. Resolve governing policy rule & rationale
        rule, why_this, why_other = PolicyResolver.resolve_governing_rule(interp, self.rules)

        # 3. Deterministically evaluate answer
        answer = PolicyEvaluator.evaluate_rule(interp, rule, why_this, why_other)
        return answer

    def answer_all(self, questions_df: pd.DataFrame) -> List[KnowledgeAnswer]:
        results: List[KnowledgeAnswer] = []
        for _, row in questions_df.iterrows():
            qid = str(row["qid"]).strip()
            q_text = str(row["question"]).strip()
            ans = self.answer_question(qid, q_text)
            results.append(ans)
        return results
