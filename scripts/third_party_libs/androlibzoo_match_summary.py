#!/usr/bin/env python3

import os
import csv
from collections import defaultdict

# ----------------------------
# Resolve project root
# ----------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))

ANDROLIBZOO_FILE = os.path.join(BASE_DIR, "data/androlibzoo/AndroLibZoo.lst")
PREFIX_DIR = os.path.join(BASE_DIR, "results/prefixes")
APPS_BASELINE = os.path.join(BASE_DIR, "results/baseline/apps_baseline.csv")

OUTPUT_FILE = os.path.join(BASE_DIR, "results/libs_longest/androlibzoo_summary.csv")


# ----------------------------
# Load AndroLibZoo prefixes
# ----------------------------
def load_androlibzoo():
    libs = set()

    with open(ANDROLIBZOO_FILE, "r", encoding="utf-8") as f:
        for line in f:
            lib = line.strip()
            if lib:
                libs.add(lib)

    print(f"[INFO] Loaded {len(libs)} AndroLibZoo libraries")
    return libs


# ----------------------------
# Load apps metadata
# ----------------------------
def load_apps():
    apps = {}

    with open(APPS_BASELINE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sha = row["sha256"]
            apps[sha] = {
                "region": row["region"],
                "app_name": row["app_name"],
                "category": row["category"],
                "pair_id": row["pair_id"],
            }

    print(f"[INFO] Loaded {len(apps)} apps metadata")
    return apps


# ----------------------------
# Match libraries per APK
# ----------------------------
def match_libraries(androlibs):

    lib_to_apps = defaultdict(set)

    files = [f for f in os.listdir(PREFIX_DIR) if f.endswith("_counts.csv")]

    print(f"[INFO] Found {len(files)} prefix files")

    for fname in files:
        path = os.path.join(PREFIX_DIR, fname)

        # extract sha256 from filename
        sha = fname.replace("_counts.csv", "")

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                prefix = row["prefix"]

                for lib in androlibs:
                    if prefix == lib or prefix.startswith(lib + "."):
                        lib_to_apps[lib].add(sha)

    print(f"[INFO] Matched {len(lib_to_apps)} libraries")
    return lib_to_apps


# ----------------------------
# Build summary
# ----------------------------
def build_summary(lib_to_apps, apps):

    rows = []

    for lib, sha_set in lib_to_apps.items():

        ru_apps = []
        eu_apps = []

        for sha in sha_set:
            if sha not in apps:
                continue

            meta = apps[sha]

            if meta["region"] == "ru":
                ru_apps.append(meta["app_name"])
            elif meta["region"] == "eu":
                eu_apps.append(meta["app_name"])

        ru_set = set(ru_apps)
        eu_set = set(eu_apps)

        if ru_set and not eu_set:
            region_type = "RU_only"
        elif eu_set and not ru_set:
            region_type = "EU_only"
        else:
            region_type = "Common"

        rows.append({
            "library": lib,
            "ru_app_count": len(ru_set),
            "eu_app_count": len(eu_set),
            "total_app_count": len(sha_set),
            "region_type": region_type,
            "ru_apps": ";".join(sorted(ru_set)),
            "eu_apps": ";".join(sorted(eu_set)),
        })

    return rows


# ----------------------------
# Save CSV
# ----------------------------
def save(rows):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "library",
            "ru_app_count",
            "eu_app_count",
            "total_app_count",
            "region_type",
            "ru_apps",
            "eu_apps"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Saved: {OUTPUT_FILE}")


# ----------------------------
# MAIN
# ----------------------------
def main():
    print("[1] Loading AndroLibZoo...")
    androlibs = load_androlibzoo()

    print("[2] Loading apps metadata...")
    apps = load_apps()

    print("[3] Matching libraries...")
    lib_to_apps = match_libraries(androlibs)

    print("[4] Building summary...")
    rows = build_summary(lib_to_apps, apps)

    print("[5] Saving results...")
    save(rows)

    print("[DONE]")


if __name__ == "__main__":
    main()
