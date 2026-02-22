#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
APPS_CSV = BASE_DIR / "data" / "meta" / "apps.csv"
CLASSES_DIR = BASE_DIR / "results" / "classes"
ALZ_LIST = BASE_DIR / "data" / "androlibzoo" / "AndroLibZoo.lst"
OUT_DIR = BASE_DIR / "results" / "libs"

# Filter out super-common namespaces to reduce noise
IGNORE_PREFIXES = (
    "android.",
    "androidx.",
    "java.",
    "javax.",
    "kotlin.",
    "kotlinx.",
    "sun.",
    "org.jetbrains.",
)

@dataclass(frozen=True)
class AppRow:
    region: str
    category: str
    pair_id: str
    app_name: str
    apk_path: str
    sha256: str

def read_apps_csv(path: Path) -> List[AppRow]:
    out: List[AppRow] = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sha = (row.get("sha256") or "").strip().upper()
            if not sha:
                continue
            out.append(
                AppRow(
                    region=(row.get("region") or "").strip(),
                    category=(row.get("category") or "").strip(),
                    pair_id=(row.get("pair_id") or "").strip(),
                    app_name=(row.get("app_name") or "").strip(),
                    apk_path=(row.get("apk_path") or "").strip(),
                    sha256=sha,
                )
            )
    return out

def load_androlibzoo_prefixes(path: Path) -> List[str]:
    """
    AndroLibZoo.lst formats vary. We handle common patterns:
    - lines that contain a Java-like prefix (dots)
    - ignore empty/comment lines
    We store prefixes like 'com.facebook.' (ensure trailing dot for safe startswith checks).
    """
    prefixes: Set[str] = set()
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Heuristic: find the first token that looks like a dotted prefix
            parts = line.replace("\t", " ").split()
            cand = None
            for p in parts:
                if "." in p and not p.startswith(("http://", "https://")):
                    cand = p.strip().strip(",;")
                    break
            if not cand:
                continue

            # Normalize
            cand = cand.strip()
            # Remove trailing wildcards if any
            cand = cand.replace(".*", ".").replace("*", "")
            # Ensure dot at end so "com.foo" doesn't match "com.foobar"
            if not cand.endswith("."):
                cand = cand + "."
            prefixes.add(cand)

    # Sort longest-first so we match most-specific prefixes first
    return sorted(prefixes, key=len, reverse=True)

def load_classes_for_sha(sha: str) -> List[str]:
    p = CLASSES_DIR / f"{sha}.txt"
    if not p.is_file():
        return []
    lines = []
    with p.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            # Convert possible "Lcom/foo/Bar;" style to dotted if it ever appears
            s = s.strip("L;").replace("/", ".")
            lines.append(s)
    return lines

def match_prefixes(classes: Iterable[str], prefixes: List[str]) -> Dict[str, int]:
    """
    Count how many classes fall under each library prefix.
    """
    counts: Dict[str, int] = {}
    for c in classes:
        # Skip framework / standard libs
        if c.startswith(IGNORE_PREFIXES):
            continue

        # Find first matching library prefix (most specific due to sort)
        for pref in prefixes:
            if c.startswith(pref):
                counts[pref] = counts.get(pref, 0) + 1
                break
    return counts

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    apps = read_apps_csv(APPS_CSV)
    prefixes = load_androlibzoo_prefixes(ALZ_LIST)

    out_csv = OUT_DIR / "app_libs.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "sha256",
            "region",
            "category",
            "pair_id",
            "app_name",
            "library_prefix",
            "class_hits",
        ])

        for a in apps:
            classes = load_classes_for_sha(a.sha256)
            counts = match_prefixes(classes, prefixes)

            # If nothing matches, still keep a row? Usually better to keep none.
            for pref, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
                w.writerow([a.sha256, a.region, a.category, a.pair_id, a.app_name, pref, n])

    print(f"Wrote {out_csv}")

if __name__ == "__main__":
    main()

