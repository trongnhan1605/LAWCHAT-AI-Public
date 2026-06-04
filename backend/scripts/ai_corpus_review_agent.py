from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.database import SessionLocal
from src.services.ai_corpus_review_agent_service import ai_corpus_review_agent_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AI pre-review agent for corpus quality.")
    parser.add_argument("--max-documents", type=int, default=None, help="Maximum number of documents to review.")
    parser.add_argument("--include-reviewed", action="store_true", help="Include documents already marked reviewed.")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path. Defaults to docs/legal_sources/ai_review_reports.")
    parser.add_argument("--print", action="store_true", help="Print the JSON report to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with SessionLocal() as db:
        report = ai_corpus_review_agent_service.review_pending_documents(
            db,
            max_documents=args.max_documents,
            include_reviewed=args.include_reviewed,
        )
    output_path = ai_corpus_review_agent_service.save_report(report, args.output)
    if args.print:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"AI corpus review report saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
