#!/usr/bin/env python3
"""
Dataset 2 store comparison plots.

Input:
  dataset2/dataset2.csv

Outputs:
  Plots/dataset2_pairs/dataset2_store_comparisons/*.png
  Plots/dataset2_pairs/dataset2_store_comparisons/*.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_dataset2_store_comparisons.py
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


INPUT_PATH = Path("dataset2/dataset2.csv")
OUT_DIR = Path("Plots/dataset2_pairs/dataset2_store_comparisons")

RUSTORE_COLOR = "tab:blue"
GPLAY_COLOR = "tab:orange"


def require_cols(df: pd.DataFrame, cols: set[str]) -> None:
    missing = cols - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}\nFound: {list(df.columns)}")


def normalize_store(x: str) -> str:
    s = str(x).strip().lower()
    if "rustore" in s:
        return "rustore"
    if "google play" in s:
        return "google_play"
    return s


def build_pair_rows(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Builds one row per apk_filename in original file order.
    Left side = RuStore
    Right side = Google Play
    """
    d = df.copy()
    d["store_norm"] = d["store"].apply(normalize_store)

    pair_order = pd.unique(d["apk_filename"])
    rows = []

    for apk in pair_order:
        g = d[d["apk_filename"] == apk]

        g_ru = g[g["store_norm"] == "rustore"]
        g_gp = g[g["store_norm"] == "google_play"]

        if g_ru.empty or g_gp.empty:
            continue

        ru = g_ru.iloc[0]
        gp = g_gp.iloc[0]

        rows.append(
            {
                "label": str(apk),
                "rustore_val": int(ru[value_col]),
                "google_play_val": int(gp[value_col]),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        raise SystemExit(f"No valid RuStore/Google Play pairs found for {value_col}")
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

    # left side = RuStore, right side = Google Play
    ru_vals = (-plot_df["rustore_val"]).tolist()
    gp_vals = plot_df["google_play_val"].tolist()

    max_abs = float(max(plot_df["rustore_val"].max(), plot_df["google_play_val"].max()))
    xlim = max_abs * 1.15 + 0.5

    fig = plt.figure(figsize=(12, max(6, len(plot_df) * 0.34)), dpi=200)
    fig.subplots_adjust(top=0.86, right=0.82)

    fig.suptitle(title, fontsize=16, y=0.97)
    fig.text(0.5, 0.91, sentence, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    ax.barh(y, ru_vals, color=RUSTORE_COLOR, label="RuStore")
    ax.barh(y, gp_vals, color=GPLAY_COLOR, label="Google Play")

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

    # value labels
    for yi, (ru, gp) in enumerate(zip(plot_df["rustore_val"].tolist(), plot_df["google_play_val"].tolist())):
        if ru > 0:
            ax.text(-ru - 0.2, yi, str(int(ru)), va="center", ha="right", fontsize=8, color=RUSTORE_COLOR)
        if gp > 0:
            ax.text(gp + 0.2, yi, str(int(gp)), va="center", ha="left", fontsize=8, color=GPLAY_COLOR)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def grouped_size_plot(df: pd.DataFrame, out_png: Path, out_svg: Path) -> None:
    d = df.copy()
    d["store_norm"] = d["store"].apply(normalize_store)

    pair_order = pd.unique(d["apk_filename"])
    rows = []

    for apk in pair_order:
        g = d[d["apk_filename"] == apk]
        g_ru = g[g["store_norm"] == "rustore"]
        g_gp = g[g["store_norm"] == "google_play"]

        if g_ru.empty or g_gp.empty:
            continue

        ru = g_ru.iloc[0]
        gp = g_gp.iloc[0]

        rows.append(
            {
                "label": str(apk),
                "rustore_mb": float(ru["size_bytes"]) / (1024 * 1024),
                "google_play_mb": float(gp["size_bytes"]) / (1024 * 1024),
            }
        )

    plot_df = pd.DataFrame(rows)
    if plot_df.empty:
        raise SystemExit("No valid size pairs found.")

    x = list(range(len(plot_df)))
    w = 0.38

    fig = plt.figure(figsize=(12, 6.5), dpi=200)
    fig.subplots_adjust(top=0.84, bottom=0.26)

    fig.suptitle("APK size comparison across stores", fontsize=16, y=0.97)
    fig.text(
        0.5,
        0.91,
        "Bars compare APK file size in megabytes for the Google Play and RuStore versions of each app.",
        ha="center",
        va="top",
        fontsize=10,
    )

    ax = fig.add_subplot(111)

    ax.bar([i - w/2 for i in x], plot_df["google_play_mb"], width=w, color=GPLAY_COLOR, label="Google Play")
    ax.bar([i + w/2 for i in x], plot_df["rustore_mb"], width=w, color=RUSTORE_COLOR, label="RuStore")

    ax.set_xticks(x)
    ax.set_xticklabels(plot_df["label"].tolist(), rotation=45, ha="right")
    ax.set_ylabel("APK size (MB)")
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")

    ymax = max(
        plot_df["google_play_mb"].max(),
        plot_df["rustore_mb"].max(),
    )
    pad = max(2.0, ymax * 0.015)

    for i, (gp, ru) in enumerate(zip(plot_df["google_play_mb"], plot_df["rustore_mb"])):
        ax.text(i - w/2, gp + pad, f"{gp:.1f}", ha="center", va="bottom", fontsize=8, color=GPLAY_COLOR)
        ax.text(i + w/2, ru + pad, f"{ru:.1f}", ha="center", va="bottom", fontsize=8, color=RUSTORE_COLOR)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_PATH.exists():
        raise SystemExit(f"Missing input: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)

    require_cols(
        df,
        {
            "apk_filename",
            "store",
            "size_bytes",
            "requested_permissions_count",
            "custom_permissions_count",
            "activities_all",
            "activities_exported",
            "services_all",
            "services_exported",
            "receivers_all",
            "receivers_exported",
            "providers_all",
            "providers_exported",
        },
    )

    numeric_cols = [
        "size_bytes",
        "requested_permissions_count",
        "custom_permissions_count",
        "activities_all",
        "activities_exported",
        "services_all",
        "services_exported",
        "receivers_all",
        "receivers_exported",
        "providers_all",
        "providers_exported",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 1 Requested permissions
    plot_df = build_pair_rows(df, "requested_permissions_count")
    mirrored_barplot(
        plot_df,
        title="Requested permissions by app store",
        sentence="Each row compares the number of requested permissions in the RuStore and Google Play versions of the same APK.",
        xlabel="Requested permissions count",
        out_png=OUT_DIR / "mirrored_requested_permissions.png",
        out_svg=OUT_DIR / "mirrored_requested_permissions.svg",
    )

    # 2 Custom permissions
    plot_df = build_pair_rows(df, "custom_permissions_count")
    mirrored_barplot(
        plot_df,
        title="Custom permissions by app store",
        sentence="Each row compares the number of custom permissions in the RuStore and Google Play versions of the same APK.",
        xlabel="Custom permissions count",
        out_png=OUT_DIR / "mirrored_custom_permissions.png",
        out_svg=OUT_DIR / "mirrored_custom_permissions.svg",
    )

    # 3 Exported components
    exported_specs = [
        ("activities_exported", "Exported activities by app store", "exported activities"),
        ("services_exported", "Exported services by app store", "exported services"),
        ("receivers_exported", "Exported receivers by app store", "exported receivers"),
        ("providers_exported", "Exported providers by app store", "exported providers"),
    ]
    for col, title, noun in exported_specs:
        plot_df = build_pair_rows(df, col)
        mirrored_barplot(
            plot_df,
            title=title,
            sentence=f"Each row compares the number of {noun} in the RuStore and Google Play versions of the same APK.",
            xlabel=f"{noun.capitalize()} count",
            out_png=OUT_DIR / f"mirrored_{col}.png",
            out_svg=OUT_DIR / f"mirrored_{col}.svg",
        )

    # 4 All components
    all_specs = [
        ("activities_all", "Activities by app store", "activities"),
        ("services_all", "Services by app store", "services"),
        ("receivers_all", "Receivers by app store", "receivers"),
        ("providers_all", "Providers by app store", "providers"),
    ]
    for col, title, noun in all_specs:
        plot_df = build_pair_rows(df, col)
        mirrored_barplot(
            plot_df,
            title=title,
            sentence=f"Each row compares the total number of {noun} in the RuStore and Google Play versions of the same APK.",
            xlabel=f"{noun.capitalize()} count",
            out_png=OUT_DIR / f"mirrored_{col}.png",
            out_svg=OUT_DIR / f"mirrored_{col}.svg",
        )

    # 5 APK size comparison in MB
    grouped_size_plot(
        df,
        out_png=OUT_DIR / "apk_size_comparison_mb.png",
        out_svg=OUT_DIR / "apk_size_comparison_mb.svg",
    )

    print("Saved plots to:", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
