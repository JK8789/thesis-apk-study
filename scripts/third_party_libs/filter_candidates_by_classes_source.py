#!/usr/bin/env python3
"""
Filter candidate package roots by what appears in extracted APK class names.

Inputs:
- data/dicts/<source>/<topic>/prefix_candidates.txt
  where <source> is: mvnrepo or maven_central
- results/classes/<SHA>.txt
- results/baseline/apps_baseline.csv

Outputs:
- data/dicts/<source>/<topic>/prefix_hits.txt
- data/dicts/<source>/<topic>/hits_per_app.csv
- data/dicts/<source>/<topic>/hits_summary_region.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]
BASELINE = BASE / "results" / "baseline" / "apps_baseline.csv"
CLASSES_DIR = BASE / "results" / "classes"
DICT_ROOT = BASE / "data" / "dicts"

def load_candidates(source: str, topic: str) -> list[str]:
    p = DICT_ROOT / source / topic / "prefix_candidates.txt"
    if not p.exists():
        raise SystemExit(f"Missing {p}. Did you run the candidate builder for {source}/{topic}?")
    return [ln.strip() for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]

def load_baseline() -> list[dict]:
    if not BASELINE.exists():
        raise SystemExit(f"Missing baseline CSV: {BASELINE}")
    with BASELINE.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def class_file(sha: str) -> Path:
    return CLASSES_DIR / f"{sha.upper()}.txt"

def app_has_prefix(classes_path: Path, prefix: str) -> bool:
    if not classes_path.exists():
        return False
    needle = prefix + "."
    with classes_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            c = line.strip()
            if c == prefix or c.startswith(needle):
                return True
    return False

def write_lines(path: Path, lines: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for x in lines:
            f.write(x + "\n")

def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", help="payments / ads / analytics etc")
    ap.add_argument("--source", default="mvnrepo", choices=["mvnrepo", "maven_central"])
    ap.add_argument("--max-candidates", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    out_dir = DICT_ROOT / args.source / args.topic
    out_dir.mkdir(parents=True, exist_ok=True)

    cands = load_candidates(args.source, args.topic)
    if args.max_candidates and args.max_candidates > 0:
        cands = cands[:args.max_candidates]

    apps = load_baseline()

    supported_hits = set()
    region_prefix_apps = defaultdict(set)
    per_app = []

    for app in apps:
        sha = (app.get("sha256") or "").strip().upper()
        if not sha:
            continue

        region = (app.get("region") or "").strip()
        category = (app.get("category") or "").strip()
        pair_id = (app.get("pair_id") or "").strip()
        app_name = (app.get("app_name") or "").strip()
        package = (app.get("package") or "").strip()

        classes_path = class_file(sha)

        hits = []
        for pref in cands:
            if app_has_prefix(classes_path, pref):
                hits.append(pref)
                supported_hits.add(pref)
                region_prefix_apps[(region, pref)].add(app_name)

        per_app.append({
            "sha256": sha,
            "region": region,
            "category": category,
            "pair_id": pair_id,
            "app_name": app_name,
            "package": package,
            "topic": args.topic,
            "source": args.source,
            "hit_count": len(hits),
            "hits": ";".join(sorted(hits)),
        })

    write_lines(out_dir / "prefix_hits.txt", sorted(supported_hits))
    write_csv(out_dir / "hits_per_app.csv", per_app,
              ["sha256","region","category","pair_id","app_name","package","topic","source","hit_count","hits"])

    summary = []
    for (region, pref), shas in region_prefix_apps.items():
        apps = sorted([a for a in shas if a])  # shas now contains app_name strings
        summary.append({
            "region": region,
            "prefix": pref,
            "apps_with_prefix": len(apps),
            "in_which_APKs": ";".join(apps),
        })
    summary.sort(key=lambda x: (-x["apps_with_prefix"], x["region"], x["prefix"]))

    write_csv(out_dir / "hits_summary_region.csv", summary, ["region","prefix","apps_with_prefix","in_which_APKs"])

    print("[OK] Wrote:")
    print(" -", out_dir / "prefix_hits.txt")
    print(" -", out_dir / "hits_per_app.csv")
    print(" -", out_dir / "hits_summary_region.csv")
    print(f"[STATS] candidates={len(cands)} supported_hits={len(supported_hits)} apps={len(per_app)}")

if __name__ == "__main__":
    main()
