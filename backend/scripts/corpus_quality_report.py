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
from src.services.corpus_quality_report_service import corpus_quality_report_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate LawChat-AI corpus quality report.")
    parser.add_argument("--pending-only", action="store_true", help="Only include documents not marked reviewed.")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with SessionLocal() as db:
        report = corpus_quality_report_service.build_report(db, include_reviewed=not args.pending_only)

    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
