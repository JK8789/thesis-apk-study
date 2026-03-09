#!/usr/bin/env python3
"""
Step 1+2:
1) Scrape mvnrepository.com/tags/<tag>?p=<n> and extract Maven coordinates (groupId, artifactId)
2) Generate candidate Java package roots from those coordinates

Outputs in data/dicts/mvn/<tag>/:
- coords.csv                groupId,artifactId
- prefix_candidates.txt     candidate package roots (one per line)

Usage:
  python3 scripts/mvn_scrape_and_candidates.py payments --pages 10
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
OUT_BASE = BASE / "data" / "dicts" / "mvn"

MVN_TAG_BASE = "https://mvnrepository.com/tags"

@dataclass(frozen=True)
class MavenCoord:
    group_id: str
    artifact_id: str

COORD_RE = re.compile(r"^([a-zA-Z0-9_.-]+)\s*»\s*([a-zA-Z0-9_.-]+)$")

def scrape_tag_page(tag: str, page: int, session: requests.Session) -> List[MavenCoord]:
    url = f"{MVN_TAG_BASE}/{tag}?p={page}"
    r = session.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    coords: List[MavenCoord] = []
    for a in soup.find_all("a"):
        txt = (a.get_text(" ", strip=True) or "").strip()
        m = COORD_RE.match(txt)
        if not m:
            continue
        g, art = m.group(1), m.group(2)
        if "." not in g:
            continue
        coords.append(MavenCoord(g, art))

    # de-dup per page
    return list(dict.fromkeys(coords))

def scrape_tag(tag: str, pages: int, sleep_s: float) -> List[MavenCoord]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "thesis-apk-study/1.0 (academic research)"
    })

    allc: List[MavenCoord] = []
    for p in range(1, pages + 1):
        allc.extend(scrape_tag_page(tag, p, session))
        time.sleep(sleep_s)

    # de-dup across all pages
    return list(dict.fromkeys(allc))

def artifact_to_segments(artifact_id: str) -> List[str]:
    # core-widgets -> ["core","widgets"]
    parts = [x for x in re.split(r"[-_]", artifact_id) if x]
    clean: List[str] = []
    for x in parts:
        x2 = re.sub(r"[^a-zA-Z0-9]", "", x)
        if x2:
            clean.append(x2)
    return clean

def coord_to_candidates(c: MavenCoord) -> Set[str]:
    g = c.group_id.strip()
    art = c.artifact_id.strip()
    segs = artifact_to_segments(art)

    cand: Set[str] = set()

    # Candidate A: groupId itself
    cand.add(g)

    # Candidate B: groupId + dotted artifact segments (com.yandex.pay.core.widgets)
    if segs:
        cand.add(g + "." + ".".join(segs))

    # Candidate C: groupId + last segment only (often functional)
    if segs:
        cand.add(g + "." + segs[-1])

    # Special: common Google Ads mapping
    if g == "com.google.android.gms" and segs and "ads" in [s.lower() for s in segs]:
        cand.add("com.google.android.gms.ads")

    # keep candidates with at least 3 segments
    cand = {x for x in cand if x.count(".") >= 2}
    return cand

def write_coords_csv(path: Path, coords: List[MavenCoord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["groupId", "artifactId"])
        for c in coords:
            w.writerow([c.group_id, c.artifact_id])

def write_lines(path: Path, lines: List[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for x in lines:
            f.write(x + "\n")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", help="e.g. payments, ads, analytics")
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--sleep", type=float, default=0.8)
    args = ap.parse_args()

    out_dir = OUT_BASE / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)

    coords = scrape_tag(args.tag, args.pages, args.sleep)
    write_coords_csv(out_dir / "coords.csv", coords)

    candidates: Set[str] = set()
    for c in coords:
        candidates |= coord_to_candidates(c)

    write_lines(out_dir / "prefix_candidates.txt", sorted(candidates))

    print("[OK] Wrote:")
    print(" -", out_dir / "coords.csv")
    print(" -", out_dir / "prefix_candidates.txt")
    print(f"[STATS] coords={len(coords)} candidates={len(candidates)}")

if __name__ == "__main__":
    main()
