#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
APPS = BASE / "results" / "baseline" / "apps_baseline.csv"
LIBS = BASE / "results" / "libs_longest" / "libs_per_app_long.csv"
DEEP = BASE / "results" / "libs_longest" / "keyword_deep_hits.csv"
TAX = BASE / "data" / "meta" / "library_taxonomy_auto.csv"

OUT = BASE / "results" / "libs_longest" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)

def main():
    apps = pd.read_csv(APPS)[["sha256","region","category","pair_id","app_name","package"]].copy()
    apps["sha256"] = apps["sha256"].str.upper()

    libs = pd.read_csv(LIBS)
    libs["sha256"] = libs["sha256"].str.upper()
    libs = libs.rename(columns={"library_prefix":"prefix"})

    deep = pd.read_csv(DEEP)
    deep["sha256"] = deep["sha256"].str.upper()
    deep = deep[["sha256","prefix","depth","class_count","in_androlibzoo"]].copy()

    tax = pd.read_csv(TAX)
    # tax: prefix -> type_auto
    tax = tax.drop_duplicates("prefix")

    # Build per-app prefix list from (matched libs + deep hits)
    allp = pd.concat([
        libs[["sha256","prefix"]],
        deep[["sha256","prefix"]],
    ], ignore_index=True).drop_duplicates()

    # attach types
    allp = allp.merge(tax, on="prefix", how="left")
    allp["type_auto"] = allp["type_auto"].fillna("other")

    # count types per app
    per_app = (allp.groupby(["sha256","type_auto"])["prefix"]
                  .nunique()
                  .reset_index(name="n_prefixes"))
    per_app_w = per_app.pivot(index="sha256", columns="type_auto", values="n_prefixes").fillna(0).reset_index()

    # attach metadata
    per_app_w = per_app_w.merge(apps, on="sha256", how="left")

    # write per-app table
    per_app_out = OUT / "library_types_per_app.csv"
    per_app_w.to_csv(per_app_out, index=False)

    # RU vs EU summary (mean/median)
    numeric_cols = [c for c in per_app_w.columns if c not in {"sha256","region","category","pair_id","app_name","package"}]
    summary = (per_app_w.groupby("region")[numeric_cols]
                 .agg(["mean","median"])
                 .reset_index())
    summary_out = OUT / "library_types_region_summary.csv"
    summary.to_csv(summary_out, index=False)

    # pairwise deltas (RU - EU) for each type
    rows = []
    for pid, g in per_app_w.groupby("pair_id"):
        ru = g[g["region"]=="ru"]
        eu = g[g["region"]=="eu"]
        if len(ru)!=1 or len(eu)!=1:
            continue
        ru = ru.iloc[0]
        eu = eu.iloc[0]
        row = {"pair_id": pid}
        for c in numeric_cols:
            row[f"{c}_ru_minus_eu"] = float(ru[c]) - float(eu[c])
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT / "library_types_pair_deltas.csv", index=False)

    print("OK wrote:")
    print(" -", per_app_out)
    print(" -", summary_out)
    print(" -", OUT / "library_types_pair_deltas.csv")

if __name__ == "__main__":
    main()

