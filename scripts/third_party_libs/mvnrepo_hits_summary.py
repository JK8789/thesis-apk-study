#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

DICT_DIR = BASE / "data" / "dicts" / "mvnrepo"
OUT = DICT_DIR / "summary.csv"

# change tags here if needed
TAGS = ["ads", "analytics", "payments", "network"]


def load_tag(tag: str) -> pd.DataFrame:
    p = DICT_DIR / tag / "hits_per_app.csv"
    df = pd.read_csv(p)

    df = df[[
        "sha256",
        "region",
        "category",
        "pair_id",
        "app_name",
        "package",
        "hit_count",
    ]].copy()

    df = df.rename(columns={"hit_count": f"{tag}_hit_count"})
    return df


def main():
    # base order from first tag
    base = load_tag(TAGS[0])

    # merge others
    for tag in TAGS[1:]:
        df = load_tag(tag)

        base = base.merge(
            df[["sha256", f"{tag}_hit_count"]],
            on="sha256",
            how="left",
        )

    # fill missing
    for tag in TAGS:
        c = f"{tag}_hit_count"
        if c in base.columns:
            base[c] = base[c].fillna(0).astype(int)

    # total
    base["total_hit_count"] = base[[f"{t}_hit_count" for t in TAGS]].sum(axis=1)

    base.to_csv(OUT, index=False)
    print("OK wrote", OUT)


if __name__ == "__main__":
    main()
