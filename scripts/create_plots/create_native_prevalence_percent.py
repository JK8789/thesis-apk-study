#!/usr/bin/env python3
"""
Native .so prevalence by region (RU vs EU) in percentage of apps.

Question answered:
  "What fraction of RU/EU apps include at least one native .so library?"

Input:
  results/native/native_libs_per_app.csv

Expected columns (best effort):
  - region (values: RU/EU)
  - native_so_names (semicolon-separated list of .so, or empty/NaN)

Output (plots only):
  Plots/native_prevalence/native_prevalence_percent.png
  Plots/native_prevalence/native_prevalence_percent.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_native_prevalence_percent.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import matplotlib.pyplot as plt


TITLE = "Native libraries (.so) prevalence by region"
EXPLANATION = (
    "Bars show the percentage of applications that contain at least one native .so library "
    "in the RU and EU datasets."
)


def normalize_region(x: Any) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip().lower()
    if s in {"ru", "russia"}:
        return "RU"
    if s in {"eu", "europe"}:
        return "EU"
    return None


def has_any_so(cell: Any) -> bool:
    """True if native_so_names cell contains at least one lib name."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return False
    s = str(cell).strip()
    if not s or s.lower() == "nan":
        return False
    # If it's semicolon-separated, at least one non-empty token is enough
    parts = [p.strip() for p in s.split(";")]
    return any(parts)  # any non-empty token


def main() -> int:
    input_path = Path("results/native/native_libs_per_app.csv")
    out_dir = Path("Plots/native_prevalence")
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "native_prevalence_percent.png"
    svg_path = out_dir / "native_prevalence_percent.svg"

    if not input_path.exists():
        print(f"Input file not found: {input_path.resolve()}", file=sys.stderr)
        return 1

    df = pd.read_csv(input_path)

    # Find required columns
    if "region" not in df.columns:
        print(f"Missing column 'region'. CSV columns: {list(df.columns)}", file=sys.stderr)
        return 1
    if "native_so_names" not in df.columns:
        print(f"Missing column 'native_so_names'. CSV columns: {list(df.columns)}", file=sys.stderr)
        return 1

    df["region_norm"] = df["region"].apply(normalize_region)
    df = df[df["region_norm"].isin(["RU", "EU"])].copy()

    # Determine if each app has any .so libs
    df["has_so"] = df["native_so_names"].apply(has_any_so)

    # Totals per region (do not assume always 20; use what is in file)
    totals = df.groupby("region_norm").size().to_dict()
    with_so = df.groupby("region_norm")["has_so"].sum().to_dict()

    # Ensure both keys exist
    for k in ["RU", "EU"]:
        totals.setdefault(k, 0)
        with_so.setdefault(k, 0)

    ru_total, eu_total = int(totals["RU"]), int(totals["EU"])
    ru_with, eu_with = int(with_so["RU"]), int(with_so["EU"])

    if ru_total == 0 or eu_total == 0:
        print(
            f"Not enough data to plot: RU total={ru_total}, EU total={eu_total}. "
            "Check the 'region' values in the CSV.",
            file=sys.stderr,
        )
        return 1

    ru_pct = 100.0 * ru_with / ru_total
    eu_pct = 100.0 * eu_with / eu_total

    # ---- Plot ----
    fig = plt.figure(figsize=(7.5, 5.5), dpi=200)
    fig.subplots_adjust(top=0.82)

    fig.suptitle(TITLE, fontsize=16, y=0.97)
    fig.text(0.5, 0.90, EXPLANATION, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    labels = ["RU", "EU"]
    pcts = [ru_pct, eu_pct]
    counts = [(ru_with, ru_total), (eu_with, eu_total)]

    bars = ax.bar(labels, pcts)

    ax.set_ylabel("Apps with ≥1 native .so (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    # Labels above bars: "X/Y (Z%)"
    for b, (num, den), pct in zip(bars, counts, pcts):
        ax.text(
            b.get_x() + b.get_width() / 2.0,
            b.get_height() + 2.0,
            f"{num}/{den} ({pct:.0f}%)",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)

    print("Saved:")
    print(f"  {png_path}")
    print(f"  {svg_path}")
    print(f"RU: {ru_with}/{ru_total} ({ru_pct:.1f}%)")
    print(f"EU: {eu_with}/{eu_total} ({eu_pct:.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
