#!/usr/bin/env python3
"""
Build RU-only / EU-only / Common prefix counts per Maven-tag category (tag),
based on hits_summary_region.csv.

Input per tag:
- data/dicts/mvnrepo/<tag>/hits_summary_region.csv
  columns: region,prefix,apps_with_prefix,(optional) in_which_APKs

Output:
- results/mvnrepo_dict/venn_counts_by_tag.csv

Usage:
  python3 scripts/mvnrepo_venn_summary.py --tags ads analytics payments network
  python3 scripts/mvnrepo_venn_summary.py --all
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
IN_BASE = BASE / "data" / "dicts" / "mvnrepo"
OUT_DIR = BASE / "results" / "mvnrepo_dict"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "venn_counts_by_tag.csv"

DEFAULT_TAGS = ["ads", "analytics", "payments", "network"]


def read_tag(tag: str) -> pd.DataFrame:
    p = IN_BASE / tag / "hits_summary_region.csv"
    if not p.exists():
        raise SystemExit(f"Missing: {p}")
    df = pd.read_csv(p)
    # normalize
    df["region"] = df["region"].astype(str).str.strip().str.lower()
    df["prefix"] = df["prefix"].astype(str).str.strip()
    df = df[df["prefix"] != ""]
    # only keep rows with apps_with_prefix > 0 if column exists
    if "apps_with_prefix" in df.columns:
        df = df[df["apps_with_prefix"].fillna(0).astype(int) > 0]
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", default=None, help="tags to include (e.g., ads analytics payments network)")
    ap.add_argument("--all", action="store_true", help="use default tags (ads analytics payments network)")
    args = ap.parse_args()

    tags = DEFAULT_TAGS if args.all or not args.tags else args.tags

    rows = []
    total_ru_only = 0
    total_eu_only = 0
    total_common = 0

    for tag in tags:
        df = read_tag(tag)

        ru = set(df[df["region"] == "ru"]["prefix"].tolist())
        eu = set(df[df["region"] == "eu"]["prefix"].tolist())

        common = ru & eu
        ru_only = ru - eu
        eu_only = eu - ru

        rows.append({
            "tag": tag,
            "ru_only_count": len(ru_only),
            "eu_only_count": len(eu_only),
            "common_count": len(common),
            "ru_only_prefixes": ";".join(sorted(ru_only)),
            "eu_only_prefixes": ";".join(sorted(eu_only)),
            "common_prefixes": ";".join(sorted(common)),
        })

        total_ru_only += len(ru_only)
        total_eu_only += len(eu_only)
        total_common += len(common)

    # add totals row
    rows.append({
        "tag": "TOTAL",
        "ru_only_count": total_ru_only,
        "eu_only_count": total_eu_only,
        "common_count": total_common,
        "ru_only_prefixes": "",
        "eu_only_prefixes": "",
        "common_prefixes": "",
    })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False)
    print("OK wrote:", OUT_CSV)


if __name__ == "__main__":
    main()
