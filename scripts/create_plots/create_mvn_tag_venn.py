#!/usr/bin/env python3
"""
Equal-size Venn-style plot(s) for Maven SDK tags (RU vs EU), with counts as text.

Input:
  results/mvnrepo_dict/venn_counts_by_tag.csv

Expected columns (case-insensitive):
  tag
  ru_only_count
  eu_only_count
  common_count

Output directory:
  Plots/mvn_venn/

For each tag (row), saves:
  <tag>_venn.png
  <tag>_venn.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_mvn_tag_venn_equal.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle


EXPLANATION = (
    "Counts denote unique Maven SDK libraries found only in RU apps, only in EU apps, or shared by both "
    "(20 apps per region)."
)


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None


def slugify(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9._-]+", "", text)
    return text or "tag"


def draw_equal_venn(ax, ru_only: int, eu_only: int, common: int) -> None:
    # Fixed geometry (equal circles)
    r = 1.2
    dx = 1.0  # overlap amount (smaller -> more overlap)

    left_center = (-dx / 2.0, 0.0)
    right_center = (dx / 2.0, 0.0)

    # Nice colors
    ru_color = "#4C78A8"   # blue
    eu_color = "#54A24B"   # green
    edge_color = "#2F2F2F"

    left = Circle(left_center, r, facecolor=ru_color, alpha=0.55, edgecolor=edge_color, linewidth=2)
    right = Circle(right_center, r, facecolor=eu_color, alpha=0.55, edgecolor=edge_color, linewidth=2)
    ax.add_patch(left)
    ax.add_patch(right)

    # Labels RU/EU
    ax.text(left_center[0], -r - 0.35, "RU", ha="center", va="top", fontsize=22)
    ax.text(right_center[0], -r - 0.35, "EU", ha="center", va="top", fontsize=22)

    # Count labels
    ax.text(left_center[0] - 0.55, 0.0, str(ru_only), ha="center", va="center", fontsize=26, color="black")
    ax.text(0.0, 0.0, str(common), ha="center", va="center", fontsize=28, color="black", fontweight="bold")
    ax.text(right_center[0] + 0.55, 0.0, str(eu_only), ha="center", va="center", fontsize=26, color="black")

    # Clean axes
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-2.2, 2.2)
    ax.set_ylim(-1.9, 1.9)
    ax.axis("off")


def main() -> int:
    input_path = Path("results/mvnrepo_dict/venn_counts_by_tag.csv")
    out_dir = Path("Plots/mvn_venn")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Input file not found: {input_path.resolve()}", file=sys.stderr)
        return 1

    df = pd.read_csv(input_path)

    tag_col = pick_col(df, ["tag", "mvn_tag", "category", "name"])
    ru_col = pick_col(df, ["ru_only_count", "ru_only", "ru"])
    eu_col = pick_col(df, ["eu_only_count", "eu_only", "eu"])
    common_col = pick_col(df, ["common_count", "common", "intersection", "intersect", "shared"])

    missing = [n for n, c in [("tag", tag_col), ("ru_only", ru_col), ("eu_only", eu_col), ("common", common_col)] if c is None]
    if missing:
        print(
            "Could not find required columns in CSV.\n"
            f"Missing: {missing}\n"
            f"CSV columns: {list(df.columns)}\n"
            "Expected something like: tag, ru_only_count, eu_only_count, common_count",
            file=sys.stderr,
        )
        return 1

    made_any = False

    for i, row in df.iterrows():
        tag = str(row[tag_col]).strip() if tag_col else f"tag_{i+1}"
        if not tag or tag.lower() == "nan":
            tag = f"tag_{i+1}"

        try:
            ru_only = int(row[ru_col])
            eu_only = int(row[eu_col])
            common = int(row[common_col])
        except Exception as e:
            print(f"Row {i}: failed to parse counts for tag '{tag}': {e}", file=sys.stderr)
            continue

        if any(x < 0 for x in (ru_only, eu_only, common)):
            print(f"Row {i}: negative counts for tag '{tag}', skipping.", file=sys.stderr)
            continue

        # Figure with title + explanatory sentence (under the title)
        fig = plt.figure(figsize=(7, 7), dpi=200)
        fig.subplots_adjust(top=0.86)

        fig.suptitle(f"Maven SDKs by tag: {tag}", fontsize=24, y=0.97)
        fig.text(0.5, 0.91, EXPLANATION, ha="center", va="top", fontsize=10)

        ax = fig.add_subplot(111)
        draw_equal_venn(ax, ru_only=ru_only, eu_only=eu_only, common=common)

        base = slugify(tag)
        png_path = out_dir / f"{base}_venn.png"
        svg_path = out_dir / f"{base}_venn.svg"

        fig.savefig(png_path, bbox_inches="tight")
        fig.savefig(svg_path, bbox_inches="tight")
        plt.close(fig)

        made_any = True
        print(f"Saved: {png_path}")
        print(f"Saved: {svg_path}")

    if not made_any:
        print("No plots created (check CSV content/columns).", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
