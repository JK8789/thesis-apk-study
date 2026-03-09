#!/usr/bin/env python3
"""
Longest-prefix library matching using AndroLibZoo (depth 3..6).

Script: python3 scripts/match_androlibzoo_longest.py

Why:
- Depth=3 is a good baseline, but some ecosystems hide functional modules deeper
  (e.g., com.vk.superapp.miniappsads).
- This script matches libraries at depths 3..6 and then keeps only the most
  specific (longest) non-overlapping matches per app.

Inputs:
- results/prefixes/<SHA>_counts.csv
- results/baseline/apps_baseline.csv  (must contain: sha256, region, category, pair_id, app_name, package)
- data/androlibzoo/AndroLibZoo.lst     (one prefix per line)

Outputs (results/libs_longest):
- libs_per_app_long.csv          (app, kept_library_prefix, depth, class_count_sum)
- libs_match_stats.csv           (per app stats for candidate/matched/kept)
- libs_summary_region.csv        (top kept libraries per region)
- pairs_libs_diff.csv            (pairwise RU-only vs EU-only kept libs)
- keyword_deep_hits.csv          (depth 4..6 prefixes containing ads/pay/tracker/etc, matched or not)

 
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

APPS_BASELINE = BASE_DIR / "results" / "baseline" / "apps_baseline.csv"
ANDROLIBZOO_LST = BASE_DIR / "data" / "androlibzoo" / "AndroLibZoo.lst"
PREFIX_DIR = BASE_DIR / "results" / "prefixes"
OUT_DIR = BASE_DIR / "results" / "libs_longest"

DEPTH_MIN = 3
DEPTH_MAX = 6

IGNORE_PREFIXES = (
    "android.", "androidx.",
    "java.", "javax.",
    "kotlin.", "kotlinx.",
    "dalvik.", "sun.", "com.sun.",
    "junit.", "org.junit.",
    "org.jetbrains.",
)

# Optional keyword report for deeper prefixes (helps spot things like ...ads, ...pay)
KEYWORDS = ("ads", "ad", "pay", "payment", "tracker", "analytics", "push", "crash", "fraud", "anti", "risk")

# Conservative exceptions for "root2" exclusion (avoid nuking huge ecosystems)
ROOT2_EXCLUDE_EXCEPTIONS = {"com.google", "com.android", "org.telegram"}


def read_csv_any_delim(path: Path) -> list[dict]:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    delim = "\t" if "\t" in sample and "," not in sample else ","
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f, delimiter=delim))


def load_androlibzoo_prefixes(path: Path) -> set[str]:
    out: set[str] = set()
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            p = line.strip()
            if not p or p.startswith("#"):
                continue
            out.add(p)
    return out


def is_ignored(prefix: str) -> bool:
    return any(prefix.startswith(p) for p in IGNORE_PREFIXES)


def prefix_depth(prefix: str) -> int:
    return prefix.count(".") + 1


def package_roots(pkg: str) -> tuple[str, str]:
    pkg = (pkg or "").strip()
    parts = pkg.split(".")
    root2 = ".".join(parts[:2]) if len(parts) >= 2 else pkg
    return pkg, root2


def is_first_party(prefix: str, pkg_full: str, pkg_root2: str) -> bool:
    # exact package or subpackage
    if pkg_full:
        if prefix == pkg_full or prefix.startswith(pkg_full + "."):
            return True

    # optional root2 exclusion (conservative)
    if pkg_root2 and pkg_root2.count(".") == 1 and pkg_root2 not in ROOT2_EXCLUDE_EXCEPTIONS:
        if prefix == pkg_root2 or prefix.startswith(pkg_root2 + "."):
            return True

    return False


def keep_longest_non_overlapping(matched_prefixes: list[str]) -> list[str]:
    """
    Keep the most specific prefixes only.
    If we already kept 'com.vk.superapp.miniappsads', we will drop 'com.vk.superapp'.
    """
    kept: list[str] = []
    kept_set: set[str] = set()

    # sort by depth desc, then lexicographically for determinism
    for p in sorted(matched_prefixes, key=lambda x: (-prefix_depth(x), x)):
        # If any already-kept prefix is a descendant of p, then p is too generic
        # Example: kept has com.vk.superapp.miniappsads, candidate p is com.vk.superapp -> skip
        if any(k == p or k.startswith(p + ".") for k in kept_set):
            continue
        kept.append(p)
        kept_set.add(p)

    # return in stable order (depth desc, name)
    return sorted(kept, key=lambda x: (-prefix_depth(x), x))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


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
    required = {"sha256", "region", "category", "pair_id", "app_name", "package"}
    missing = required - set(apps[0].keys())
    if missing:
        raise SystemExit(f"apps_baseline.csv missing columns: {sorted(missing)}")

    libs_long_rows: list[dict] = []
    stats_rows: list[dict] = []
    keyword_rows: list[dict] = []

    region_counter = defaultdict(Counter)  # region -> Counter(lib_prefix)
    per_app_kept = {}  # (pair_id, region) -> set(kept libs) for pairs_diff

    for app in apps:
        sha = (app.get("sha256") or "").strip().upper()
        region = (app.get("region") or "").strip()
        category = (app.get("category") or "").strip()
        pair_id = (app.get("pair_id") or "").strip()
        app_name = (app.get("app_name") or "").strip()
        pkg = (app.get("package") or "").strip()

        counts_path = PREFIX_DIR / f"{sha}_counts.csv"
        if not counts_path.exists():
            raise SystemExit(f"Missing prefix counts for {sha}: {counts_path}")

        rows = read_csv_any_delim(counts_path)
        pkg_full, pkg_root2 = package_roots(pkg)

        candidate = 0
        excluded_platform = 0
        excluded_first_party = 0

        matched_prefixes: list[str] = []
        matched_classsum = Counter()   # prefix -> total classes contributing (here it is one row per prefix anyway)

        # collect keyword deep hits too (depth 4..6, external)
        for r in rows:
            prefix = (r.get("prefix") or "").strip()
            if not prefix:
                continue

            d = int(r.get("depth") or prefix_depth(prefix))
            if d < DEPTH_MIN or d > DEPTH_MAX:
                continue

            if is_ignored(prefix):
                excluded_platform += 1
                continue

            if is_first_party(prefix, pkg_full, pkg_root2):
                excluded_first_party += 1
                continue

            candidate += 1
            cls_cnt = int(r.get("class_count") or 0)

            # keyword report for deeper prefixes (helps manual taxonomy)
            if d >= 4:
                low = prefix.lower()
                if any(k in low for k in KEYWORDS):
                    keyword_rows.append({
                        "sha256": sha,
                        "region": region,
                        "category": category,
                        "pair_id": pair_id,
                        "app_name": app_name,
                        "package": pkg,
                        "prefix": prefix,
                        "depth": d,
                        "class_count": cls_cnt,
                        "in_androlibzoo": int(prefix in lib_prefixes),
                    })

            if prefix in lib_prefixes:
                matched_prefixes.append(prefix)
                matched_classsum[prefix] += cls_cnt

        kept = keep_longest_non_overlapping(matched_prefixes)

        # output per app kept libs
        kept_set = set(kept)
        for lib in kept:
            libs_long_rows.append({
                "sha256": sha,
                "region": region,
                "category": category,
                "pair_id": pair_id,
                "app_name": app_name,
                "package": pkg,
                "library_prefix": lib,
                "depth": prefix_depth(lib),
                "class_count": matched_classsum.get(lib, 0),
            })
            region_counter[region][lib] += 1

        per_app_kept[(pair_id, region)] = kept_set

        matched = len(matched_prefixes)
        kept_n = len(kept)
        stats_rows.append({
            "sha256": sha,
            "region": region,
            "category": category,
            "pair_id": pair_id,
            "app_name": app_name,
            "package": pkg,
            "candidate_prefixes_d3_6": candidate,
            "matched_prefixes_d3_6": matched,
            "kept_longest_matches": kept_n,
            "excluded_platform_d3_6": excluded_platform,
            "excluded_first_party_d3_6": excluded_first_party,
        })

    # Write main outputs
    write_csv(
        OUT_DIR / "libs_per_app_long.csv",
        libs_long_rows,
        ["sha256", "region", "category", "pair_id", "app_name", "package", "library_prefix", "depth", "class_count"],
    )
    write_csv(
        OUT_DIR / "libs_match_stats.csv",
        stats_rows,
        ["sha256", "region", "category", "pair_id", "app_name", "package",
         "candidate_prefixes_d3_6", "matched_prefixes_d3_6", "kept_longest_matches",
         "excluded_platform_d3_6", "excluded_first_party_d3_6"],
    )

    # Region summary
    summary_rows = []
    for region, c in region_counter.items():
        for lib, n_apps in c.most_common(400):
            summary_rows.append({"region": region, "library_prefix": lib, "apps_with_library": n_apps})
    write_csv(OUT_DIR / "libs_summary_region.csv", summary_rows, ["region", "library_prefix", "apps_with_library"])

    # Pairwise diff
    pair_rows = []
    pair_ids = sorted(set(pid for (pid, _) in per_app_kept.keys()))
    for pid in pair_ids:
        ru = per_app_kept.get((pid, "ru"))
        eu = per_app_kept.get((pid, "eu"))
        if ru is None or eu is None:
            continue
        pair_rows.append({
            "pair_id": pid,
            "ru_only": len(ru - eu),
            "eu_only": len(eu - ru),
            "intersection": len(ru & eu),
            "ru_only_libs": ";".join(sorted(list(ru - eu))[:80]),
            "eu_only_libs": ";".join(sorted(list(eu - ru))[:80]),
        })
    write_csv(
        OUT_DIR / "pairs_libs_diff.csv",
        pair_rows,
        ["pair_id", "ru_only", "eu_only", "intersection", "ru_only_libs", "eu_only_libs"],
    )

    # Keyword deep hits
    write_csv(
        OUT_DIR / "keyword_deep_hits.csv",
        keyword_rows,
        ["sha256", "region", "category", "pair_id", "app_name", "package",
         "prefix", "depth", "class_count", "in_androlibzoo"],
    )

    print("[OK] Wrote results to:", OUT_DIR)
    print(" - libs_per_app_long.csv")
    print(" - libs_match_stats.csv")
    print(" - libs_summary_region.csv")
    print(" - pairs_libs_diff.csv")
    print(" - keyword_deep_hits.csv")


if __name__ == "__main__":
    main()

