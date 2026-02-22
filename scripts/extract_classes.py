#!/usr/bin/env python3
"""
Extract class names from apk dex files using androguard.

Outputs:
- results/classes/<SHA256>.txt  (one class per line, in dot notation)

Input:
- data/meta/apps.csv (must contain apk_path, sha256)
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Iterable, List, Set

from androguard.core.apk import APK
from androguard.core.dex import DEX


BASE_DIR = Path(__file__).resolve().parents[1]
APPS_CSV = BASE_DIR / "data" / "meta" / "apps.csv"
OUT_DIR = BASE_DIR / "results" / "classes"


def dex_classnames(apk: APK) -> Set[str]:
    """
    Return a set of class names in dot notation, e.g. 'com.facebook.ads.AdView'
    """
    classnames: Set[str] = set()

    dex_blobs = apk.get_all_dex() or []
    for blob in dex_blobs:
        try:
            d = DEX(blob)
            for c in d.get_classes():

                desc = c.get_name()
                if not desc or not desc.startswith("L") or "/" not in desc:
                    continue

                dotted = desc[1:].rstrip(";").replace("/", ".")
                classnames.add(dotted)
        except Exception as e:

            print(f"[WARN] Failed parsing a dex blob: {e}", file=sys.stderr)
            continue

    return classnames


def read_apps(csv_path: Path) -> Iterable[dict]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            yield row


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not APPS_CSV.exists():
        print(f"ERROR: missing {APPS_CSV}", file=sys.stderr)
        sys.exit(1)

    total = 0
    ok = 0
    failed = 0

    for row in read_apps(APPS_CSV):
        apk_path = (row.get("apk_path") or "").strip()
        sha = (row.get("sha256") or "").strip().upper()

        # skip empty rows in CSV
        if not apk_path or not sha:
            continue

        total += 1
        out_txt = OUT_DIR / f"{sha}.txt"

        print(f"[CLASSES] {sha}")

        if not os.path.isfile(apk_path):
            print(f"[ERROR] missing APK file: {apk_path}", file=sys.stderr)
            failed += 1
            continue

        try:
            apk = APK(apk_path)
            names = sorted(dex_classnames(apk))

            # Write atomically
            tmp = out_txt.with_suffix(".txt.tmp")
            with tmp.open("w", encoding="utf-8") as w:
                for n in names:
                    w.write(n + "\n")
            tmp.replace(out_txt)

            ok += 1
        except Exception as e:
            print(f"[ERROR] {sha}: failed extracting classes: {e}", file=sys.stderr)
            failed += 1
            continue

    print(f"Done. total={total} ok={ok} failed={failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

