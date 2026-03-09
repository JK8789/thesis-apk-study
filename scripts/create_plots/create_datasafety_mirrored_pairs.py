#!/usr/bin/env python3
"""
Mirrored (back-to-back) barplots for Data Safety pair comparison using existing counts.

EU bars extend to the RIGHT, RU bars extend to the LEFT (mirrored using negative values),
but the x-axis is formatted as absolute counts (no negative labels).

Input:
  results/datasafety/datasafety_pairs_purpose.csv

Outputs:
  Plots/datasafety/mirrored_collected_count.png/.svg
  Plots/datasafety/mirrored_shared_count.png/.svg
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


RU_COLOR = "tab:blue"     # RU bars (LEFT)
EU_COLOR = "tab:orange"   # EU bars (RIGHT)

TITLE_COLLECTED = "Data Safety (paired): declared collected data items (RU vs EU)"
EXPL_COLLECTED = (
    "Each row represents a matched RU–EU app pair. RU counts are shown to the left (blue) and EU counts "
    "to the right (orange), using collected_count from the dataset."
)

TITLE_SHARED = "Data Safety (paired): declared shared data items (RU vs EU)"
EXPL_SHARED = (
    "Each row represents a matched RU–EU app pair. RU counts are shown to the left (blue) and EU counts "
    "to the right (orange), using shared_count from the dataset."
)


def mirrored_plot(
    df_pairs: pd.DataFrame,
    value_col: str,
    title: str,
    explanation: str,
    out_png: Path,
    out_svg: Path,
    xlabel: str,
) -> None:
    pair_order = pd.unique(df_pairs["pair_id"])

    rows = []
    for pid in pair_order:
        g = df_pairs[df_pairs["pair_id"] == pid]

        g_ru = g[g["region"].astype(str).str.lower().eq("ru")]
        g_eu = g[g["region"].astype(str).str.lower().eq("eu")]
        if g_ru.empty or g_eu.empty:
            continue

        ru_row = g_ru.iloc[0]
        eu_row = g_eu.iloc[0]

        ru_val = int(ru_row[value_col])
        eu_val = int(eu_row[value_col])

        label = f"{str(ru_row['app_name'])} vs {str(eu_row['app_name'])}"
        rows.append((pid, label, ru_val, eu_val))

    if not rows:
        raise SystemExit(f"No valid RU/EU pairs found for {value_col}. Check 'region' and 'pair_id'.")

    plot_df = pd.DataFrame(rows, columns=["pair_id", "label", "ru_val", "eu_val"])

    y = list(range(len(plot_df)))

    # mirrored values for plotting only
    ru_vals = (-plot_df["ru_val"]).tolist()   # RU left
    eu_vals = (plot_df["eu_val"]).tolist()    # EU right

    max_abs = float(max(plot_df["ru_val"].max(), plot_df["eu_val"].max()))
    xlim = max_abs * 1.15 + 0.5

    fig = plt.figure(figsize=(12, max(6, len(plot_df) * 0.32)), dpi=200)
    fig.subplots_adjust(top=0.86, right=0.82)

    fig.suptitle(title, fontsize=16, y=0.97)
    fig.text(0.5, 0.91, explanation, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    ax.barh(y, ru_vals, color=RU_COLOR, label="RU")
    ax.barh(y, eu_vals, color=EU_COLOR, label="EU")
    ax.axvline(0, linewidth=1.2, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["label"].tolist())

    ax.set_xlim(-xlim, xlim)
    ax.set_xlabel(xlabel)

    # Make axis show absolute counts, not negative numbers
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{int(abs(v))}"))

    ax.grid(axis="x", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    ax.legend(
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
    )

    # labels at bar ends (absolute text)
    for yi, (ru, eu) in enumerate(zip(plot_df["ru_val"].tolist(), plot_df["eu_val"].tolist())):
        if ru > 0:
            ax.text(-ru - 0.2, yi, str(int(ru)), va="center", ha="right", fontsize=8, color=RU_COLOR)
        if eu > 0:
            ax.text(eu + 0.2, yi, str(int(eu)), va="center", ha="left", fontsize=8, color=EU_COLOR)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    input_path = Path("results/datasafety/datasafety_pairs_purpose.csv")
    out_dir = Path("Plots/datasafety")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"Missing input: {input_path}")

    df = pd.read_csv(input_path)

    needed = {"region", "pair_id", "app_name", "collected_count", "shared_count"}
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}\nFound: {list(df.columns)}")

    # do not sort: keep file order
    df["collected_count"] = pd.to_numeric(df["collected_count"], errors="coerce").fillna(0).astype(int)
    df["shared_count"] = pd.to_numeric(df["shared_count"], errors="coerce").fillna(0).astype(int)

    mirrored_plot(
        df_pairs=df,
        value_col="collected_count",
        title=TITLE_COLLECTED,
        explanation=EXPL_COLLECTED,
        out_png=out_dir / "mirrored_collected_count.png",
        out_svg=out_dir / "mirrored_collected_count.svg",
        xlabel="Declared collected data items (count)",
    )

    mirrored_plot(
        df_pairs=df,
        value_col="shared_count",
        title=TITLE_SHARED,
        explanation=EXPL_SHARED,
        out_png=out_dir / "mirrored_shared_count.png",
        out_svg=out_dir / "mirrored_shared_count.svg",
        xlabel="Declared shared data items (count)",
    )

    print("Saved plots to:", out_dir)


if __name__ == "__main__":
    main()
