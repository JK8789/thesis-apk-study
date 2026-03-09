#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
APPS_CSV = BASE_DIR / "data" / "meta" / "apps.csv"
VT_DIR = BASE_DIR / "results" / "vt" / "file"
OUT_DIR = BASE_DIR / "results" / "pairs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUT_DIR / "pair_component_status_vt.csv"


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def vt_path_for_sha(sha: str) -> Path | None:

    p1 = VT_DIR / f"{sha}.json"
    p2 = VT_DIR / f"{sha.lower()}.json"
    p3 = VT_DIR / f"{sha.upper()}.json"
    for p in (p1, p2, p3):
        if p.exists():
            return p
    return None


def extract_androguard_block(vt_obj):

    if isinstance(vt_obj, list):
        if not vt_obj:
            return {}
        vt_obj = vt_obj[0]

    if not isinstance(vt_obj, dict):
        return {}

    if "androguard" in vt_obj and isinstance(vt_obj["androguard"], dict):
        return vt_obj["androguard"]


    ag = (
        vt_obj.get("data", {})
        .get("attributes", {})
        .get("androguard", {})
    )
    return ag if isinstance(ag, dict) else {}


def get_list(ag: dict, key_variants):
    for k in key_variants:
        v = ag.get(k)
        if isinstance(v, list):
            return v

        if isinstance(v, dict):

            vals = [x for x in v.values() if isinstance(x, str)]
            if vals:
                return vals
    return []


def load_components_from_vt(sha: str):

    out = {"activity": set(), "service": set(), "receiver": set(), "provider": set()}
    p = vt_path_for_sha(sha)
    if not p:
        return out

    vt = read_json(p)
    ag = extract_androguard_block(vt)

    activities = get_list(ag, ["Activities", "activities"])
    services = get_list(ag, ["Services", "services"])
    receivers = get_list(ag, ["Receivers", "receivers"])
    providers = get_list(ag, ["Providers", "providers"])

    out["activity"] = set(activities)
    out["service"] = set(services)
    out["receiver"] = set(receivers)
    out["provider"] = set(providers)
    return out


def main():
    pairs = defaultdict(dict)

    with open(APPS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            pair_id = row["pair_id"].strip()
            region = row["region"].strip()
            pairs[pair_id]["category"] = row["category"].strip()
            pairs[pair_id][region] = {
                "sha256": row["sha256"].strip(),
                "app_name": row["app_name"].strip(),
            }

    rows = []
    for pair_id, data in sorted(pairs.items()):
        if "ru" not in data or "eu" not in data:
            continue

        category = data.get("category", "")
        ru = data["ru"]
        eu = data["eu"]

        ru_sets = load_components_from_vt(ru["sha256"])
        eu_sets = load_components_from_vt(eu["sha256"])

        for comp_type in ("activity", "service", "receiver", "provider"):
            ru_set = ru_sets.get(comp_type, set())
            eu_set = eu_sets.get(comp_type, set())

            common = ru_set & eu_set
            ru_only = ru_set - eu_set
            eu_only = eu_set - ru_set

            for name in sorted(common):
                rows.append([category, pair_id, comp_type, name, "common"])
            for name in sorted(ru_only):
                rows.append([category, pair_id, comp_type, name, "ru_only"])
            for name in sorted(eu_only):
                rows.append([category, pair_id, comp_type, name, "eu_only"])

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "pair_id", "component_type", "component_name", "status"])
        w.writerows(rows)

    print(f"Wrote {OUT_CSV} ({len(rows)} rows)")


if __name__ == "__main__":
    main()

