"""
Diagnostics and audit report generator for Knowledge Engine.
"""
from __future__ import annotations

from pathlib import Path
from typing import List
import pandas as pd

from .models import KnowledgeAnswer


class KnowledgeDiagnostics:
    @staticmethod
    def generate_submission_csv(answers: List[KnowledgeAnswer], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {"qid": a.qid, "answer": a.answer, "governing_source": a.governing_source}
            for a in answers
        ]
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding="utf-8")

    @staticmethod
    def generate_diagnostics_csv(answers: List[KnowledgeAnswer], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "qid": a.qid,
                "answer": a.answer,
                "governing_source": a.governing_source,
                "confidence": a.confidence,
                "status": a.status,
                "rule_id": a.rule_id,
                "evidence_text": a.evidence_text,
                "resolution_notes": a.resolution_notes,
                "why_this_source": a.why_this_source,
                "why_other_sources_rejected": a.why_other_sources_rejected,
            }
            for a in answers
        ]
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding="utf-8")
