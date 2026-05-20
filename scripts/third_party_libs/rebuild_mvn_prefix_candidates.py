#!/usr/bin/env python3

from __future__ import annotations
import csv
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parents[1]
MVN_DIR = BASE_DIR / "data" / "dicts" / "mvnrepo"

# tokens we DO NOT want as suffixes
IGNORE_TOKENS = {
    "android", "java", "sdk", "core", "api", "impl",
    "ktx", "common", "client", "server",
    "play", "services", "service",
    "mobile", "base"
}

def extract_suffix(artifact_id: str) -> str | None:
    artifact_id = artifact_id.lower().strip()
    parts = [p for p in artifact_id.replace("_", "-").split("-") if p]

    # remove generic tokens
    filtered = [p for p in parts if p not in IGNORE_TOKENS]

    if not filtered:
        return None

    # take LAST meaningful token (most specific)
    return filtered[-1]


def build_candidate(group_id: str, artifact_id: str) -> str | None:
    group_id = group_id.strip()
    if not group_id:
        return None

    suffix = extract_suffix(artifact_id)
    if not suffix:
        return None

    return f"{group_id}.{suffix}"


def process_tag(tag_dir: Path) -> None:
    coords_file = tag_dir / "coords_ranked.csv"
    out_file = tag_dir / "prefix_candidates.txt"

    if not coords_file.exists():
        print(f"[SKIP] Missing {coords_file}")
        return

    candidates = set()

    with coords_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_id = row.get("groupId", "")
            artifact_id = row.get("artifactId", "")
            candidate = build_candidate(group_id, artifact_id)
            if candidate:
                candidates.add(candidate)

    sorted_candidates = sorted(candidates)

    with out_file.open("w", encoding="utf-8") as f:
        for c in sorted_candidates:
            f.write(c + "\n")

    print(f"[OK] {tag_dir.name}: wrote {len(sorted_candidates)} candidates (groupId+suffix only)")


def main():
    for tag_dir in sorted(MVN_DIR.iterdir()):
        if tag_dir.is_dir():
            process_tag(tag_dir)


if __name__ == "__main__":
    main()
