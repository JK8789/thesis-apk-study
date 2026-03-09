#!/usr/bin/env python3
import csv
from pathlib import Path

IN_CSV = Path("results/baseline/apps_baseline.csv")
OUT_DIR = Path("results/qc")
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_MISMATCH = OUT_DIR / "permissions_local_vs_vt.csv"
OUT_SUMMARY = OUT_DIR / "summary.txt"

def to_int(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def main():
    rows = []
    with IN_CSV.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    mismatch_rows = []
    counts = {
        "n": len(rows),
        "local_perm_zero": 0,
        "vt_perm_missing": 0,
        "perm_mismatch": 0,
        "vt_malicious_pos": 0,
        "vt_suspicious_pos": 0,
        "sdk_missing_any": 0,
    }

    for row in rows:
        sha = row.get("sha256","").strip()
        app = row.get("app_name","").strip()
        pkg = row.get("package","").strip()

        local_perm = to_int(row.get("perm_count_local"))
        vt_perm = to_int(row.get("vt_perm_count"))
        vt_mal = to_int(row.get("vt_malicious")) or 0
        vt_susp = to_int(row.get("vt_suspicious")) or 0

        min_sdk = row.get("min_sdk","").strip()
        target_sdk = row.get("target_sdk","").strip()

        if local_perm == 0:
            counts["local_perm_zero"] += 1

        if vt_perm is None:
            counts["vt_perm_missing"] += 1

        if (min_sdk == "" or target_sdk == ""):
            counts["sdk_missing_any"] += 1

        if vt_mal > 0:
            counts["vt_malicious_pos"] += 1
        if vt_susp > 0:
            counts["vt_suspicious_pos"] += 1

        mismatch = False
        if local_perm is not None and vt_perm is not None and local_perm != vt_perm:
            mismatch = True
            counts["perm_mismatch"] += 1

        mismatch_rows.append({
            "sha256": sha,
            "app_name": app,
            "package": pkg,
            "perm_count_local": "" if local_perm is None else local_perm,
            "vt_perm_count": "" if vt_perm is None else vt_perm,
            "perm_diff_vt_minus_local": "" if (local_perm is None or vt_perm is None) else (vt_perm - local_perm),
            "vt_perm_missing": "1" if vt_perm is None else "0",
            "local_perm_zero": "1" if local_perm == 0 else "0",
            "mismatch": "1" if mismatch else "0",
        })

    with OUT_MISMATCH.open("w", newline="", encoding="utf-8") as f:
        fields = list(mismatch_rows[0].keys()) if mismatch_rows else []
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(mismatch_rows)

    summary_lines = [
        f"apps_total={counts['n']}",
        f"local_perm_zero={counts['local_perm_zero']}",
        f"vt_perm_missing={counts['vt_perm_missing']}",
        f"perm_mismatch_local_vs_vt={counts['perm_mismatch']}",
        f"vt_malicious_positive={counts['vt_malicious_pos']}",
        f"vt_suspicious_positive={counts['vt_suspicious_pos']}",
        f"sdk_missing_any(min_sdk or target_sdk)={counts['sdk_missing_any']}",
        "",
        "Notes:",
        "- VT perm counts may be missing even when scan stats exist (normal).",
        "- If local_perm_zero but vt_perm_count>0, local manifest extraction needs investigation for that APK.",
    ]
    OUT_SUMMARY.write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"Wrote {OUT_MISMATCH}")
    print(f"Wrote {OUT_SUMMARY}")

if __name__ == "__main__":
    main()

