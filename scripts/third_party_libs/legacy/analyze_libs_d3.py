#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
LIBS_LONG = BASE / "results" / "libs_d3" / "libs_per_app_long.csv"
APPS = BASE / "results" / "baseline" / "apps_baseline.csv"

OUT = BASE / "results" / "libs_d3" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)

def main():
    libs = pd.read_csv(LIBS_LONG)
    apps = pd.read_csv(APPS)[["sha256","region","category","pair_id","app_name","package"]].copy()
    apps["sha256"] = apps["sha256"].str.upper()
    libs["sha256"] = libs["sha256"].str.upper()

    # Ensure one row per app-library
    df = libs.merge(apps, on=["sha256","region","category","pair_id","app_name","package"], how="left")

    # (A) How many apps in each region use each library?
    presence = (df.groupby(["region","library_prefix"])["sha256"]
                  .nunique()
                  .reset_index(name="apps_with_library"))

    # Pivot RU vs EU and compute diff
    piv = presence.pivot(index="library_prefix", columns="region", values="apps_with_library").fillna(0).reset_index()
    if "ru" not in piv.columns: piv["ru"] = 0
    if "eu" not in piv.columns: piv["eu"] = 0
    piv["ru_minus_eu"] = piv["ru"] - piv["eu"]
    piv["eu_minus_ru"] = piv["eu"] - piv["ru"]

    piv.sort_values("ru_minus_eu", ascending=False).to_csv(OUT / "libs_ru_more.csv", index=False)
    piv.sort_values("eu_minus_ru", ascending=False).to_csv(OUT / "libs_eu_more.csv", index=False)

    # (B) Category-level comparison (apps_with_library by region+category)
    cat_presence = (df.groupby(["region","category","library_prefix"])["sha256"]
                      .nunique()
                      .reset_index(name="apps_with_library"))
    cat_presence.to_csv(OUT / "libs_by_category_region.csv", index=False)

    # (C) Pairwise: libraries unique to RU vs EU per pair
    # First build set per app
    per_app = (df.groupby(["sha256","region","pair_id"])["library_prefix"]
                 .apply(set)
                 .reset_index())

    # Convert to pairwise rows
    rows = []
    for pid, g in per_app.groupby("pair_id"):
        ru = g[g["region"]=="ru"]["library_prefix"]
        eu = g[g["region"]=="eu"]["library_prefix"]
        if len(ru)!=1 or len(eu)!=1:
            continue
        ru_set = next(iter(ru))
        eu_set = next(iter(eu))
        rows.append({
            "pair_id": pid,
            "ru_only": len(ru_set - eu_set),
            "eu_only": len(eu_set - ru_set),
            "intersection": len(ru_set & eu_set),
            "ru_only_libs": ";".join(sorted(ru_set - eu_set)[:50]),
            "eu_only_libs": ";".join(sorted(eu_set - ru_set)[:50]),
        })
    pd.DataFrame(rows).to_csv(OUT / "pairs_libs_diff.csv", index=False)

    print("OK wrote:")
    for p in ["libs_ru_more.csv","libs_eu_more.csv","libs_by_category_region.csv","pairs_libs_diff.csv"]:
        print(" -", OUT / p)

if __name__ == "__main__":
    main()

