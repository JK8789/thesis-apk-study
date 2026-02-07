#!/usr/bin/env python3
import csv
import json
import os
from collections import defaultdict

APPS_CSV = "data/meta/apps.csv"
LOCAL_CSV = "results/local/local_from_manifest.csv"
VT_CSV = "results/vt/vt_features.csv"
MANIFEST_DIR = "results/manifest"
OUT_DIR = "results/pairs"

def read_csv_index(path, key_field):
    idx = {}
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            k = (row.get(key_field) or "").strip().upper()
            if not k:
                continue
            idx[k] = row
    return idx

def to_int(x):
    if x is None:
        return 0
    s = str(x).strip()
    if s == "":
        return 0
    try:
        return int(float(s))
    except Exception:
        return 0

def get_any(row, keys, default=""):
    for k in keys:
        if k in row and str(row.get(k)).strip() != "":
            return row.get(k)
    return default

def get_int_any(row, keys, default=0):
    return to_int(get_any(row, keys, default=""))

def load_manifest_permissions(sha):
    p = os.path.join(MANIFEST_DIR, f"{sha}.json")
    if not os.path.isfile(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        j = json.load(f)
    perms = j.get("permissions") or []
    perms = [str(x).strip() for x in perms if str(x).strip()]
    return perms

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    local_idx = read_csv_index(LOCAL_CSV, "sha256")
    vt_idx = read_csv_index(VT_CSV, "sha256")


    apps = []
    with open(APPS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sha = (row.get("sha256") or "").strip().upper()
            if not sha:
                continue
            apps.append({
                "region": (row.get("region") or "").strip(),
                "category": (row.get("category") or "").strip(),
                "pair_id": (row.get("pair_id") or "").strip(),
                "app_name": (row.get("app_name") or "").strip(),
                "apk_path": (row.get("apk_path") or "").strip(),
                "sha256": sha,
            })

    enriched = {}
    for a in apps:
        sha = a["sha256"]
        loc = local_idx.get(sha, {})
        vt = vt_idx.get(sha, {})

        perms_list = load_manifest_permissions(sha)

        perm_count_local = get_int_any(loc, [
            "permissions_count", "perm_count_local", "perm_count", "permissions"
        ])

        rec = dict(a)
        rec.update({
            "package": str(get_any(loc, ["package", "pkg", "package_name"], "")).strip(),
            "version_code": str(get_any(loc, ["version_code", "ver_code"], "")).strip(),
            "version_name": str(get_any(loc, ["version_name", "ver_name"], "")).strip(),
            "min_sdk": str(get_any(loc, ["min_sdk", "minSdkVersion"], "")).strip(),
            "target_sdk": str(get_any(loc, ["target_sdk", "targetSdkVersion"], "")).strip(),
            "max_sdk": str(get_any(loc, ["max_sdk", "maxSdkVersion"], "")).strip(),

            "perm_count_local": perm_count_local,
            "permissions_list": perms_list,

            "activities_local": get_int_any(loc, ["activities_count", "activities_local", "activities"]),
            "services_local": get_int_any(loc, ["services_count", "services_local", "services"]),
            "receivers_local": get_int_any(loc, ["receivers_count", "receivers_local", "receivers"]),
            "providers_local": get_int_any(loc, ["providers_count", "providers_local", "providers"]),

            "exported_act_true": get_int_any(loc, ["exported_activities_true", "exported_act_true"]),
            "exported_srv_true": get_int_any(loc, ["exported_services_true", "exported_srv_true"]),
            "exported_rcv_true": get_int_any(loc, ["exported_receivers_true", "exported_rcv_true"]),
            "exported_prv_true": get_int_any(loc, ["exported_providers_true", "exported_prv_true"]),
            "is_debuggable": str(get_any(loc, ["is_debuggable", "debuggable"], "")).strip(),

            "vt_last_analysis_date": str(get_any(vt, ["vt_last_analysis_date"], "")).strip(),
            "vt_malicious": get_int_any(vt, ["vt_malicious", "malicious"]),
            "vt_suspicious": get_int_any(vt, ["vt_suspicious", "suspicious"]),
            "vt_harmless": get_int_any(vt, ["vt_harmless", "harmless"]),
            "vt_undetected": get_int_any(vt, ["vt_undetected", "undetected"]),
            "vt_perm_count": get_int_any(vt, ["vt_perm_count", "perm_count"]),
            "vt_dangerous_perm_count": get_int_any(vt, ["vt_dangerous_perm_count", "dangerous_perm_count"]),
        })

        rec["exported_total"] = (
            rec["exported_act_true"] + rec["exported_srv_true"] +
            rec["exported_rcv_true"] + rec["exported_prv_true"]
        )
        enriched[sha] = rec

    pairs = defaultdict(list)
    for sha, rec in enriched.items():
        pairs[rec["pair_id"]].append(rec)

    # Output 1: pair summary
    out1 = os.path.join(OUT_DIR, "pairs_summary.csv")
    with open(out1, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "category","pair_id",
            "ru_app","eu_app",
            "ru_sha256","eu_sha256",
            "ru_package","eu_package",
            "ru_perm_count_local","eu_perm_count_local","delta_perm_local_ru_minus_eu",
            "ru_exported_total","eu_exported_total","delta_exported_total_ru_minus_eu",
            "ru_vt_malicious","eu_vt_malicious",
            "ru_vt_suspicious","eu_vt_suspicious",
            "ru_vt_perm_count","eu_vt_perm_count",
            "ru_vt_dangerous_perm_count","eu_vt_dangerous_perm_count",
        ])

        for pair_id, lst in sorted(pairs.items()):
            if not pair_id:
                continue
            ru = next((x for x in lst if x["region"] == "ru"), None)
            eu = next((x for x in lst if x["region"] == "eu"), None)
            if not ru or not eu:
                continue

            w.writerow([
                ru["category"], pair_id,
                ru["app_name"], eu["app_name"],
                ru["sha256"], eu["sha256"],
                ru["package"], eu["package"],
                ru["perm_count_local"], eu["perm_count_local"], ru["perm_count_local"] - eu["perm_count_local"],
                ru["exported_total"], eu["exported_total"], ru["exported_total"] - eu["exported_total"],
                ru["vt_malicious"], eu["vt_malicious"],
                ru["vt_suspicious"], eu["vt_suspicious"],
                ru["vt_perm_count"], eu["vt_perm_count"],
                ru["vt_dangerous_perm_count"], eu["vt_dangerous_perm_count"],
            ])

    # Output 2: permission set diffs
    out2 = os.path.join(OUT_DIR, "pairs_permissions_diff.csv")
    with open(out2, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "category","pair_id",
            "ru_app","eu_app",
            "ru_perm_count_local","eu_perm_count_local",
            "ru_only_count","eu_only_count","common_count",
            "ru_only_permissions","eu_only_permissions","common_permissions"
        ])

        for pair_id, lst in sorted(pairs.items()):
            if not pair_id:
                continue
            ru = next((x for x in lst if x["region"] == "ru"), None)
            eu = next((x for x in lst if x["region"] == "eu"), None)
            if not ru or not eu:
                continue

            ru_set = set(ru["permissions_list"] or [])
            eu_set = set(eu["permissions_list"] or [])
            ru_only = sorted(ru_set - eu_set)
            eu_only = sorted(eu_set - ru_set)
            common = sorted(ru_set & eu_set)

            w.writerow([
                ru["category"], pair_id,
                ru["app_name"], eu["app_name"],
                ru["perm_count_local"], eu["perm_count_local"],
                len(ru_only), len(eu_only), len(common),
                ";".join(ru_only),
                ";".join(eu_only),
                ";".join(common),
            ])

    # Output 3: app permission list
    out3 = os.path.join(OUT_DIR, "app_permissions_list.csv")
    with open(out3, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sha256","region","category","pair_id","app_name","package","perm_count_local","permissions"])
        for sha, rec in sorted(enriched.items(), key=lambda x: (x[1]["region"], x[1]["category"], x[1]["pair_id"], x[1]["app_name"])):
            w.writerow([
                sha,
                rec["region"], rec["category"], rec["pair_id"],
                rec["app_name"], rec["package"],
                rec["perm_count_local"],
                ";".join(rec["permissions_list"] or [])
            ])

    print(f"Wrote {out1}")
    print(f"Wrote {out2}")
    print(f"Wrote {out3}")

if __name__ == "__main__":
    main()

