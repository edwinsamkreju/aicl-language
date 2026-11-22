"""Compare tokenizer counts for equivalent baseline and AICL files.

Install optional dependency: pip install -e '.[bench]'. Counts are source
token measurements only, not workflow-token or task-success benchmarks.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoding", default="cl100k_base")
    args = parser.parse_args()
    try:
        import tiktoken
    except ImportError:
        print("Missing optional dependency. Install with: pip install -e '.[bench]'", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / "benchmarks/tasks/manifest.json").read_text(encoding="utf-8"))
    encoding = tiktoken.get_encoding(args.encoding)
    results = []
    for task in tasks:
        baseline = root / task["baseline"]
        candidate = root / task["candidate"]
        baseline_tokens = len(encoding.encode(baseline.read_text(encoding="utf-8")))
        aicl_tokens = len(encoding.encode(candidate.read_text(encoding="utf-8")))
        results.append({
            "task": task["id"],
            "description": task["description"],
            "encoding": args.encoding,
            "baseline_source_tokens": baseline_tokens,
            "aicl_source_tokens": aicl_tokens,
            "source_token_reduction_fraction": round(
                (baseline_tokens - aicl_tokens) / baseline_tokens if baseline_tokens else 0, 6
            ),
            "note": "Source token count only; not a task-success or total-workflow benchmark."
        })
    print(json.dumps({"results": results}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
