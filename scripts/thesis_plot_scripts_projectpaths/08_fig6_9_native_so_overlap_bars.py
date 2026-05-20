import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Plots" / "thesis_plot_scripts_real"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "results/native/native_summary.csv")

counts = {
    "RU only": int(df.loc[0, "ru_only_count"]),
    "Shared": int(df.loc[0, "common_count"]),
    "EU only": int(df.loc[0, "eu_only_count"]),
}

labels = list(counts.keys())
values = list(counts.values())
colors = ["#0046FF", "#7CB342", "#FB3600"]

fig, ax = plt.subplots(figsize=(7.5, 5))

bars = ax.bar(labels, values, color=colors, width=0.62)

for bar, value in zip(bars, values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        value + 1,
        str(value),
        ha="center",
        va="bottom",
        fontsize=11
    )

ax.set_ylabel("Number of unique native .so library names")
ax.set_title("Unique native .so library names in RU-only, shared, and EU-only sets", fontsize=14, pad=12)
ax.grid(axis="y", linestyle=":", alpha=0.35)

fig.tight_layout()
out = OUT / "fig6_9_native_so_overlap_bars.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
print(out)
