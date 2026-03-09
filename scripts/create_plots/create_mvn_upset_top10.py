#!/usr/bin/env python3
"""
UpSet plot for top 10 Maven SDK tags across RU/EU apps.

Input:
  results/mvnrepo_dict/venn_counts_by_tag.csv

Output:
  Plots/mvn_upset/mvn_upset_top10.png
  Plots/mvn_upset/mvn_upset_top10.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_mvn_upset_top10.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


TOP_N = 10


def main() -> int:
    input_path = Path("results/mvnrepo_dict/venn_counts_by_tag.csv")
    out_dir = Path("Plots/mvn_upset")
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "mvn_upset_top10.png"
    svg_path = out_dir / "mvn_upset_top10.svg"

    if not input_path.exists():
        print(f"Input file not found: {input_path.resolve()}", file=sys.stderr)
        return 1

    df = pd.read_csv(input_path)

    required = [
        "tag",
        "ru_only_count",
        "eu_only_count",
        "common_count",
        "ru_only_prefixes",
        "eu_only_prefixes",
        "common_prefixes",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"Missing required columns: {missing}", file=sys.stderr)
        print(f"CSV columns: {list(df.columns)}", file=sys.stderr)
        return 1

    # Ensure numeric
    for c in ["ru_only_count", "eu_only_count", "common_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # Rank tags by total (RU-only + EU-only + common)
    df["total"] = df["ru_only_count"] + df["eu_only_count"] + df["common_count"]
    df = df.sort_values(["total", "tag"], ascending=[False, True]).head(TOP_N).reset_index(drop=True)

    tags = df["tag"].astype(str).tolist()

    # Totals per region (for labels on bars)
    # RU total = RU-only + common
    # EU total = EU-only + common
    ru_totals = (df["ru_only_count"] + df["common_count"]).tolist()
    eu_totals = (df["eu_only_count"] + df["common_count"]).tolist()

    # Total for bar height (both regions, but common counted once)
    totals = df["total"].tolist()

    # Presence in each set for dot matrix
    ru_present = ((df["ru_only_count"] + df["common_count"]) > 0).tolist()
    eu_present = ((df["eu_only_count"] + df["common_count"]) > 0).tolist()

    # --- Plot layout ---
    fig = plt.figure(figsize=(max(12, TOP_N * 1.0), 6), dpi=200)
    gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3.5, 1.2], hspace=0.05)

    ax_bar = fig.add_subplot(gs[0, 0])
    ax_mat = fig.add_subplot(gs[1, 0], sharex=ax_bar)

    x = list(range(len(tags)))

    # Bars (top) - total tags count coverage
    bars = ax_bar.bar(x, totals)
    ax_bar.set_ylabel("Count (RU-only + EU-only + common)")
    ax_bar.set_title(f"Top {TOP_N} Maven SDK tags: RU vs EU")
    ax_bar.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax_bar.set_axisbelow(True)

    # Add RU/EU totals on each bar:
    # RU total (black) and EU total (orange)
    ymax = max(totals) if totals else 0
    pad = max(0.6, ymax * 0.02)

    for i, b in enumerate(bars):
        h = b.get_height()
        if h <= 0:
            continue

        x_center = b.get_x() + b.get_width() / 2.0
        y_text = h + pad

        ru = int(ru_totals[i])
        eu = int(eu_totals[i])

        if ru > 0:
            ax_bar.text(
                x_center - 0.12, y_text, str(ru),
                ha="right", va="bottom", fontsize=9, color="black"
            )
        if eu > 0:
            ax_bar.text(
                x_center + 0.12, y_text, str(eu),
                ha="left", va="bottom", fontsize=9, color="orange"
            )

    # Matrix (bottom)
    y_ru, y_eu = 1, 0
    ax_mat.set_yticks([y_ru, y_eu])
    ax_mat.set_yticklabels(["RU", "EU"])

    ax_mat.hlines([y_ru, y_eu], xmin=-0.5, xmax=len(tags) - 0.5, linewidth=0.8, alpha=0.4)

    ru_x = [i for i, p in enumerate(ru_present) if p]
    eu_x = [i for i, p in enumerate(eu_present) if p]
    ax_mat.scatter(ru_x, [y_ru] * len(ru_x), s=60)
    ax_mat.scatter(eu_x, [y_eu] * len(eu_x), s=60)

    # Connect dots for tags present in both RU and EU
    both_x = [i for i, (r, e) in enumerate(zip(ru_present, eu_present)) if r and e]
    for i in both_x:
        ax_mat.vlines(i, y_eu, y_ru, linewidth=1.0, alpha=0.6)

    ax_mat.set_xticks(x)
    ax_mat.set_xticklabels(tags, rotation=45, ha="right")
    ax_mat.set_xlabel("Maven tags")

    ax_mat.set_ylim(-0.7, 1.7)
    ax_mat.grid(False)

    for spine in ["top", "right"]:
        ax_mat.spines[spine].set_visible(False)
        ax_bar.spines[spine].set_visible(False)

    # Hide x tick labels on bar plot
    plt.setp(ax_bar.get_xticklabels(), visible=False)

    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)

    print("Saved:")
    print(f"  {png_path}")
    print(f"  {svg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
