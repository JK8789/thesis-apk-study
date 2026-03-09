# scripts/build_pair_permission_status.py
import csv
from pathlib import Path

IN_PATH = Path("results/pairs/pairs_permissions_diff.csv")
OUT_PATH = Path("results/pairs/pair_permission_status.csv")

def split_perms(s: str) -> list[str]:
    if not s:
        return []
    # permissions are stored as ';' separated in our outputs
    return [p.strip() for p in s.split(";") if p.strip()]

def main() -> None:
    if not IN_PATH.exists():
        raise SystemExit(f"Missing input: {IN_PATH} (run build_pair_tables.py first)")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows_out = []
    with IN_PATH.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)


        # ru_only_permissions, eu_only_permissions, common_permissions
        for row in r:
            pair_id = row.get("pair_id", "").strip()
            if not pair_id:
                continue

            ru_only = split_perms(row.get("ru_only_permissions", ""))
            eu_only = split_perms(row.get("eu_only_permissions", ""))
            common = split_perms(row.get("common_permissions", ""))

            for p in ru_only:
                rows_out.append({"pair_id": pair_id, "permission": p, "status": "ru_only"})
            for p in eu_only:
                rows_out.append({"pair_id": pair_id, "permission": p, "status": "eu_only"})
            for p in common:
                rows_out.append({"pair_id": pair_id, "permission": p, "status": "common"})


    rows_out.sort(key=lambda x: (x["pair_id"], x["status"], x["permission"]))

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pair_id", "permission", "status"])
        w.writeheader()
        w.writerows(rows_out)

    print(f"Wrote {OUT_PATH} ({len(rows_out)} rows)")

if __name__ == "__main__":
    main()

