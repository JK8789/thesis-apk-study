#!/usr/bin/env python3
import csv
import json
import datetime
from pathlib import Path

APPS_CSV = Path("data/meta/apps.csv")
VT_DIR = Path("results/vt/file")
OUT_CSV = Path("results/vt/vt_features.csv")

VT_FIELDS = [
    "vt_last_analysis_date",
    "vt_malicious",
    "vt_suspicious",
    "vt_harmless",
    "vt_undetected",
    "vt_perm_count",
    "vt_dangerous_perm_count",
]

def iso_utc_from_ts(ts):
    if ts is None or ts == "":
        return ""

    if isinstance(ts, (int, float)):
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        tsi = int(ts)
        return datetime.datetime.fromtimestamp(tsi, tz=datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return str(ts)

def safe_int(x):
    try:
        if x is None or x == "":
            return ""
        return int(x)
    except Exception:
        return ""

def main():
    rows_out = []
    with APPS_CSV.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sha = (row.get("sha256") or "").strip().upper()
            if not sha:
                continue

            vt_path = VT_DIR / f"{sha}.json"
            out = {k: "" for k in VT_FIELDS}
            out["sha256"] = sha

            if vt_path.exists():
                data = json.loads(vt_path.read_text(encoding="utf-8"))
                obj = data[0] if isinstance(data, list) and data else {}

                stats = obj.get("last_analysis_stats") or {}
                out["vt_malicious"] = stats.get("malicious", "")
                out["vt_suspicious"] = stats.get("suspicious", "")
                out["vt_harmless"] = stats.get("harmless", "")
                out["vt_undetected"] = stats.get("undetected", "")

                out["vt_last_analysis_date"] = iso_utc_from_ts(obj.get("last_analysis_date"))

                ag = obj.get("androguard") or {}

                # permissions list can be missing in VT, even if scan stats exist
                perms_list = ag.get("permissions")
                perm_details = ag.get("permission_details") or {}

                if isinstance(perms_list, list):
                    out["vt_perm_count"] = len(perms_list)
                elif isinstance(perm_details, dict) and perm_details:
                    out["vt_perm_count"] = len(perm_details)
                else:
                    out["vt_perm_count"] = ""

                if isinstance(perm_details, dict) and perm_details:
                    dang = 0
                    for _, v in perm_details.items():
                        ptype = (v or {}).get("permission_type", "") or ""
                        if "dangerous" in ptype.lower():
                            dang += 1
                    out["vt_dangerous_perm_count"] = dang
                else:
                    out["vt_dangerous_perm_count"] = ""

            rows_out.append(out)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sha256"] + VT_FIELDS)
        w.writeheader()
        for row in rows_out:
            for k in ["vt_malicious","vt_suspicious","vt_harmless","vt_undetected","vt_perm_count","vt_dangerous_perm_count"]:
                row[k] = safe_int(row.get(k, ""))
            w.writerow(row)

    print(f"Wrote {OUT_CSV}")

if __name__ == "__main__":
    main()

