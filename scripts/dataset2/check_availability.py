#!/usr/bin/env python3
"""
Dataset 2 availability check for Google Play and RuStore.

Input:
  dataset2.csv   (contains column 'package')
  data/meta/latest.csv.gz              (AndroZoo snapshot)

Output:
  dataset2/apps_dataset2_availability.csv

Notes:
-Live checks are best-effort HTTP checks against public store pages
-I take each app’s package name from dataset2.csv
-I check AndroZoo latest.csv.gz to see which markets that package was observed in (historical presence).
-I then open the Google Play and RuStore app pages for that package and treat a valid page response as available now
"""

import csv
import gzip
import time
from pathlib import Path
from typing import Dict, Set, Tuple, Optional

import requests

PLAY_MARKET = "play.google.com"


def find_project_root() -> Path:
    # scripts/dataset2/check_availability.py -> project root is 2 levels up
    return Path(__file__).resolve().parents[2]


def read_dataset2_packages(dataset2_csv: Path) -> Dict[str, Set[str]]:
    """
    Reads dataset2.csv that contains at least: package, store.
    Returns: pkg -> set(stores)
    """
    pkg_to_stores: Dict[str, Set[str]] = {}
    with dataset2_csv.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        fields = r.fieldnames or []
        lower_fields = {name.lower(): name for name in fields}

        pkg_col = lower_fields.get("package") or lower_fields.get("pkg_name") or lower_fields.get("package_name")
        store_col = lower_fields.get("store")

        if not pkg_col:
            raise ValueError(f"dataset2.csv must contain a package column. Found: {fields}")
        if not store_col:
            raise ValueError(f"dataset2.csv must contain a store column. Found: {fields}")

        for row in r:
            pkg = (row.get(pkg_col) or "").strip()
            store = (row.get(store_col) or "").strip()
            if not pkg:
                continue
            pkg_to_stores.setdefault(pkg, set()).add(store)

    return pkg_to_stores


def scan_androzoo_latest(latest_gz: Path, packages: Set[str]):
    """
    Streams latest.csv.gz once and collects:
    - markets set observed for each package
    - best Play entry (max vercode) for each package: (vercode, sha256)
    """
    markets_map: Dict[str, Set[str]] = {p: set() for p in packages}
    best_play: Dict[str, Tuple[int, str]] = {}

    with gzip.open(latest_gz, "rt", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        _ = next(reader, None)  # header
        for row in reader:
            if len(row) != 11:
                continue
            sha256, sha1, md5, dex_date, apk_size, pkg_name, vercode, vt_det, vt_scan_date, dex_size, markets = row
            if pkg_name not in packages:
                continue

            for m in markets.split("|"):
                m = m.strip()
                if m:
                    markets_map[pkg_name].add(m)

            if PLAY_MARKET in markets:
                try:
                    vc = int(vercode)
                except ValueError:
                    continue
                prev = best_play.get(pkg_name)
                if prev is None or vc > prev[0]:
                    best_play[pkg_name] = (vc, sha256)

    return markets_map, best_play


def check_play_live(pkg: str, session: requests.Session) -> Tuple[Optional[int], bool]:
    """
    Best-effort check of Play availability via the public app page.
    """
    url = f"https://play.google.com/store/apps/details?id={pkg}&hl=en&gl=US"
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            return r.status_code, False
        t = r.text.lower()
        if "requested url was not found" in t or "item not found" in t:
            return r.status_code, False
        return r.status_code, True
    except Exception:
        return None, False


def check_rustore_live(pkg: str, session: requests.Session) -> Tuple[Optional[int], bool]:
    """
    Best-effort check of RuStore availability via the catalog app page.
    """
    url = f"https://www.rustore.ru/catalog/app/{pkg}"
    try:
        r = session.get(url, timeout=20, allow_redirects=True)
        if r.status_code != 200:
            return r.status_code, False
        t = r.text.lower()
        if "страница не найдена" in t or "page not found" in t:
            return r.status_code, False
        return r.status_code, True
    except Exception:
        return None, False


def main():
    root = find_project_root()

    dataset2_csv = root / "dataset2" / "dataset2.csv"
    latest_gz = root / "data" / "meta" / "latest.csv.gz"
    out_csv = root / "dataset2" / "availability_report.csv"

    if not dataset2_csv.exists():
        raise FileNotFoundError(f"Missing: {dataset2_csv} (put dataset2.csv there, or rename accordingly)")
    if not latest_gz.exists():
        raise FileNotFoundError(f"Missing: {latest_gz} (expected AndroZoo latest.csv.gz here)")

    pkg_to_stores = read_dataset2_packages(dataset2_csv)
    packages = set(pkg_to_stores.keys())

    markets_map, best_play = scan_androzoo_latest(latest_gz, packages)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    })

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "package",
            "dataset2_store",
            "in_androzoo",
            "androzoo_markets",
            "androzoo_has_play",
            "androzoo_best_play_vercode",
            "androzoo_best_play_sha256",
            "play_http_status",
            "play_live_available",
            "rustore_http_status",
            "rustore_live_available",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for pkg in sorted(packages):
            stores = sorted(pkg_to_stores.get(pkg, set()))
            androzoo_markets = sorted(markets_map.get(pkg, set()))
            in_androzoo = "1" if androzoo_markets else "0"
            has_play = "1" if PLAY_MARKET in androzoo_markets else "0"

            best = best_play.get(pkg)
            best_vc = str(best[0]) if best else ""
            best_sha = best[1] if best else ""

            play_status, play_ok = check_play_live(pkg, session)
            time.sleep(0.6)
            rustore_status, rustore_ok = check_rustore_live(pkg, session)
            time.sleep(0.6)

            w.writerow({
                "package": pkg,
                "dataset2_store": "|".join(stores),
                "in_androzoo": in_androzoo,
                "androzoo_markets": "|".join(androzoo_markets),
                "androzoo_has_play": has_play,
                "androzoo_best_play_vercode": best_vc,
                "androzoo_best_play_sha256": best_sha,
                "play_http_status": "" if play_status is None else str(play_status),
                "play_live_available": "1" if play_ok else "0",
                "rustore_http_status": "" if rustore_status is None else str(rustore_status),
                "rustore_live_available": "1" if rustore_ok else "0",
            })

    print(f"Wrote: {out_csv}")


if __name__ == "__main__":
    main()
