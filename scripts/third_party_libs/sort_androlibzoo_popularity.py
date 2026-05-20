#!/usr/bin/env python3

import os
import pandas as pd

# ----------------------------
# Resolve project root
# ----------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))

INPUT_FILE = os.path.join(BASE_DIR, "results/libs_longest/androlibzoo_summary_faster.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "results/libs_longest/androlibzoo_popularity_sorted.csv")

RU_TOTAL_APPS = 20
EU_TOTAL_APPS = 20


def main():
    df = pd.read_csv(INPUT_FILE)

    # safety
    for col in ["ru_app_count", "eu_app_count", "total_app_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # usage percentages
    df["ru_usage_percent"] = (df["ru_app_count"] / RU_TOTAL_APPS * 100).round(1)
    df["eu_usage_percent"] = (df["eu_app_count"] / EU_TOTAL_APPS * 100).round(1)

    # sort by popularity
    df = df.sort_values(
        by=["total_app_count", "ru_app_count", "eu_app_count", "library"],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)

    df.to_csv(OUTPUT_FILE, index=False)
    print("[OK] saved:", OUTPUT_FILE)
    print("[INFO] rows:", len(df))


if __name__ == "__main__":
    main()
