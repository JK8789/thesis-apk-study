#!/usr/bin/env python3
"""
Build package-prefix inventories from extracted classes.

Inputs:
- results/classes/<SHA256>.txt  (one class per line, dot notation)

Outputs:
- results/prefixes/<SHA256>.txt             unique prefixes (2..6 segments)
- results/prefixes/<SHA256>_counts.csv      prefix,class_count,depth
- results/prefixes/prefix_stats.csv         per-app summary stats + heuristics

Why:
- Library matching works best on package prefixes, not full class names.
- Keeping counts lets us estimate confidence, detect obfuscation, and quantify "unknown surface".
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parents[1]
CLASSES_DIR = BASE_DIR / "results" / "classes"
OUT_DIR = BASE_DIR / "results" / "prefixes"

MIN_DEPTH = 2
MAX_DEPTH = 6

# Filter out platform / language / common test namespaces (not useful for 3rd-party library matching)
IGNORE_PREFIXES = (
    "android.", "androidx.",
    "java.", "javax.",
    "kotlin.", "kotlinx.",
    "dalvik.", "sun.", "com.sun.",
    "junit.", "org.junit.",
    "org.jetbrains.",
)

def is_ignored_class(cls: str) -> bool:
    return any(cls.startswith(p) for p in IGNORE_PREFIXES)

def iter_prefixes(cls: str, min_depth: int = MIN_DEPTH, max_depth: int = MAX_DEPTH) -> Iterable[str]:
    parts = cls.split(".")
    if len(parts) < min_depth:
        return []
    lim = min(max_depth, len(parts))
    return (".".join(parts[:d]) for d in range(min_depth, lim + 1))

def depth(prefix: str) -> int:
    return prefix.count(".") + 1

def looks_obfuscated_token(tok: str) -> bool:
    # crude but effective: single-letter or two-letter tokens are common in obfuscation
    return len(tok) <= 2

def obfuscation_score(prefixes_at_depth3: Counter) -> float:
    """
    % of depth-3 prefixes whose tokens look obfuscated (e.g., a.b.c / x.y.z style).
    """
    if not prefixes_at_depth3:
        return 0.0
    total = sum(prefixes_at_depth3.values())
    obf = 0
    for p, cnt in prefixes_at_depth3.items():
        toks = p.split(".")
        if len(toks) == 3 and all(looks_obfuscated_token(t) for t in toks):
            obf += cnt
    return obf / total if total else 0.0

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    class_files = sorted(CLASSES_DIR.glob("*.txt"))
    if not class_files:
        raise SystemExit(f"ERROR: no class files found in {CLASSES_DIR}")

    stats_rows = []
    for f in class_files:
        sha = f.stem.upper()
        print(f"[PREFIX] {sha}")

        classes = []
        with f.open("r", encoding="utf-8", errors="ignore") as r:
            for line in r:
                c = line.strip()
                if not c:
                    continue
                if is_ignored_class(c):
                    continue
                classes.append(c)

        # Count how many classes contribute to each prefix
        prefix_counts: Counter[str] = Counter()
        prefix_counts_by_depth: dict[int, Counter[str]] = defaultdict(Counter)

        for c in classes:
            for p in iter_prefixes(c):
                prefix_counts[p] += 1
                prefix_counts_by_depth[depth(p)][p] += 1

        # Write unique prefixes list
        out_txt = OUT_DIR / f"{sha}.txt"
        tmp_txt = out_txt.with_suffix(".txt.tmp")
        with tmp_txt.open("w", encoding="utf-8") as w:
            for p in sorted(prefix_counts.keys()):
                w.write(p + "\n")
        tmp_txt.replace(out_txt)

        # Write counts CSV
        out_counts = OUT_DIR / f"{sha}_counts.csv"
        tmp_csv = out_counts.with_suffix(".csv.tmp")
        with tmp_csv.open("w", encoding="utf-8", newline="") as w:
            wr = csv.writer(w)
            wr.writerow(["sha256", "prefix", "depth", "class_count"])
            for p, cnt in prefix_counts.most_common():
                wr.writerow([sha, p, depth(p), cnt])
        tmp_csv.replace(out_counts)

        # Heuristic: likely first-party candidate prefix (depth 3 preferred, else depth 2)
        top_d3 = prefix_counts_by_depth.get(3, Counter()).most_common(1)
        top_d2 = prefix_counts_by_depth.get(2, Counter()).most_common(1)
        first_party_guess = top_d3[0][0] if top_d3 else (top_d2[0][0] if top_d2 else "")

        # Obfuscation hint based on depth-3 distribution
        obf = obfuscation_score(prefix_counts_by_depth.get(3, Counter()))

        stats_rows.append({
            "sha256": sha,
            "classes_nonplatform": len(classes),
            "unique_prefixes_total": len(prefix_counts),
            "unique_prefixes_d2": len(prefix_counts_by_depth.get(2, Counter())),
            "unique_prefixes_d3": len(prefix_counts_by_depth.get(3, Counter())),
            "unique_prefixes_d4": len(prefix_counts_by_depth.get(4, Counter())),
            "first_party_guess_prefix": first_party_guess,
            "obfuscation_score_d3": f"{obf:.4f}",
            "top_prefix_d3": top_d3[0][0] if top_d3 else "",
            "top_prefix_d3_class_count": top_d3[0][1] if top_d3 else 0,
        })

    # Write global stats file
    stats_csv = OUT_DIR / "prefix_stats.csv"
    with stats_csv.open("w", encoding="utf-8", newline="") as w:
        fieldnames = list(stats_rows[0].keys()) if stats_rows else []
        wr = csv.DictWriter(w, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(stats_rows)

    print(f"Done. wrote {len(class_files)} apps into {OUT_DIR}")
    print(f"Stats: {stats_csv}")

if __name__ == "__main__":
    main()

