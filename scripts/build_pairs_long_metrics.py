# scripts/build_pairs_long_metrics.py
import csv
from pathlib import Path

IN_PATH = Path("results/pairs/pairs_summary.csv")
OUT_PATH = Path("results/pairs/pairs_metrics_long.csv")

ID_COLS = ["category", "pair_id", "ru_app", "eu_app"]
DROP_COLS = {
    # non-metrics (identifiers)
    "ru_sha256", "eu_sha256", "ru_package", "eu_package",
}

def sniff_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="replace")[:5000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";"]).delimiter
    except Exception:
        return ","

def main() -> None:
    if not IN_PATH.exists():
        raise SystemExit(f"Missing input: {IN_PATH} (run build_pair_tables.py first)")

    delim = sniff_delimiter(IN_PATH)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with IN_PATH.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter=delim)
        if not r.fieldnames:
            raise SystemExit("pairs_summary.csv has no header?")


        metrics = [c for c in r.fieldnames if c not in ID_COLS and c not in DROP_COLS]

        out_rows = []
        for row in r:
            base = {k: (row.get(k, "") or "").strip() for k in ID_COLS}


            if not base["pair_id"]:
                continue

            for m in metrics:
                val = (row.get(m, "") or "").strip()

                if val == "":
                    continue
                out_rows.append({
                    **base,
                    "metric": m,
                    "value": val,
                })


    out_rows.sort(key=lambda x: (x["category"], x["pair_id"], x["metric"]))

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ID_COLS + ["metric", "value"])
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {OUT_PATH} ({len(out_rows)} rows)")

if __name__ == "__main__":
    main()

