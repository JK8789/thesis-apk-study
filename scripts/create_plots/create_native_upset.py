#!/usr/bin/env python3
"""
UpSet-like plot (bars + RU/EU membership dots) for native .so libraries per app.

Input:
  results/native/native_libs_per_app.csv

Output:
  Plots/native_upset/native_upset.png
  Plots/native_upset/native_upset.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_native_upset.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import matplotlib.pyplot as plt


# Change this if you want more or fewer columns (libs)
TOP_N = 30


def split_libs(cell) -> set[str]:
    """Split 'native_so_names' field into a set of libs for one app row."""
    if pd.isna(cell):
        return set()
    parts = [p.strip() for p in str(cell).split(";")]
    return {p for p in parts if p}


def main() -> int:
    input_path = Path("results/native/native_libs_per_app.csv")
    out_dir = Path("Plots/native_upset")
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "native_upset.png"
    svg_path = out_dir / "native_upset.svg"

    if not input_path.exists():
        print(f"Input file not found: {input_path.resolve()}", file=sys.stderr)
        return 1

    df = pd.read_csv(input_path)

    required = {"region", "native_so_names"}
    missing = required - set(df.columns)
    if missing:
        print(f"Missing required columns: {sorted(missing)}", file=sys.stderr)
        print(f"CSV columns: {list(df.columns)}", file=sys.stderr)
        return 1

    # Normalize region labels
    df["region"] = df["region"].astype(str).str.strip().str.lower()
    df = df[df["region"].isin(["ru", "eu"])].copy()

    # For each app row: set of libs (avoid double counting within one app)
    df["libs_set"] = df["native_so_names"].apply(split_libs)

    # Count apps per lib per region (each row = one app)
    ru_apps_by_lib: dict[str, set[int]] = {}
    eu_apps_by_lib: dict[str, set[int]] = {}

    for idx, row in df.iterrows():
        libs = row["libs_set"]
        region = row["region"]
        if not libs:
            continue

        target = ru_apps_by_lib if region == "ru" else eu_apps_by_lib
        for lib in libs:
            target.setdefault(lib, set()).add(idx)

    all_libs = sorted(set(ru_apps_by_lib) | set(eu_apps_by_lib))

    stats = []
    for lib in all_libs:
        ru_count = len(ru_apps_by_lib.get(lib, set()))
        eu_count = len(eu_apps_by_lib.get(lib, set()))
        total = ru_count + eu_count
        stats.append((lib, ru_count, eu_count, total))

    if not stats:
        print("No libraries found to plot (native_so_names empty?).", file=sys.stderr)
        return 1

    stats_df = pd.DataFrame(stats, columns=["lib", "ru_apps", "eu_apps", "total_apps"])
    stats_df = stats_df.sort_values(["total_apps", "lib"], ascending=[False, True])

    # Take TOP_N (for readability)
    plot_df = stats_df.head(TOP_N).reset_index(drop=True)

    libs = plot_df["lib"].tolist()
    totals = plot_df["total_apps"].tolist()
    ru_counts = plot_df["ru_apps"].tolist()
    eu_counts = plot_df["eu_apps"].tolist()

    ru_present = (plot_df["ru_apps"] > 0).tolist()
    eu_present = (plot_df["eu_apps"] > 0).tolist()

    # --- Plot layout (bars on top, membership dots bottom) ---
    fig = plt.figure(figsize=(max(12, TOP_N * 0.55), 6), dpi=200)
    gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3.5, 1.2], hspace=0.05)

    ax_bar = fig.add_subplot(gs[0, 0])
    ax_mat = fig.add_subplot(gs[1, 0], sharex=ax_bar)

    x = list(range(len(libs)))

    # Bars (top) - total apps (RU+EU)
    bars = ax_bar.bar(x, totals)
    ax_bar.set_ylabel("Apps containing lib")
    ax_bar.set_title(f"Native .so libraries: RU vs EU (Top {TOP_N} by app count)")
    ax_bar.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax_bar.set_axisbelow(True)

    # Add RU/EU numbers on each bar:
    # - RU in black
    # - EU in orange
    # - If common -> both will appear
    ymax = max(totals) if totals else 0
    pad = max(0.6, ymax * 0.02)  # vertical padding above bar

    for i, b in enumerate(bars):
        h = b.get_height()
        if h <= 0:
            continue

        # Place labels near the top of bar, slightly separated horizontally
        x_center = b.get_x() + b.get_width() / 2.0
        y_text = h + pad

        ru = ru_counts[i]
        eu = eu_counts[i]

        # RU label (black) if present
        if ru > 0:
            ax_bar.text(
                x_center - 0.12, y_text, str(ru),
                ha="right", va="bottom", fontsize=9, color="black"
            )

        # EU label (orange) if present
        if eu > 0:
            ax_bar.text(
                x_center + 0.12, y_text, str(eu),
                ha="left", va="bottom", fontsize=9, color="orange"
            )

    # Membership matrix (bottom)
    y_ru, y_eu = 1, 0
    ax_mat.set_yticks([y_ru, y_eu])
    ax_mat.set_yticklabels(["RU", "EU"])

    # guide lines
    ax_mat.hlines([y_ru, y_eu], xmin=-0.5, xmax=len(libs) - 0.5, linewidth=0.8, alpha=0.4)

    # Dots
    ru_x = [i for i, p in enumerate(ru_present) if p]
    eu_x = [i for i, p in enumerate(eu_present) if p]
    ax_mat.scatter(ru_x, [y_ru] * len(ru_x), s=60)
    ax_mat.scatter(eu_x, [y_eu] * len(eu_x), s=60)

    # connect dots for libs present in both RU and EU
    both_x = [i for i, (r, e) in enumerate(zip(ru_present, eu_present)) if r and e]
    for i in both_x:
        ax_mat.vlines(i, y_eu, y_ru, linewidth=1.0, alpha=0.6)

    # X labels = lib names
    ax_mat.set_xticks(x)
    ax_mat.set_xticklabels(libs, rotation=60, ha="right")
    ax_mat.set_xlabel("Libraries (.so)")

    # Clean up axes
    ax_mat.set_ylim(-0.7, 1.7)
    ax_mat.grid(False)
    for spine in ["top", "right"]:
        ax_mat.spines[spine].set_visible(False)
        ax_bar.spines[spine].set_visible(False)

    # Hide x tick labels on bar plot (use matrix plot only)
    plt.setp(ax_bar.get_xticklabels(), visible=False)

    # Save
    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)

    print("Saved:")
    print(f"  {png_path}")
    print(f"  {svg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
