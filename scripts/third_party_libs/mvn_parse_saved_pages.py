#!/usr/bin/env python3
"""
Parse locally-saved mvnrepository tag pages (HTML) to extract Maven coordinates.

Robust strategy:
- Find <a href="/artifact/<groupId>/<artifactId>"> links
- Extract groupId/artifactId from the href path (works even if UI text changes)
- Try to find "NN usages" near the link (best-effort)

Input:
  data/mvn_pages/<tag>/*.html   (saved via "Webpage, complete" is OK)

Outputs:
  data/dicts/mvnrepo/<tag>/coords_ranked.csv   groupId,artifactId,usages,page
  data/dicts/mvnrepo/<tag>/prefix_candidates.txt
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import List, Tuple, Set

from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
PAGES_BASE = BASE / "data" / "mvn_pages"
OUT_BASE = BASE / "data" / "dicts" / "mvnrepo"

USAGES_RE = re.compile(r"(\d+)\s+usages?")

def artifact_to_segments(artifact_id: str) -> List[str]:
    # core-widgets -> ["core","widgets"]
    parts = re.split(r"[-_]", artifact_id)
    return [p for p in parts if p]

def coord_to_candidates(group_id: str, artifact_id: str) -> Set[str]:
    g = group_id.strip()
    a = artifact_id.strip()
    segs = artifact_to_segments(a)

    cand: Set[str] = set()
    cand.add(g)
    if segs:
        cand.add(g + "." + ".".join(segs))
        cand.add(g + "." + segs[-1])

    # keep only reasonably specific roots (>= 3 segments)
    cand = {x for x in cand if x.count(".") >= 2}
    return cand

def extract_usages_near(node) -> int:
    """
    Best-effort: climb a few parents to find "NN usages".
    If not found, return 0.
    """
    cur = node
    for _ in range(6):
        if cur is None:
            break
        txt = cur.get_text(" ", strip=True)
        m = USAGES_RE.search(txt)
        if m:
            return int(m.group(1))
        cur = cur.parent
    return 0

def parse_one_html(html_path: Path) -> List[Tuple[str, str, int]]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "lxml")

    out: List[Tuple[str, str, int]] = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # We want href like: /artifact/com.yandex.pay/core-widgets
        if not href.startswith("/artifact/"):
            continue

        parts = href.split("/")
        # ["", "artifact", "<groupId>", "<artifactId>", ...]
        if len(parts) < 4:
            continue

        group_id = parts[2].strip()
        artifact_id = parts[3].strip()

        if not group_id or not artifact_id or "." not in group_id:
            continue

        key = (group_id, artifact_id)
        if key in seen:
            continue
        seen.add(key)

        usages = extract_usages_near(a)
        out.append((group_id, artifact_id, usages))

    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", help="payments / ads / analytics (folder under data/mvn_pages/)")
    args = ap.parse_args()

    in_dir = PAGES_BASE / args.tag
    if not in_dir.exists():
        raise SystemExit(f"Missing folder: {in_dir}. Save HTML pages there first.")

    html_files = sorted(in_dir.glob("*.html"))
    if not html_files:
        raise SystemExit(f"No .html files found in {in_dir}")

    out_dir = OUT_BASE / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    candidates: Set[str] = set()

    total_found = 0
    for f in html_files:
        page_name = f.stem
        parsed = parse_one_html(f)
        total_found += len(parsed)
        print(f"[PARSE] {f.name}: {len(parsed)} coords")

        for g, art, usages in parsed:
            rows.append({"groupId": g, "artifactId": art, "usages": usages, "page": page_name})
            candidates |= coord_to_candidates(g, art)

    coords_csv = out_dir / "coords_ranked.csv"
    with coords_csv.open("w", encoding="utf-8", newline="") as w:
        writer = csv.DictWriter(w, fieldnames=["groupId", "artifactId", "usages", "page"])
        writer.writeheader()
        writer.writerows(rows)

    cand_txt = out_dir / "prefix_candidates.txt"
    cand_txt.write_text("\n".join(sorted(candidates)) + "\n", encoding="utf-8")

    print("[OK] Wrote:")
    print(" -", coords_csv)
    print(" -", cand_txt)
    print(f"[STATS] pages={len(html_files)} coords_total={len(rows)} candidates={len(candidates)}")

    if total_found == 0:
        print("[WARN] Parsed 0 artifacts. Your saved HTML might be a bot-block/consent page.")
        print("       Quick check: run `grep -R \"/artifact/\" -n data/mvn_pages/{tag}/*.html | head`")

if __name__ == "__main__":
    main()
