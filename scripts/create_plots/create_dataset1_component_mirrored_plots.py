#!/usr/bin/env python3
"""
Mirrored component comparison plots for baseline results.

Inputs:
  results/baseline/component_counts.csv
  results/baseline/pair_order.csv

Outputs:
  Plots/baseline_components_mirrored/*.png
  Plots/baseline_components_mirrored/*.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_baseline_component_mirrored_plots.py
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


COUNTS_PATH = Path("results/baseline/component_counts.csv")
ORDER_PATH = Path("results/baseline/pair_order.csv")
OUT_DIR = Path("Plots/baseline_components_mirrored")

RU_COLOR = "tab:blue"
EU_COLOR = "tab:orange"

PLOT_SPECS = [
    ("activities_local", "Activities by app", "Number of activities declared in each paired app version."),
    ("services_local", "Services by app", "Number of services declared in each paired app version."),
    ("receivers_local", "Receivers by app", "Number of broadcast receivers declared in each paired app version."),
    ("providers_local", "Providers by app", "Number of content providers declared in each paired app version."),
    ("exported_act_true", "Exported activities by app", "Number of exported activities declared in each paired app version."),
    ("exported_srv_true", "Exported services by app", "Number of exported services declared in each paired app version."),
    ("exported_rcv_true", "Exported receivers by app", "Number of exported receivers declared in each paired app version."),
    ("exported_prv_true", "Exported providers by app", "Number of exported providers declared in each paired app version."),
    ("Total_components", "Total components by app", "Total number of Android components declared in each paired app version."),
    ("Total_exported_components", "Total exported components by app", "Total number of exported Android components declared in each paired app version."),
]


def require_cols(df: pd.DataFrame, cols: set[str], name: str) -> None:
    missing = cols - set(df.columns)
    if missing:
        raise SystemExit(f"{name}: missing columns {sorted(missing)}; found {list(df.columns)}")


def build_pair_rows(counts_df: pd.DataFrame, order_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Builds rows in the exact pair_id order from order_df.
    Uses sha256 to map RU/EU rows to component counts.
    Y-axis label becomes:
      'RU app_name vs EU app_name'
    """
    counts = counts_df.copy()
    order = order_df.copy()

    counts["sha256"] = counts["sha256"].astype(str).str.strip().str.upper()
    order["sha256"] = order["sha256"].astype(str).str.strip().str.upper()
    order["region"] = order["region"].astype(str).str.strip().str.lower()
    order["pair_id"] = order["pair_id"].astype(str).str.strip()
    order["app_name"] = order["app_name"].astype(str).str.strip()

    pair_order = pd.unique(order["pair_id"])

    rows = []
    for pid in pair_order:
        g = order[order["pair_id"] == pid]
        g_ru = g[g["region"] == "ru"]
        g_eu = g[g["region"] == "eu"]
        if g_ru.empty or g_eu.empty:
            continue

        ru_row = g_ru.iloc[0]
        eu_row = g_eu.iloc[0]

        ru_sha = str(ru_row["sha256"]).upper()
        eu_sha = str(eu_row["sha256"]).upper()

        ru_match = counts[counts["sha256"] == ru_sha]
        eu_match = counts[counts["sha256"] == eu_sha]
        if ru_match.empty or eu_match.empty:
            continue

        ru_val = int(ru_match.iloc[0][value_col])
        eu_val = int(eu_match.iloc[0][value_col])

        label = f"{ru_row['app_name']} vs {eu_row['app_name']}"

        rows.append(
            {
                "pair_id": pid,
                "label": label,
                "ru_val": ru_val,
                "eu_val": eu_val,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        raise SystemExit(f"No valid RU/EU pair rows produced for column '{value_col}'.")
    return out


def mirrored_barplot(
    plot_df: pd.DataFrame,
    title: str,
    sentence: str,
    xlabel: str,
    out_png: Path,
    out_svg: Path,
) -> None:
    y = list(range(len(plot_df)))
    ru_vals = (-plot_df["ru_val"]).tolist()
    eu_vals = plot_df["eu_val"].tolist()

    max_abs = float(max(plot_df["ru_val"].max(), plot_df["eu_val"].max()))
    xlim = max_abs * 1.15 + 0.5

    fig = plt.figure(figsize=(12, max(6, len(plot_df) * 0.42)), dpi=200)
    fig.subplots_adjust(top=0.86, right=0.82)

    fig.suptitle(title, fontsize=16, y=0.97)
    fig.text(0.5, 0.91, sentence, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    ax.barh(y, ru_vals, color=RU_COLOR, label="RU")
    ax.barh(y, eu_vals, color=EU_COLOR, label="EU")

    ax.axvline(0, linewidth=1.2, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["label"].tolist())

    ax.set_xlim(-xlim, xlim)
    ax.set_xlabel(xlabel)

    # show positive counts on both sides
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{int(abs(v))}"))

    ax.grid(axis="x", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    ax.legend(
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
    )

    for yi, (ru, eu) in enumerate(zip(plot_df["ru_val"].tolist(), plot_df["eu_val"].tolist())):
        if ru > 0:
            ax.text(-ru - 0.2, yi, str(int(ru)), va="center", ha="right", fontsize=8, color=RU_COLOR)
        if eu > 0:
            ax.text(eu + 0.2, yi, str(int(eu)), va="center", ha="left", fontsize=8, color=EU_COLOR)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not COUNTS_PATH.exists():
        raise SystemExit(f"Missing counts input: {COUNTS_PATH}")
    if not ORDER_PATH.exists():
        raise SystemExit(f"Missing order input: {ORDER_PATH}")

    counts_df = pd.read_csv(COUNTS_PATH)
    order_df = pd.read_csv(ORDER_PATH)

    require_cols(
        counts_df,
        {
            "sha256",
            "activities_local",
            "services_local",
            "receivers_local",
            "providers_local",
            "exported_act_true",
            "exported_srv_true",
            "exported_rcv_true",
            "exported_prv_true",
            "Total_components",
            "Total_exported_components",
        },
        name=str(COUNTS_PATH),
    )

    require_cols(
        order_df,
        {"region", "category", "pair_id", "app_name", "sha256"},
        name=str(ORDER_PATH),
    )

    numeric_cols = [
        "activities_local",
        "services_local",
        "receivers_local",
        "providers_local",
        "exported_act_true",
        "exported_srv_true",
        "exported_rcv_true",
        "exported_prv_true",
        "Total_components",
        "Total_exported_components",
    ]
    for col in numeric_cols:
        counts_df[col] = pd.to_numeric(counts_df[col], errors="coerce").fillna(0).astype(int)

    for col, short_title, sentence_core in PLOT_SPECS:
        plot_df = build_pair_rows(counts_df, order_df, col)

        mirrored_barplot(
            plot_df=plot_df,
            title=f" {short_title}",
            sentence=f"Each row represents a matched RU–EU app pair. {sentence_core} RU is shown on the left and EU on the right.",
            xlabel=f"{col} (count)",
            out_png=OUT_DIR / f"{col}.png",
            out_svg=OUT_DIR / f"{col}.svg",
        )

    print("Saved plots to:", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
