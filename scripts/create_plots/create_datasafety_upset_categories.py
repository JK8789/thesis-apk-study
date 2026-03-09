#!/usr/bin/env python3
"""
UpSet-style plot (bars + RU/EU membership matrix) for Data Safety.

For each app:
  - Blue bar: collected_count
  - Orange bar: shared_count
  - Bottom dots: RU (black) / EU (green)

Input:
  results/datasafety/datasafety_pairs_purpose.csv

Output:
  Plots/datasafety/datasafety_upset_collected_shared.png
  Plots/datasafety/datasafety_upset_collected_shared.svg

Run:
  python3 scripts/create_plots/create_datasafety_upset_collected_shared.py
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


TITLE = "Data Safety: declared collected vs shared data types per app (RU vs EU)"
EXPLANATION = (
    "Bars show how many data types each application declares as collected (blue) and shared (orange); "
    "dots indicate whether the app belongs to the RU or EU dataset."
)

# Bars
COL_BAR_COLOR = "tab:blue"
SHR_BAR_COLOR = "tab:orange"

# Dots/lines (different from bars)
RU_DOT_COLOR = "black"
EU_DOT_COLOR = "tab:green"


def main() -> None:
    input_path = Path("results/datasafety/datasafety_pairs_purpose.csv")
    out_dir = Path("Plots/datasafety")
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "datasafety_upset_collected_shared.png"
    svg_path = out_dir / "datasafety_upset_collected_shared.svg"

    df = pd.read_csv(input_path)

    needed = {"app_name", "region", "collected_count", "shared_count"}
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}. Found: {list(df.columns)}")

    df["region"] = df["region"].astype(str).str.strip().str.lower()

    # Sort for nicer visualization
    df = df.sort_values(["collected_count", "shared_count", "app_name"], ascending=[False, False, True]).reset_index(drop=True)

    apps = df["app_name"].astype(str).tolist()
    collected = df["collected_count"].astype(int).tolist()
    shared = df["shared_count"].astype(int).tolist()
    regions = df["region"].tolist()

    n = len(apps)
    x = list(range(n))
    w = 0.38  # per-series bar width

    # ---- Figure ----
    fig = plt.figure(figsize=(max(13, n * 0.45), 6), dpi=200)
    fig.subplots_adjust(top=0.82, bottom=0.27, hspace=0.02)

    fig.suptitle(TITLE, fontsize=16, y=0.97)
    fig.text(0.5, 0.90, EXPLANATION, ha="center", va="top", fontsize=10)

    gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3.4, 1.2])
    ax_bar = fig.add_subplot(gs[0, 0])
    ax_dot = fig.add_subplot(gs[1, 0], sharex=ax_bar)

    # ---- Bars ----
    # Collected = LEFT bar, Shared = RIGHT bar
    ax_bar.bar([i - w/2 for i in x], collected, width=w, color=COL_BAR_COLOR, label="Collected")
    ax_bar.bar([i + w/2 for i in x], shared, width=w, color=SHR_BAR_COLOR, label="Shared")

    ax_bar.set_ylabel("Declared data types")
    ax_bar.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax_bar.set_axisbelow(True)
    ax_bar.legend(frameon=False, loc="upper right")

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels([])
    ax_bar.tick_params(axis="x", length=0)

    # ---- Numbers above bars (match your requirement) ----
    # Collected (blue) above LEFT bar, Shared (orange) above RIGHT bar
    ymax = max([0] + [max(c, s) for c, s in zip(collected, shared)])
    pad = max(0.6, ymax * 0.03)

    for i, (c, s) in enumerate(zip(collected, shared)):
        top = max(c, s)
        y_text = top + pad

        if c > 0:
            ax_bar.text(
                i - 0.18, y_text, str(c),
                ha="center", va="bottom", fontsize=9, color=COL_BAR_COLOR
            )
        if s > 0:
            ax_bar.text(
                i + 0.18, y_text, str(s),
                ha="center", va="bottom", fontsize=9, color=SHR_BAR_COLOR
            )

    # ---- Dot matrix (RU/EU) ----
    y_eu = 0
    y_ru = 1

    # Guide lines match dot colors
    ax_dot.hlines(y_ru, -0.5, n - 0.5, color=RU_DOT_COLOR, linewidth=1.6, alpha=0.6)
    ax_dot.hlines(y_eu, -0.5, n - 0.5, color=EU_DOT_COLOR, linewidth=1.6, alpha=0.6)

    ru_x = [i for i, r in enumerate(regions) if r == "ru"]
    eu_x = [i for i, r in enumerate(regions) if r == "eu"]

    ax_dot.scatter(ru_x, [y_ru] * len(ru_x), s=60, color=RU_DOT_COLOR, zorder=3)
    ax_dot.scatter(eu_x, [y_eu] * len(eu_x), s=60, color=EU_DOT_COLOR, zorder=3)

    ax_dot.set_yticks([y_ru, y_eu])
    ax_dot.set_yticklabels(["RU", "EU"])

    ax_dot.set_xticks(x)
    ax_dot.set_xticklabels(apps, rotation=60, ha="right")
    ax_dot.set_xlabel("Applications", labelpad=10)

    ax_dot.set_ylim(-0.6, 1.6)
    ax_dot.grid(False)

    for spine in ["top", "right"]:
        ax_bar.spines[spine].set_visible(False)
        ax_dot.spines[spine].set_visible(False)

    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)

    print("Saved:")
    print(png_path)
    print(svg_path)


if __name__ == "__main__":
    main()
