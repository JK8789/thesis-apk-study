#!/usr/bin/env python3
"""
Paired comparison plots (RU vs EU) for permissions.

Input:
  results/pairs/pair_summary.csv

Produces two paired "slope" charts:
  1) ru_perm_count_local vs eu_perm_count_local
  2) ru_vt_dangerous_perm_count vs eu_vt_dangerous_perm_count

Output (plots only):
  Plots/permissions_pairs/paired_perm_count_local.png
  Plots/permissions_pairs/paired_perm_count_local.svg
  Plots/permissions_pairs/paired_vt_dangerous_perm_count.png
  Plots/permissions_pairs/paired_vt_dangerous_perm_count.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_permissions_paired_comparison.py
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


TITLE_1 = "Paired comparison: total requested permissions (RU vs EU)"
EXPL_1 = (
    "Each line represents a matched RU–EU app pair. The endpoints show the number of locally extracted "
    "Android permissions for the RU and EU app versions."
)

TITLE_2 = "Paired comparison: dangerous permissions (RU vs EU)"
EXPL_2 = (
    "Each line represents a matched RU–EU app pair. The endpoints show the number of VirusTotal-flagged "
    "dangerous Android permissions for the RU and EU app versions."
)


def plot_slope(
    df: pd.DataFrame,
    ru_col: str,
    eu_col: str,
    title: str,
    explanation: str,
    out_png: Path,
    out_svg: Path,
    ylabel: str,
) -> None:
    # Keep only rows with numeric values
    d = df.copy()
    d[ru_col] = pd.to_numeric(d[ru_col], errors="coerce")
    d[eu_col] = pd.to_numeric(d[eu_col], errors="coerce")
    d = d.dropna(subset=[ru_col, eu_col]).reset_index(drop=True)

    # Sort by difference to make the plot more readable
    d["_delta"] = d[ru_col] - d[eu_col]
    d = d.sort_values("_delta", ascending=False).reset_index(drop=True)

    fig = plt.figure(figsize=(10.5, 6.5), dpi=200)
    fig.subplots_adjust(top=0.82)

    fig.suptitle(title, fontsize=16, y=0.97)
    fig.text(0.5, 0.90, explanation, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    # x positions for RU and EU
    x_ru, x_eu = 0, 1

    # Plot each pair as a line
    for _, row in d.iterrows():
        ax.plot(
            [x_ru, x_eu],
            [row[ru_col], row[eu_col]],
            linewidth=1.2,
            alpha=0.55,
        )

    # Overlay points
    ax.scatter([x_ru] * len(d), d[ru_col], s=25)
    ax.scatter([x_eu] * len(d), d[eu_col], s=25)

    # Median markers (helpful summary)
    ru_med = float(d[ru_col].median())
    eu_med = float(d[eu_col].median())
    ax.scatter([x_ru], [ru_med], s=90, marker="D", zorder=4)
    ax.scatter([x_eu], [eu_med], s=90, marker="D", zorder=4)

    ax.text(x_ru, ru_med, f" median={ru_med:.0f}", ha="right", va="center", fontsize=9)
    ax.text(x_eu, eu_med, f" median={eu_med:.0f}", ha="left", va="center", fontsize=9)

    ax.set_xticks([x_ru, x_eu])
    ax.set_xticklabels(["RU app", "EU app"])
    ax.set_ylabel(ylabel)

    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    # Expand margins a bit
    ax.set_xlim(-0.25, 1.25)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    input_path = Path("results/pairs/pairs_summary.csv")
    out_dir = Path("Plots/permissions_pairs")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"Missing input: {input_path}")

    df = pd.read_csv(input_path)

    needed = {
        "ru_perm_count_local",
        "eu_perm_count_local",
        "ru_vt_dangerous_perm_count",
        "eu_vt_dangerous_perm_count",
    }
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}\nFound: {list(df.columns)}")

    plot_slope(
        df=df,
        ru_col="ru_perm_count_local",
        eu_col="eu_perm_count_local",
        title=TITLE_1,
        explanation=EXPL_1,
        out_png=out_dir / "paired_perm_count_local.png",
        out_svg=out_dir / "paired_perm_count_local.svg",
        ylabel="Locally extracted permissions (count)",
    )

    plot_slope(
        df=df,
        ru_col="ru_vt_dangerous_perm_count",
        eu_col="eu_vt_dangerous_perm_count",
        title=TITLE_2,
        explanation=EXPL_2,
        out_png=out_dir / "paired_vt_dangerous_perm_count.png",
        out_svg=out_dir / "paired_vt_dangerous_perm_count.svg",
        ylabel="Dangerous permissions (count)",
    )

    print("Saved plots to:", out_dir)


if __name__ == "__main__":
    main()
