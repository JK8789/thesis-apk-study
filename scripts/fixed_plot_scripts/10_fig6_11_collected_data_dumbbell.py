import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Plots" / "thesis_plot_scripts_projectpaths"
OUT.mkdir(parents=True, exist_ok=True)

PAIR_LABELS = {
    "maps": "Yandex Maps vs Google Maps",
    "taxi": "Yandex Go Taxi vs Bolt",
    "rail1": "RZD vs DB Navigator",
    "rail2": "Yandex Trains vs Mobiliteit.lu",
    "ecom1": "Ozon vs Amazon Shopping",
    "ecom2": "Wildberries vs Zalando",
    "ecom3": "Yandex Market vs bol",
    "ecom4": "Avito vs Vinted",
    "bank1": "Sberbank vs BGL",
    "bank2": "Tinkoff vs ING Luxembourg",
    "bank3": "Alfa Bank vs Revolut",
    "bank4": "VTB vs BILnet",
    "health": "EMIAS.INFO vs Doctena",
    "social1": "VK vs Facebook",
    "social2": "OK vs X",
    "msg1": "MAX vs WhatsApp",
    "msg2": "Yandex Telemost vs Telegram",
    "gov1": "Gosuslugi vs MyGuichet.lu",
    "gov2": "Nalogi FL vs impots.gouv",
    "gov3": "Gosuslugi Biometria vs itsme",
}

df = pd.read_csv(ROOT / "results/datasafety/datasafety_pairs_purpose.csv")
df.columns = [c.strip() for c in df.columns]

required = ["region", "pair_id", "collected_count"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}\nAvailable columns: {df.columns.tolist()}")

wide = df.pivot_table(
    index="pair_id",
    columns="region",
    values="collected_count",
    aggfunc="first"
).reset_index()

wide = wide.dropna(subset=["ru", "eu"]).copy()

# Better ordering: strongest EU>RU differences first, then stronger RU>EU below
wide["pair_min"] = wide[["ru", "eu"]].min(axis=1)
wide["pair_max"] = wide[["ru", "eu"]].max(axis=1)
wide["eu_minus_ru"] = wide["eu"] - wide["ru"]

wide = wide.sort_values(
    ["pair_min", "pair_max", "eu_minus_ru"],
    ascending=[True, True, False]
).reset_index(drop=True)

y = np.arange(len(wide))

fig, ax = plt.subplots(figsize=(10.8, 8.0))

for i, row in enumerate(wide.itertuples(index=False)):
    ax.plot([row.ru, row.eu], [i, i], color="#C9D1D9", linewidth=2, zorder=1)

ru_color = "#3852B4"
eu_color = "#F08D39"

ax.scatter(wide["ru"], y, s=65, marker="o", color=ru_color, label="RU", zorder=3)
ax.scatter(wide["eu"], y, s=65, marker="D", color=eu_color, label="EU", zorder=3)

for i, row in enumerate(wide.itertuples(index=False)):
    ax.text(row.ru - 0.20, i + 0.07, f"{int(row.ru)}",
            ha="right", va="bottom", fontsize=14, color=ru_color)
    ax.text(row.eu + 0.20, i + 0.07, f"{int(row.eu)}",
            ha="left", va="bottom", fontsize=14, color=eu_color)
ax.tick_params(axis='x', labelsize=14)
ax.set_yticks(y)
ax.set_yticklabels([PAIR_LABELS.get(p, p) for p in wide["pair_id"]], fontsize=14)
ax.set_xlabel("Number of declared collected data categories", fontsize=14)
ax.set_title("Collected data categories by matched RU-EU pair", fontsize=14, pad=14)

# Lighter grid
ax.grid(axis="x", linestyle=":", linewidth=0.8, alpha=0.18)

# Cleaner frame
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Legend just below title
ax.legend(
    frameon=False,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.02),
    ncol=2,
    handletextpad=0.5,
    columnspacing=1.4,
    fontsize=14
)

fig.tight_layout()
out = OUT / "fig6_11_collected_data_dumbbell.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
print(out)
