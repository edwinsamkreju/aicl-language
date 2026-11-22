"""Compare tokenizer counts for equivalent baseline and AICL files.

Install optional dependency: pip install -e '.[bench]'. Counts are source
length measurements only, not workflow-token or task-success benchmarks.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--encoding",default="cl100k_base"); args=p.parse_args()
 try: import tiktoken
 except ImportError:
  print("Missing optional dependency. Install with: pip install -e '.[bench]'",file=sys.stderr); return 2
 root=Path(__file__).resolve().parents[1]; tasks=json.loads((Path(__file__).parent/"tasks/manifest.json").read_text(encoding="utf-8")); enc=tiktoken.get_encoding(args.encoding); results=[]
 for task in tasks:
  baseline=(Path(__file__).parent/task["baseline"]).resolve(); candidate=(Path(__file__).parent/task["candidate"]).resolve()
  a=len(enc.encode(baseline.read_text(encoding="utf-8"))); b=len(enc.encode(candidate.read_text(encoding="utf-8")))
  results.append({"task":task["id"],"description":task["description"],"encoding":args.encoding,"baseline_tokens":a,"aicl_tokens":b,"token_reduction_fraction":round((a-b)/a if a else 0,6),"note":"Source token count only; not a task-success or total-workflow benchmark."})
 print(json.dumps({"results":results},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
