#!/usr/bin/env python3
import csv
from pathlib import Path

APPS_CSV = Path("data/meta/apps.csv")
LOCAL_CSV = Path("results/local/local_from_manifest.csv")
VT_CSV = Path("results/vt/vt_features.csv")
OUT_CSV = Path("results/baseline/apps_baseline.csv")

def load_by_sha(path: Path):
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return {(row.get("sha256") or "").strip().upper(): row for row in r if (row.get("sha256") or "").strip()}

def main():
    local = load_by_sha(LOCAL_CSV)
    vt = load_by_sha(VT_CSV)

    with APPS_CSV.open(newline="", encoding="utf-8") as f:
        apps_r = csv.DictReader(f)
        apps_rows = list(apps_r)
        apps_fields = apps_r.fieldnames or []

    local_fields = [c for c in (next(iter(local.values())).keys() if local else []) if c != "sha256"]
    vt_fields = [c for c in (next(iter(vt.values())).keys() if vt else []) if c != "sha256"]

    out_fields = apps_fields + local_fields + vt_fields

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()

        for row in apps_rows:
            sha = (row.get("sha256") or "").strip().upper()
            merged = dict(row)

            if sha in local:
                for k, v in local[sha].items():
                    if k != "sha256":
                        merged[k] = v

            if sha in vt:
                for k, v in vt[sha].items():
                    if k != "sha256":
                        merged[k] = v

            w.writerow(merged)

    print(f"Wrote {OUT_CSV}")

if __name__ == "__main__":
    main()

