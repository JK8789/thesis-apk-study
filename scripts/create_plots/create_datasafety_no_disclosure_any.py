#!/usr/bin/env python3
"""
Simple non-disclosure figure for Data Safety.

Shows:
RU apps: 4/20 (20%)
EU apps: 0/20 (0%)

Outputs:
  Plots/datasafety/datasafety_nondisclosure_simple.png
  Plots/datasafety/datasafety_nondisclosure_simple.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_datasafety_nondisclosure_simple.py
"""

from pathlib import Path
import matplotlib.pyplot as plt


# ---- Fixed values (no computation) ----
RU_TOTAL = 20
EU_TOTAL = 20

RU_NO_DISCLOSE = 4
EU_NO_DISCLOSE = 0

RU_PCT = RU_NO_DISCLOSE / RU_TOTAL * 100
EU_PCT = EU_NO_DISCLOSE / EU_TOTAL * 100


TITLE = "Google Play Data Safety: apps disclosing no collected/shared data"
EXPLANATION = (
    "Bars show how many applications do not disclose any collected or shared data "
    "in the Data Safety section (neither collected nor shared)."
)


def main() -> None:
    out_dir = Path("Plots/datasafety")
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "datasafety_nondisclosure_simple.png"
    svg_path = out_dir / "datasafety_nondisclosure_simple.svg"

    # ---- Plot ----
    fig = plt.figure(figsize=(7.5, 5.5), dpi=200)
    fig.subplots_adjust(top=0.82)

    fig.suptitle(TITLE, fontsize=15, y=0.97)
    fig.text(0.5, 0.90, EXPLANATION, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    labels = ["RU", "EU"]
    values = [RU_PCT, EU_PCT]
    counts = [(RU_NO_DISCLOSE, RU_TOTAL), (EU_NO_DISCLOSE, EU_TOTAL)]

    bars = ax.bar(labels, values)

    ax.set_ylabel("Apps (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    # Labels above bars
    for bar, (num, den), pct in zip(bars, counts, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{num}/{den} ({pct:.0f}%)",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)

    print("Saved:")
    print(png_path)
    print(svg_path)


if __name__ == "__main__":
    main()
