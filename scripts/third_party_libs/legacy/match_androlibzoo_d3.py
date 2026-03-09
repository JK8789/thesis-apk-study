#!/usr/bin/env python3
"""
Depth-3 AndroLibZoo matching (recommended).

Uses only depth==3 prefixes to avoid denominator explosion and generic matches.

Inputs:
- results/prefixes/<SHA>_counts.csv
- results/baseline/apps_baseline.csv (includes package)
- data/androlibzoo/AndroLibZoo.lst (prefix list)

Outputs (results/libs_d3):
- libs_per_app_long.csv              (matched libs at depth 3)
- libs_match_stats.csv               (per app match stats at depth 3)
- unmatched_prefixes_top.csv         (top unmatched depth-3 prefixes per app)
- unmatched_region_top.csv           (top unmatched depth-3 prefixes per region)
- libs_summary_region.csv            (top matched libs per region)
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

APPS_BASELINE = BASE_DIR / "results" / "baseline" / "apps_baseline.csv"
ANDROLIBZOO_LST = BASE_DIR / "data" / "androlibzoo" / "AndroLibZoo.lst"
PREFIX_DIR = BASE_DIR / "results" / "prefixes"
OUT_DIR = BASE_DIR / "results" / "libs_d3"

D_MATCH = 3  # depth we match on
TOP_UNMATCHED_PER_APP = 200
TOP_UNMATCHED_PER_REGION = 300

IGNORE_PREFIXES = (
    "android.", "androidx.",
    "java.", "javax.",
    "kotlin.", "kotlinx.",
    "dalvik.", "sun.", "com.sun.",
    "junit.", "org.junit.",
    "org.jetbrains.",
)

def read_csv_any_delim(path: Path) -> list[dict]:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    delim = "\t" if "\t" in sample and "," not in sample else ","
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f, delimiter=delim))

def load_androlibzoo_prefixes(path: Path) -> set[str]:
    out = set()
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            p = line.strip()
            if not p or p.startswith("#"):
                continue
            out.add(p)
    return out

def is_ignored(prefix: str) -> bool:
    return any(prefix.startswith(p) for p in IGNORE_PREFIXES)

def package_roots(pkg: str) -> tuple[str, str]:
    pkg = (pkg or "").strip()
    parts = pkg.split(".")
    root2 = ".".join(parts[:2]) if len(parts) >= 2 else pkg
    return pkg, root2

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
    required = {"sha256","region","category","pair_id","app_name","apk_path","package"}
    missing = required - set(apps[0].keys())
    if missing:
        raise SystemExit(f"apps_baseline.csv missing columns: {sorted(missing)}")

    libs_long_rows = []
    stats_rows = []

    # region summaries
    region_lib_counter = defaultdict(Counter)          # region -> Counter(library_prefix) counted by apps
    region_unmatched_counter = defaultdict(Counter)    # region -> Counter(prefix) counted by apps

    # store top unmatched per app (avoid multi-million-row output)
    unmatched_top_rows = []

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

        pkg_full, pkg_root2 = package_roots(pkg)

        candidate = 0
        matched = 0
        unmatched = 0
        excluded_first_party = 0
        excluded_platform = 0

        app_matched = Counter()      # lib_prefix -> class_count sum
        app_unmatched = Counter()    # prefix -> class_count sum

        for r in prefix_rows:
            prefix = (r.get("prefix") or "").strip()
            if not prefix:
                continue

            d = int(r.get("depth") or (prefix.count(".") + 1))
            if d != D_MATCH:
                continue

            if is_ignored(prefix):
                excluded_platform += 1
                continue

            # exclude first-party (exact and subpackages)
            is_fp = False
            if pkg_full and (prefix == pkg_full or prefix.startswith(pkg_full + ".")):
                is_fp = True

            # optional root2 exclusion (conservative)
            if not is_fp and pkg_root2 and pkg_root2.count(".") == 1:
                if pkg_root2 not in {"com.google", "com.android", "org.telegram"}:
                    if prefix == pkg_root2 or prefix.startswith(pkg_root2 + "."):
                        is_fp = True

            if is_fp:
                excluded_first_party += 1
                continue

            candidate += 1
            cls_cnt = int(r.get("class_count") or 0)

            if prefix in lib_prefixes:
                matched += 1
                app_matched[prefix] += cls_cnt
            else:
                unmatched += 1
                app_unmatched[prefix] += cls_cnt

        # output matched libs per app
        for lib, cls_sum in app_matched.most_common():
            libs_long_rows.append({
                "sha256": sha,
                "region": region,
                "category": category,
                "pair_id": pair_id,
                "app_name": app_name,
                "package": pkg,
                "library_prefix": lib,
                "matched_class_count_sum": cls_sum,
            })
            region_lib_counter[region][lib] += 1

        # top unmatched per app (store only top N)
        for pref, cls_sum in app_unmatched.most_common(TOP_UNMATCHED_PER_APP):
            unmatched_top_rows.append({
                "sha256": sha,
                "region": region,
                "category": category,
                "pair_id": pair_id,
                "app_name": app_name,
                "package": pkg,
                "unmatched_prefix_d3": pref,
                "class_count_sum": cls_sum,
            })
            region_unmatched_counter[region][pref] += 1

        rate = (matched / candidate) if candidate else 0.0
        stats_rows.append({
            "sha256": sha,
            "region": region,
            "category": category,
            "pair_id": pair_id,
            "app_name": app_name,
            "package": pkg,
            "candidate_prefixes_d3": candidate,
            "matched_prefixes_d3": matched,
            "unmatched_prefixes_d3": unmatched,
            "match_rate_d3": f"{rate:.4f}",
            "excluded_platform_d3": excluded_platform,
            "excluded_first_party_d3": excluded_first_party,
            "unique_matched_libraries_d3": len(app_matched),
        })

    def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    # write outputs
    write_csv(
        OUT_DIR / "libs_per_app_long.csv",
        libs_long_rows,
        ["sha256","region","category","pair_id","app_name","package","library_prefix","matched_class_count_sum"],
    )

    write_csv(
        OUT_DIR / "libs_match_stats.csv",
        stats_rows,
        ["sha256","region","category","pair_id","app_name","package",
         "candidate_prefixes_d3","matched_prefixes_d3","unmatched_prefixes_d3","match_rate_d3",
         "excluded_platform_d3","excluded_first_party_d3","unique_matched_libraries_d3"],
    )

    write_csv(
        OUT_DIR / "unmatched_prefixes_top.csv",
        unmatched_top_rows,
        ["sha256","region","category","pair_id","app_name","package","unmatched_prefix_d3","class_count_sum"],
    )

    # region summaries
    reg_lib_rows = []
    for region, c in region_lib_counter.items():
        for lib, n_apps in c.most_common(300):
            reg_lib_rows.append({"region": region, "library_prefix": lib, "apps_with_library": n_apps})
    write_csv(OUT_DIR / "libs_summary_region.csv", reg_lib_rows, ["region","library_prefix","apps_with_library"])

    reg_un_rows = []
    for region, c in region_unmatched_counter.items():
        for pref, n_apps in c.most_common(TOP_UNMATCHED_PER_REGION):
            reg_un_rows.append({"region": region, "unmatched_prefix_d3": pref, "apps_with_prefix": n_apps})
    write_csv(OUT_DIR / "unmatched_region_top.csv", reg_un_rows, ["region","unmatched_prefix_d3","apps_with_prefix"])

    print("[OK] Wrote results to:", OUT_DIR)

if __name__ == "__main__":
    main()

