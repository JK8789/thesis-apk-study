#!/usr/bin/env python3
import csv
import gzip
import sys
from pathlib import Path

# latest.csv.gz columns (AndroZoo): sha256,sha1,md5,dex_date,apk_size,pkg_name,vercode,vt_detection,vt_scan_date,dex_size,markets

def main(latest_gz: Path, packages_txt: Path, out_csv: Path, missing_txt: Path, market_filter: str = "play.google.com"):
    targets = [line.strip() for line in packages_txt.read_text(encoding="utf-8").splitlines() if line.strip()]
    target_set = set(targets)


    best = {}  # pkg -> (vercode:int, row:list[str])

    with gzip.open(latest_gz, "rt", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)  

        for row in reader:
            if len(row) != 11:
                continue

            sha256, sha1, md5, dex_date, apk_size, pkg_name, vercode, vt_det, vt_scan_date, dex_size, markets = row

            if pkg_name not in target_set:
                continue
            if market_filter not in markets:
                continue

            try:
                vc = int(vercode)
            except ValueError:
                continue

            prev = best.get(pkg_name)
            if prev is None or vc > prev[0]:
                best[pkg_name] = (vc, row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as o:
        w = csv.writer(o)
        w.writerow(["pkg_name","vercode","sha256","apk_size","dex_date","vt_detection","vt_scan_date","markets"])
        for pkg in targets:
            if pkg in best:
                vc, row = best[pkg]
                sha256, sha1, md5, dex_date, apk_size, pkg_name, vercode, vt_det, vt_scan_date, dex_size, markets = row
                w.writerow([pkg_name, vercode, sha256, apk_size, dex_date, vt_det, vt_scan_date, markets])

    missing = [pkg for pkg in targets if pkg not in best]
    missing_txt.parent.mkdir(parents=True, exist_ok=True)
    missing_txt.write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")

    print(f"Selected: {len(best)}/{len(targets)}")
    if missing:
        print("Missing packages (not found in AndroZoo with market filter):")
        for m in missing:
            print("  -", m)
        print(f"Wrote missing list to: {missing_txt}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(f"Usage: {sys.argv[0]} <latest.csv.gz> <eu_packages.txt> <out.csv> <missing.txt>")
        sys.exit(2)

    main(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3]),
        Path(sys.argv[4]),
    )

