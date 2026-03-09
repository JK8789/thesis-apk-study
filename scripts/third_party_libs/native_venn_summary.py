#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
IN = BASE / "results" / "native" / "native_libs_per_app.csv"
OUT = BASE / "results" / "native" / "native_summary.csv"


def parse_list(x: str):
    if pd.isna(x) or not str(x).strip():
        return set()
    return set(i.strip() for i in str(x).split(";") if i.strip())


def main():
    df = pd.read_csv(IN)

    # collect unique .so per region
    ru_set = set()
    eu_set = set()

    for _, r in df.iterrows():
        s = parse_list(r.get("native_so_names"))

        if str(r.get("region")).lower() == "ru":
            ru_set |= s
        elif str(r.get("region")).lower() == "eu":
            eu_set |= s

    common = ru_set & eu_set
    ru_only = ru_set - eu_set
    eu_only = eu_set - ru_set

    out = pd.DataFrame([
        {
            "ru_only_count": len(ru_only),
            "eu_only_count": len(eu_only),
            "common_count": len(common),
            "ru_only_list": ";".join(sorted(ru_only)),
            "eu_only_list": ";".join(sorted(eu_only)),
            "common_list": ";".join(sorted(common)),
        }
    ])

    out.to_csv(OUT, index=False)
    print("OK wrote", OUT)


if __name__ == "__main__":
    main()
