#!/usr/bin/env python3
"""
Extract native (.so) libraries from APKs and produce a clean per-app summary.

Inputs:
- results/baseline/apps_baseline.csv  (preferred; must include apk_path)
  or fallback: data/meta/apps.csv (must include apk_path)
  Required columns: sha256, region, category, pair_id, app_name, apk_path
  Optional: package

Outputs (results/native):
- native_libs_long.csv        one row per (app, abi, so_name, zip_path)
- native_libs_per_app.csv     one row per app with counts + list of .so names
"""

from __future__ import annotations

import csv
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]

BASELINE_CSV = BASE_DIR / "results" / "baseline" / "apps_baseline.csv"
APPS_CSV = BASE_DIR / "data" / "meta" / "apps.csv"
OUT_DIR = BASE_DIR / "results" / "native"

KNOWN_ABIS = {
    "armeabi", "armeabi-v7a", "arm64-v8a",
    "x86", "x86_64",
    "mips", "mips64",
    "riscv64",
}

def read_csv_any_delim(path: Path) -> List[dict]:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    delim = "\t" if ("\t" in sample and "," not in sample) else ","
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f, delimiter=delim))

def select_input_csv() -> Path:
    if BASELINE_CSV.exists():
        return BASELINE_CSV
    if APPS_CSV.exists():
        return APPS_CSV
    raise SystemExit("Missing both results/baseline/apps_baseline.csv and data/meta/apps.csv")

def require_columns(rows: List[dict], required: Set[str], label: str) -> None:
    if not rows:
        raise SystemExit(f"{label} is empty")
    missing = required - set(rows[0].keys())
    if missing:
        raise SystemExit(f"{label} missing columns: {sorted(missing)}")

def parse_abi_and_soname(zip_path: str) -> Tuple[str, str] | None:
    # Expected: lib/<abi>/<name>.so
    if not zip_path.startswith("lib/") or not zip_path.endswith(".so"):
        return None
    parts = zip_path.split("/")
    if len(parts) != 3:
        return None
    _, abi, soname = parts
    return abi, soname

def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    in_csv = select_input_csv()
    apps = read_csv_any_delim(in_csv)

    required = {"sha256", "region", "category", "pair_id", "app_name", "apk_path"}
    require_columns(apps, required, str(in_csv))

    native_long: List[dict] = []
    per_app: List[dict] = []

    total = ok = failed = 0

    for app in apps:
        sha = (app.get("sha256") or "").strip().upper()
        region = (app.get("region") or "").strip()
        category = (app.get("category") or "").strip()
        pair_id = (app.get("pair_id") or "").strip()
        app_name = (app.get("app_name") or "").strip()
        apk_path = (app.get("apk_path") or "").strip()
        package = (app.get("package") or "").strip()  # optional

        if not sha or not apk_path:
            continue

        total += 1

        unique_sos: Set[str] = set()
        total_so_files = 0
        abi_set: Set[str] = set()
        abi_counter = Counter()

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                for info in z.infolist():
                    parsed = parse_abi_and_soname(info.filename)
                    if not parsed:
                        continue

                    abi, soname = parsed
                    abi_norm = abi if abi in KNOWN_ABIS else f"other:{abi}"

                    total_so_files += 1
                    unique_sos.add(soname)
                    abi_set.add(abi_norm)
                    abi_counter[abi_norm] += 1

                    native_long.append({
                        "sha256": sha,
                        "region": region,
                        "category": category,
                        "pair_id": pair_id,
                        "app_name": app_name,
                        "package": package,
                        "abi": abi_norm,
                        "so_name": soname,
                        "apk_zip_path": info.filename,
                        "compressed_size": info.compress_size,
                        "uncompressed_size": info.file_size,
                    })

            top_abi = abi_counter.most_common(1)[0][0] if abi_counter else ""

            per_app.append({
                "sha256": sha,
                "region": region,
                "category": category,
                "pair_id": pair_id,
                "app_name": app_name,
                "package": package,
                # requested fields
                "native_so_count_total": int(total_so_files),
                "native_so_count_unique": int(len(unique_sos)),
                "native_so_names": ";".join(sorted(unique_sos)),
                # keep ABI info (small, useful)
                "native_abis": ";".join(sorted(abi_set)),
                "native_distinct_abis": int(len(abi_set)),
                "native_top_abi": top_abi,
            })

            ok += 1
        except Exception as e:
            failed += 1
            print(f"[ERROR] {sha}: failed reading APK zip: {e}")

    write_csv(
        OUT_DIR / "native_libs_long.csv",
        native_long,
        [
            "sha256", "region", "category", "pair_id", "app_name", "package",
            "abi", "so_name", "apk_zip_path", "compressed_size", "uncompressed_size"
        ],
    )

    write_csv(
        OUT_DIR / "native_libs_per_app.csv",
        per_app,
        [
            "sha256", "region", "category", "pair_id", "app_name", "package",
            "native_so_count_total", "native_so_count_unique", "native_so_names",
            "native_abis", "native_distinct_abis", "native_top_abi"
        ],
    )

    print(f"[OK] Done. total={total} ok={ok} failed={failed}")
    print("[OK] Wrote:")
    print(" -", OUT_DIR / "native_libs_long.csv")
    print(" -", OUT_DIR / "native_libs_per_app.csv")

if __name__ == "__main__":
    main()
