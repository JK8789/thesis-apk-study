#!/usr/bin/env python3
"""
Build per-app counts AND per-type prefix lists (semicolon-separated) for library "types"
(ads, analytics, payments, etc.), combining:

1) results/libs_longest/libs_per_app_long.csv
   - prefixes matched via AndroLibZoo longest-prefix matching

2) results/libs_longest/keyword_deep_hits_typed.csv
   - "deep" prefixes found via keyword heuristics, already labeled with a type
     (from label_keyword_deep_hits.py)

Type assignment rule (important):
- For deep hits, we trust the pre-labeled "type" column if present.
- For matched libs, we map via data/meta/library_taxonomy_auto.csv (prefix -> type_auto).
- If taxonomy has no entry, fallback to "other".

Output (ordered like baseline apps list):
- results/libs_longest/analysis/library_types_per_app_with_lists.csv

Ordering:
- Uses results/baseline/apps_baseline.csv (one row per app, stable ordering).
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

LIBS = BASE / "results" / "libs_longest" / "libs_per_app_long.csv"
DEEP_TYPED = BASE / "results" / "libs_longest" / "keyword_deep_hits_typed.csv"
TAX = BASE / "data" / "meta" / "library_taxonomy_auto.csv"
BASELINE = BASE / "results" / "baseline" / "apps_baseline.csv"

OUT_DIR = BASE / "results" / "libs_longest" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PER_APP = OUT_DIR / "library_types_per_app_with_lists.csv"

TYPES = ["ads", "analytics", "anti_fraud", "crash", "networking", "payments", "push", "other"]


def main() -> None:
    # Load inputs
    if not LIBS.exists():
        raise SystemExit(f"Missing {LIBS}")
    if not TAX.exists():
        raise SystemExit(f"Missing {TAX}")
    if not BASELINE.exists():
        raise SystemExit(f"Missing {BASELINE}")

    libs = pd.read_csv(LIBS)
    tax = pd.read_csv(TAX)
    baseline = pd.read_csv(BASELINE)

    # Optional deep hits file
    if DEEP_TYPED.exists():
        deep = pd.read_csv(DEEP_TYPED)
    else:
        deep = pd.DataFrame(columns=["sha256", "region", "category", "pair_id", "app_name", "package", "prefix", "type"])

    # Normalize
    libs = libs.rename(columns={"library_prefix": "prefix"})
    libs["prefix"] = libs["prefix"].astype(str)
    libs["sha256"] = libs["sha256"].astype(str).str.upper()

    tax["prefix"] = tax["prefix"].astype(str)
    tax["type_auto"] = tax["type_auto"].astype(str)

    baseline["sha256"] = baseline["sha256"].astype(str).str.upper()

    # Taxonomy map for matched libs
    tax_map = dict(zip(tax["prefix"], tax["type_auto"]))

    def map_type_from_tax(p: str) -> str:
        return tax_map.get(p, "other")

    # Assign types to AndroLibZoo matched prefixes via taxonomy
    libs["type_auto"] = libs["prefix"].map(map_type_from_tax)

    # Deep hits: trust column 'type' if present, else taxonomy fallback
    if "prefix" not in deep.columns:
        deep["prefix"] = ""
    deep["prefix"] = deep["prefix"].astype(str)
    deep["sha256"] = deep["sha256"].astype(str).str.upper()

    if "type" in deep.columns:
        deep["type_auto"] = deep["type"].astype(str)
    elif "type_auto" not in deep.columns:
        deep["type_auto"] = deep["prefix"].map(map_type_from_tax)

    # Keep only relevant columns and drop duplicates
    libs_use = libs[["sha256", "region", "category", "pair_id", "app_name", "package", "prefix", "type_auto"]].copy()

    deep_cols = ["sha256", "region", "category", "pair_id", "app_name", "package", "prefix", "type_auto"]
    # If deep is missing some metadata columns, create empty ones to keep schema stable
    for c in deep_cols:
        if c not in deep.columns:
            deep[c] = ""
    deep_use = deep[deep_cols].copy()

    combined = pd.concat([libs_use, deep_use], ignore_index=True)
    combined["type_auto"] = combined["type_auto"].fillna("other").astype(str)

    # Normalize unexpected types into "other"
    combined.loc[~combined["type_auto"].isin(TYPES), "type_auto"] = "other"

    # Remove duplicates per app/prefix/type
    combined = combined.drop_duplicates(subset=["sha256", "prefix", "type_auto"])

    # Aggregate per app: counts + lists per type
    rows = []
    for sha, g in combined.groupby("sha256", sort=False):
        # Get metadata (prefer non-empty values)
        def first_nonempty(col: str) -> str:
            vals = [v for v in g[col].astype(str).tolist() if v and v != "nan"]
            return vals[0] if vals else ""

        meta = {
            "sha256": sha,
            "region": first_nonempty("region"),
            "category": first_nonempty("category"),
            "pair_id": first_nonempty("pair_id"),
            "app_name": first_nonempty("app_name"),
            "package": first_nonempty("package"),
        }

        out = dict(meta)

        for t in TYPES:
            prefixes = sorted(g.loc[g["type_auto"] == t, "prefix"].dropna().astype(str).unique().tolist())
            out[t] = len(prefixes)
            out[f"{t}_list"] = ";".join(prefixes)

        rows.append(out)

    out_df = pd.DataFrame(rows)

    # Ensure all expected columns exist even if empty
    base_cols = ["sha256", "region", "category", "pair_id", "app_name", "package"]
    count_cols = TYPES
    list_cols = [f"{t}_list" for t in TYPES]
    for c in base_cols + count_cols + list_cols:
        if c not in out_df.columns:
            out_df[c] = "" if c.endswith("_list") or c in base_cols else 0

    out_df = out_df[base_cols + count_cols + list_cols]

    # ORDER output exactly like baseline (stable thesis dataset ordering)
    out_df = baseline[["sha256", "region", "category", "pair_id", "app_name", "package"]].merge(
        out_df, on="sha256", how="left", suffixes=("", "_y")
    )

    # If baseline has better metadata, keep baseline (drop duplicates from merge)
    for c in ["region", "category", "pair_id", "app_name", "package"]:
        if f"{c}_y" in out_df.columns:
            out_df.drop(columns=[f"{c}_y"], inplace=True)

    # Fill NA for counts/lists
    for t in TYPES:
        if t in out_df.columns:
            out_df[t] = out_df[t].fillna(0).astype(int)
        lc = f"{t}_list"
        if lc in out_df.columns:
            out_df[lc] = out_df[lc].fillna("").astype(str)

    out_df.to_csv(OUT_PER_APP, index=False)
    print("OK wrote (ordered):", OUT_PER_APP, "rows=", len(out_df))


if __name__ == "__main__":
    main()
