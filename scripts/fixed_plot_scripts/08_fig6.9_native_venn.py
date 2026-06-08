#!/usr/bin/env python3
"""
Create RU vs EU Venn diagram from:
  thesis-apk-study/results/native/native_summary.csv

Save to:
  thesis-apk-study/Plots/thesis_plot_scripts_projectpaths/fig6_9_native_venn.png

Run from thesis-apk-study/:
  python3 scripts/fixed_plot_scripts/08_fig6.9_native_venn.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

try:
    from matplotlib_venn import venn2
except ImportError:
    print(
        "Missing dependency: matplotlib-venn\n"
        "Install it with:\n"
        "  python3 -m pip install matplotlib-venn\n",
        file=sys.stderr,
    )
    raise


def _pick_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def main() -> int:
    ROOT = Path(__file__).resolve().parents[2]
    input_path = ROOT / "results/native/native_summary.csv"
    out_dir = ROOT / "Plots/thesis_plot_scripts_projectpaths"
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "fig6_9_native_venn.png"


    if not input_path.exists():
        print(f"Input file not found: {input_path.resolve()}", file=sys.stderr)
        return 1

    df = pd.read_csv(input_path)

    # Prefer these column names (matches what you used earlier)
    ru_col = _pick_first_existing_column(
        df,
        ["ru_only_count", "RU_only", "ru_only", "RU only", "ru_only_so", "ru_only_libs"],
    )
    eu_col = _pick_first_existing_column(
        df,
        ["eu_only_count", "EU_only", "eu_only", "EU only", "eu_only_so", "eu_only_libs"],
    )
    common_col = _pick_first_existing_column(
        df,
        ["common_count", "common", "intersection", "intersect", "Common", "shared"],
    )

    missing = [name for name, col in [("ru_only", ru_col), ("eu_only", eu_col), ("common", common_col)] if col is None]
    if missing:
        print(
            "Could not find required columns in CSV.\n"
            f"CSV columns are: {list(df.columns)}\n"
            "Expected something like: ru_only_count, eu_only_count, common_count",
            file=sys.stderr,
        )
        return 1

    # Use first row
    try:
        ru_only = int(df.loc[0, ru_col])     # type: ignore[index]
        eu_only = int(df.loc[0, eu_col])     # type: ignore[index]
        common = int(df.loc[0, common_col])  # type: ignore[index]
    except Exception as e:
        print(f"Failed to parse counts from first row: {e}", file=sys.stderr)
        return 1

    if any(x < 0 for x in (ru_only, eu_only, common)):
        print("Counts cannot be negative. Check the CSV.", file=sys.stderr)
        return 1

    # Plot
    fig = plt.figure(figsize=(8, 6), dpi=200)
    ax = fig.add_subplot(111)

    # venn2 takes (A_only, B_only, A_and_B)

    v = venn2(subsets=(ru_only, eu_only, common), set_labels=("RU region", "EU region"), ax=ax)
    
    v.set_labels[0].set_fontsize(14)
    v.set_labels[1].set_fontsize(14)
    
    for label in v.subset_labels:
        if label is not None:
          label.set_fontsize(14)
    
    ax.set_title("Native libraries (.so): RU vs EU", fontsize=14)

    # Save outputs (plots only)
    fig.savefig(png_path, bbox_inches="tight")

    plt.close(fig)

    # Helpful console output
    print("Counts used:")
    print(f"  RU only: {ru_only}")
    print(f"  EU only: {eu_only}")
    print(f"  Common:  {common}")
    print("\nSaved:")
    print(f"  {png_path}")


    return 0


if __name__ == "__main__":
    raise SystemExit(main())
