#!/usr/bin/env python3
import csv
import sys
import time
from pathlib import Path
import requests

BASE = "https://androzoo.uni.lu/api/download"

def main(selected_csv: Path, out_dir: Path, apikey: str, sleep_s: float = 0.5):
    out_dir.mkdir(parents=True, exist_ok=True)

    with selected_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    ok = 0
    fail = 0

    for row in rows:
        pkg = row["pkg_name"]
        ver = row["vercode"]
        sha = row["sha256"]

        out_path = out_dir / f"{pkg}__vc{ver}__{sha}.apk"
        if out_path.exists() and out_path.stat().st_size > 1024 * 1024:
            print(f"[SKIP] {out_path.name}")
            ok += 1
            continue

        url = f"{BASE}?apikey={apikey}&sha256={sha}"
        try:
            with requests.get(url, stream=True, timeout=240) as r:
                r.raise_for_status()
                tmp = out_path.with_suffix(".apk.part")
                with open(tmp, "wb") as o:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            o.write(chunk)
                tmp.replace(out_path)

            size_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"[OK] {pkg} vc{ver} ({size_mb:.1f} MB)")
            ok += 1

        except Exception as e:
            print(f"[FAIL] {pkg} vc{ver} sha={sha} -> {e}")
            fail += 1

        time.sleep(sleep_s)

    print(f"\nDone. OK={ok}, FAIL={fail}, TOTAL={len(rows)}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <eu_selected.csv> <out_dir> <APIKEY>")
        sys.exit(2)

    main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3].strip())

