#!/usr/bin/env python3
"""
Dataset 1 availability check for Google Play and RuStore.

Input:
  results/baseline/apps_baseline.csv   (contains column 'package')
  data/meta/latest.csv.gz              (AndroZoo snapshot)

Output:
  results/baseline/apps_dataset1_availability.csv

Notes:
-Live checks are best-effort HTTP checks against public store pages
-I take each app’s package name from apps_baseline.csv
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
    """
    Walk upward from this script location until we find a directory that looks like the project root:
    - has data/meta/latest.csv.gz
    - has results/
    """
    here = Path(__file__).resolve()
    for p in [here.parent] + list(here.parents):
        if (p / "data" / "meta" / "latest.csv.gz").exists() and (p / "results").exists():
            return p
    # fallback to current working directory
    return Path.cwd().resolve()


def read_baseline_rows(baseline_csv: Path):
    with baseline_csv.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        fields = r.fieldnames or []
        lf = {c.lower(): c for c in fields}

        pkg_col = lf.get("package") or lf.get("pkg_name") or lf.get("package_name")
        if not pkg_col:
            raise ValueError(f"apps_baseline.csv must contain a package column. Found: {fields}")

        region_col = lf.get("region", "")
        cat_col = lf.get("category", "")
        pair_col = lf.get("pair_id", "")
        name_col = lf.get("app_name", "")
        sha_col = lf.get("sha256", "")
        path_col = lf.get("apk_path", "")

        rows = []
        packages = set()

        for row in r:
            pkg = (row.get(pkg_col) or "").strip()
            if not pkg:
                continue
            packages.add(pkg)
            rows.append({
                "region": (row.get(region_col) or "").strip() if region_col else "",
                "category": (row.get(cat_col) or "").strip() if cat_col else "",
                "pair_id": (row.get(pair_col) or "").strip() if pair_col else "",
                "app_name": (row.get(name_col) or "").strip() if name_col else "",
                "apk_path": (row.get(path_col) or "").strip() if path_col else "",
                "sha256": (row.get(sha_col) or "").strip() if sha_col else "",
                "package": pkg,
            })

        return rows, packages


def scan_androzoo_latest(latest_gz: Path, packages: Set[str]):
    """
    For each package:
    - union all observed markets
    - best Play entry by max vercode -> (vercode, sha256)
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
    Best-effort: request public Play page.
    """
    url = f"https://play.google.com/store/apps/details?id={pkg}&hl=en&gl=US"
    try:
        r = session.get(url, timeout=20, allow_redirects=True)
        if r.status_code != 200:
            return r.status_code, False
        t = r.text.lower()
        if "requested url was not found" in t or "item not found" in t:
            return r.status_code, False
        # sanity: package often appears in page source
        if pkg.lower() not in t:
            return r.status_code, False
        return r.status_code, True
    except Exception:
        return None, False


def check_rustore_live(pkg: str, session: requests.Session) -> Tuple[Optional[int], bool]:
    """
    Best-effort: request RuStore catalog page and verify redirect + body hints.
    """
    url = f"https://www.rustore.ru/catalog/app/{pkg}"
    try:
        r = session.get(url, timeout=20, allow_redirects=True)
        if r.status_code != 200:
            return r.status_code, False

        final_url = str(r.url)
        final_ok = f"/catalog/app/{pkg}" in final_url

        t = r.text.lower()
        not_found = ("страница не найдена" in t) or ("page not found" in t)
        body_ok = (pkg.lower() in t)

        ok = final_ok and (body_ok or (not not_found))
        return r.status_code, ok
    except Exception:
        return None, False


def main():
    root = find_project_root()

    baseline_csv = root / "results" / "baseline" / "apps_baseline.csv"
    latest_gz = root / "data" / "meta" / "latest.csv.gz"
    out_csv = root / "results" / "baseline" / "apps_availability.csv"

    if not baseline_csv.exists():
        raise FileNotFoundError(f"Missing: {baseline_csv}")
    if not latest_gz.exists():
        raise FileNotFoundError(f"Missing: {latest_gz}")

    rows, packages = read_baseline_rows(baseline_csv)
    markets_map, best_play = scan_androzoo_latest(latest_gz, packages)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    })

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "region", "category", "pair_id", "app_name", "package",
            "apk_path", "sha256",
            "androzoo_in_latest", "androzoo_markets", "androzoo_has_play",
            "androzoo_best_play_vercode", "androzoo_best_play_sha256",
            "play_http_status", "play_live_available",
            "rustore_http_status", "rustore_live_available",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for r in rows:
            pkg = r["package"]
            androzoo_markets = sorted(markets_map.get(pkg, set()))
            in_latest = "1" if androzoo_markets else "0"
            has_play = "1" if PLAY_MARKET in androzoo_markets else "0"

            best = best_play.get(pkg)
            best_vc = str(best[0]) if best else ""
            best_sha = best[1] if best else ""

            play_status, play_ok = check_play_live(pkg, session)
            time.sleep(0.6)
            rustore_status, rustore_ok = check_rustore_live(pkg, session)
            time.sleep(0.6)

            w.writerow({
                **r,
                "androzoo_in_latest": in_latest,
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
