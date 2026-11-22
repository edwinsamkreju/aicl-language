"""Compare compact AICL patches with equivalent minified JSON patches.

The character count is always reported. Optional tiktoken counts are reported
only when the optional dependency is installed. This is a representation
microbenchmark, not an end-to-end AI workflow benchmark.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_HASH = "sha256:" + "0" * 64


def payloads():
    compact = (
        "aicl-patch 0.2\n"
        f"base {BASE_HASH}\n"
        "node scale n:scale:body/right = 3\n"
    )
    structured = {
        "base_hash": BASE_HASH,
        "operations": [{
            "op": "replace_node",
            "function": "scale",
            "node_id": "n:scale:body/right",
            "expression": "3",
        }],
    }
    json_text = json.dumps(structured, separators=(",", ":")) + "\n"
    return compact, json_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoding", default="cl100k_base")
    args = parser.parse_args()
    compact, json_text = payloads()
    result = {
        "compact_patch_characters": len(compact),
        "json_patch_characters": len(json_text),
        "character_reduction_percent": round((1 - len(compact) / len(json_text)) * 100, 2),
        "warning": "Character reduction is not tokenizer reduction or an end-to-end workflow result.",
    }
    try:
        import tiktoken
    except ImportError:
        result["token_counts"] = "Not measured: install the optional 'bench' dependency."
    else:
        encoding = tiktoken.get_encoding(args.encoding)
        compact_tokens = len(encoding.encode(compact))
        json_tokens = len(encoding.encode(json_text))
        result["token_counts"] = {
            "encoding": args.encoding,
            "compact_patch": compact_tokens,
            "json_patch": json_tokens,
            "token_reduction_percent": round((1 - compact_tokens / json_tokens) * 100, 2),
        }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
