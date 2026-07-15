# scripts/engine_parity_diff.py
"""Compare kkoclaw engine against a local deer-flow checkout.
Usage: uv run python scripts/engine_parity_diff.py /path/to/deer-flow
"""
import os, sys
from pathlib import Path

def collect(root, prefix):
    files = set()
    for dp, dn, fn in os.walk(root):
        if "__pycache__" in dp: continue
        for f in fn:
            if f.endswith((".pyc",)): continue
            files.add(os.path.relpath(os.path.join(dp, f), root))
    return files

def main(upstream_root):
    up = Path(upstream_root) / "backend/packages/harness/deerflow"
    kk = Path("backend/packages/harness/kkoclaw")
    up_files = collect(up, None)
    kk_files = collect(kk, None)
    only_up = sorted(up_files - kk_files)
    only_kk = sorted(kk_files - up_files)
    print(f"ONLY UPSTREAM (port candidates): {len(only_up)}")
    print(f"ONLY KKOCLAW  (preserve):       {len(only_kk)}")
    print(f"COMMON (merged):                {len(up_files & kk_files)}")
    print("\n=== ONLY UPSTREAM ===")
    for p in only_up: print("  " + p)
    print("\n=== ONLY KKOCLAW ===")
    for p in only_kk: print("  " + p)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/deer-flow-upstream")
