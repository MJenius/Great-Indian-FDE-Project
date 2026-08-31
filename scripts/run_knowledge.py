#!/usr/bin/env python3
"""
run_knowledge.py — CLI runner for Knowledge Policy Engine.

Usage:
    python scripts/run_knowledge.py --data-dir data --output-dir outputs
    python scripts/run_knowledge.py --data-dir data --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge.answerer import KnowledgeEngine
from src.knowledge.diagnostics import KnowledgeDiagnostics


def main():
    parser = argparse.ArgumentParser(description="Run DRI Knowledge Engine")
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    parser.add_argument("--output-dir", default="outputs", help="Path to outputs directory")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run without writing outputs")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    questions_path = data_dir / "knowledge_questions.csv"
    if not questions_path.exists():
        print(f"Error: Questions file not found at {questions_path}")
        sys.exit(1)

    df_questions = pd.read_csv(questions_path)
    engine = KnowledgeEngine(data_dir=data_dir)

    print("==================================================")
    print("RUNNING KNOWLEDGE ENGINE")
    print(f"Questions: {len(df_questions)} | Dry Run: {args.dry_run}")
    print("==================================================")

    answers = engine.answer_all(df_questions)

    for ans in answers:
        print(f"\n[{ans.qid}] {ans.governing_source}")
        print(f"  Answer: {ans.answer}")
        print(f"  Why Source: {ans.why_this_source}")

    if not args.dry_run:
        sub_path = output_dir / "knowledge_submission.csv"
        diag_path = output_dir / "knowledge_diagnostics.csv"
        KnowledgeDiagnostics.generate_submission_csv(answers, sub_path)
        KnowledgeDiagnostics.generate_diagnostics_csv(answers, diag_path)
        print(f"\nSubmission CSV saved to: {sub_path}")
        print(f"Diagnostics CSV saved to: {diag_path}")


if __name__ == "__main__":
    main()
