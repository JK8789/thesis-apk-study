#!/usr/bin/env python3
"""
Match app package prefixes against AndroLibZoo prefix list.

Inputs:
- results/prefixes/<SHA>_counts.csv      (prefix,class_count,depth)
- results/prefixes/<SHA>.txt             (unique prefixes, optional)
- results/baseline/apps_baseline.csv     (must contain sha256, region, category, pair_id, app_name, apk_path, package)
- data/androlibzoo/AndroLibZoo.lst       (one library package prefix per line)

Outputs (results/libs):
- libs_per_app_long.csv
- libs_match_stats.csv
- unmatched_prefixes_long.csv
- libs_summary_region.csv

Design notes:
- Uses REAL package name from apps_baseline.csv to exclude first-party prefixes.
- Longest-prefix match is approximated by matching exact prefixes (since prefixes file already contains multiple depths).
- Computes match rate and unknown surface.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

APPS_BASELINE = BASE_DIR / "results" / "baseline" / "apps_baseline.csv"
ANDROLIBZOO_LST = BASE_DIR / "data" / "androlibzoo" / "AndroLibZoo.lst"
PREFIX_DIR = BASE_DIR / "results" / "prefixes"
OUT_DIR = BASE_DIR / "results" / "libs"

OUT_LIBS_LONG = OUT_DIR / "libs_per_app_long.csv"
OUT_STATS = OUT_DIR / "libs_match_stats.csv"
OUT_UNMATCHED = OUT_DIR / "unmatched_prefixes_long.csv"
OUT_SUMMARY_REGION = OUT_DIR / "libs_summary_region.csv"

# Prefixes we generally do not consider "third-party libraries" for the thesis library layer
IGNORE_PREFIXES = (
    "android.", "androidx.",
    "java.", "javax.",
    "kotlin.", "kotlinx.",
    "dalvik.", "sun.", "com.sun.",
    "junit.", "org.junit.",
    "org.jetbrains.",
)

def load_androlibzoo_prefixes(path: Path) -> set[str]:
    prefixes = set()
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            p = line.strip()
            if not p or p.startswith("#"):
                continue
            prefixes.add(p)
    return prefixes

def is_ignored(prefix: str) -> bool:
    return any(prefix.startswith(p) for p in IGNORE_PREFIXES)

def package_roots(pkg: str) -> tuple[str, str]:
    """
    Returns (full_package, org_root_2segments).
    Example: 'ru.ozon.app' -> ('ru.ozon.app', 'ru.ozon')
    """
    pkg = (pkg or "").strip()
    parts = pkg.split(".")
    root2 = ".".join(parts[:2]) if len(parts) >= 2 else pkg
    return pkg, root2

def read_csv_any_delim(path: Path) -> list[dict]:
    """
    Your repo uses comma CSVs in results, but just in case.
    """
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    delim = "\t" if "\t" in sample and "," not in sample else ","
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        r = csv.DictReader(f, delimiter=delim)
        return list(r)

def main() -> None:
    if not APPS_BASELINE.exists():
        raise SystemExit(f"Missing {APPS_BASELINE}")
    if not ANDROLIBZOO_LST.exists():
        raise SystemExit(f"Missing {ANDROLIBZOO_LST}")
    if not PREFIX_DIR.exists():
        raise SystemExit(f"Missing {PREFIX_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    lib_prefixes = load_androlibzoo_prefixes(ANDROLIBZOO_LST)
    print(f"[INFO] Loaded AndroLibZoo prefixes: {len(lib_prefixes)}")

    apps = read_csv_any_delim(APPS_BASELINE)

    # Sanity check required columns
    required = {"sha256","region","category","pair_id","app_name","apk_path","package"}
    missing = required - set(apps[0].keys())
    if missing:
        raise SystemExit(f"apps_baseline.csv missing columns: {sorted(missing)}")

    libs_long_rows = []
    stats_rows = []
    unmatched_rows = []

    # For region summary
    region_lib_counter = defaultdict(Counter)  # region -> Counter(lib_prefix)

    for app in apps:
        sha = (app["sha256"] or "").strip().upper()
        region = (app["region"] or "").strip()
        category = (app["category"] or "").strip()
        pair_id = (app["pair_id"] or "").strip()
        app_name = (app["app_name"] or "").strip()
        pkg = (app["package"] or "").strip()

        counts_path = PREFIX_DIR / f"{sha}_counts.csv"
        if not counts_path.exists():
            raise SystemExit(f"Missing prefix counts for {sha}: {counts_path}")

        prefix_rows = read_csv_any_delim(counts_path)

        # Exclusion rules (first-party)
        pkg_full, pkg_root2 = package_roots(pkg)

        total_prefixes = 0
        excluded_first_party = 0
        excluded_platform = 0

        matched_prefixes = 0
        unmatched_prefixes = 0

        # per-app matched library counter (with class_count sum)
        app_matched = Counter()  # lib_prefix -> number of prefixes matched
        app_matched_classsum = Counter()  # lib_prefix -> total class_count from matched prefixes

        # Process each prefix candidate
        for r in prefix_rows:
            prefix = (r.get("prefix") or "").strip()
            if not prefix:
                continue

            total_prefixes += 1

            # Skip platform-like prefixes
            if is_ignored(prefix):
                excluded_platform += 1
                continue

            # Exclude first-party: exact package OR startswith exact package + '.'
            # Also optionally exclude org-root (2 segments). This can be too aggressive for "com.google" apps,
            # so we only use root2 if it's not overly generic.
            is_first_party = False
            if pkg_full:
                if prefix == pkg_full or prefix.startswith(pkg_full + "."):
                    is_first_party = True

            # Root2 exclusion: apply only if not extremely generic (heuristic)
            if not is_first_party and pkg_root2 and pkg_root2.count(".") == 1:
                # avoid excluding huge ecosystems like "com.google" by default
                if pkg_root2 not in {"com.google", "com.android", "org.telegram"}:
                    if prefix == pkg_root2 or prefix.startswith(pkg_root2 + "."):
                        is_first_party = True

            if is_first_party:
                excluded_first_party += 1
                continue

            # Now this prefix is "candidate third-party / external"
            if prefix in lib_prefixes:
                matched_prefixes += 1
                lib = prefix
                cls_cnt = int(r.get("class_count") or 0)
                d = int(r.get("depth") or (prefix.count(".")+1))

                app_matched[lib] += 1
                app_matched_classsum[lib] += cls_cnt
            else:
                unmatched_prefixes += 1
                # Store unmatched for later RU-specific SDK discovery
                unmatched_rows.append({
                    "sha256": sha,
                    "region": region,
                    "category": category,
                    "pair_id": pair_id,
                    "app_name": app_name,
                    "package": pkg,
                    "prefix": prefix,
                    "depth": r.get("depth") or (prefix.count(".")+1),
                    "class_count": r.get("class_count") or 0,
                })

        # Emit per-app matched rows
        for lib, n_pref in app_matched.most_common():
            libs_long_rows.append({
                "sha256": sha,
                "region": region,
                "category": category,
                "pair_id": pair_id,
                "app_name": app_name,
                "package": pkg,
                "library_prefix": lib,
                "matched_prefix_count": n_pref,
                "matched_class_count_sum": app_matched_classsum[lib],
            })
            region_lib_counter[region][lib] += 1

        # Per-app stats
        denom = max((total_prefixes - excluded_platform - excluded_first_party), 0)
        match_rate = (matched_prefixes / denom) if denom else 0.0

        stats_rows.append({
            "sha256": sha,
            "region": region,
            "category": category,
            "pair_id": pair_id,
            "app_name": app_name,
            "package": pkg,
            "prefixes_total": total_prefixes,
            "excluded_platform": excluded_platform,
            "excluded_first_party": excluded_first_party,
            "candidate_prefixes": denom,
            "matched_prefixes": matched_prefixes,
            "unmatched_prefixes": unmatched_prefixes,
            "match_rate": f"{match_rate:.4f}",
            "unique_matched_libraries": len(app_matched),
        })

    # Write outputs
    def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    write_csv(
        OUT_LIBS_LONG,
        libs_long_rows,
        ["sha256","region","category","pair_id","app_name","package","library_prefix","matched_prefix_count","matched_class_count_sum"],
    )
    write_csv(
        OUT_STATS,
        stats_rows,
        ["sha256","region","category","pair_id","app_name","package","prefixes_total","excluded_platform","excluded_first_party",
         "candidate_prefixes","matched_prefixes","unmatched_prefixes","match_rate","unique_matched_libraries"],
    )
    write_csv(
        OUT_UNMATCHED,
        unmatched_rows,
        ["sha256","region","category","pair_id","app_name","package","prefix","depth","class_count"],
    )

    # Region summary (top 200 per region)
    summary_rows = []
    for region, c in region_lib_counter.items():
        for lib, n_apps in c.most_common(200):
            summary_rows.append({
                "region": region,
                "library_prefix": lib,
                "apps_with_library": n_apps,
            })
    write_csv(OUT_SUMMARY_REGION, summary_rows, ["region","library_prefix","apps_with_library"])

    print("[OK] Wrote:")
    print(" -", OUT_LIBS_LONG)
    print(" -", OUT_STATS)
    print(" -", OUT_UNMATCHED)
    print(" -", OUT_SUMMARY_REGION)

if __name__ == "__main__":
    main()

