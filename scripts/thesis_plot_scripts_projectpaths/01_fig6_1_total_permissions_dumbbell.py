
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT
OUT = ROOT / "Plots" / "thesis_plot_scripts_real"
OUT.mkdir(parents=True, exist_ok=True)

PAIR_ORDER = ['maps', 'taxi', 'rail1', 'rail2', 'ecom1', 'ecom2', 'ecom3', 'ecom4', 'bank1', 'bank2', 'bank3', 'bank4', 'health', 'social1', 'social2', 'msg1', 'msg2', 'gov1', 'gov2', 'gov3']
PAIR_LABELS = {
    'maps': 'Yandex Maps vs Google Maps',
    'taxi': 'Yandex Go Taxi vs Bolt',
    'rail1': 'RZD vs DB Navigator',
    'rail2': 'Yandex Trains vs Mobiliteit.lu',
    'ecom1': 'Ozon vs Amazon Shopping',
    'ecom2': 'Wildberries vs Zalando',
    'ecom3': 'Yandex Market vs bol',
    'ecom4': 'Avito vs Vinted',
    'bank1': 'Sberbank vs BGL',
    'bank2': 'Tinkoff vs ING Luxembourg',
    'bank3': 'Alfa Bank vs Revolut',
    'bank4': 'VTB vs BILnet',
    'health': 'EMIAS.INFO vs Doctena',
    'social1': 'VK vs Facebook',
    'social2': 'OK vs X',
    'msg1': 'MAX vs WhatsApp',
    'msg2': 'Yandex Telemost vs Telegram',
    'gov1': 'Gosuslugi vs MyGuichet.lu',
    'gov2': 'Nalogi FL vs impots.gouv',
    'gov3': 'Gosuslugi Biometria vs itsme',
}


def order_pairs(df, col="pair_id"):
    df = df.copy()
    df[col] = pd.Categorical(df[col], categories=PAIR_ORDER, ordered=True)
    return df.sort_values(col)

# Figure 6.1 replacement
# Dumbbell plot: total requested permissions in DPW
df = pd.read_csv(DATA / "results/local/extracted_local_manifest_features and lists.csv")
gcol = "group" if "group" in df.columns else "region"
valcol = "total_permissions_count"
app = df.pivot_table(index="pair_id", columns=gcol, values=valcol, aggfunc="first").reset_index()
app = order_pairs(app)
y = np.arange(len(app))

fig, ax = plt.subplots(figsize=(11, 8))
for i, row in enumerate(app.itertuples(index=False)):
    ax.plot([row.eu, row.ru], [i, i], color="#B0BEC5", linewidth=2, zorder=1)
ax.scatter(app["ru"], y, s=80, color="#3852B4", label="RU", zorder=3)
ax.scatter(app["eu"], y, s=80, color="#F08D39", label="EU", zorder=3)

for i, row in enumerate(app.itertuples(index=False)):
    ax.text(row.ru + 0.8, i + 0.12, f"{int(row.ru)}", fontsize=9, color="#1565C0")
    ax.text(row.eu + 0.8, i - 0.28, f"{int(row.eu)}", fontsize=9, color="#EF6C00")

ax.set_yticks(y)
ax.set_yticklabels([PAIR_LABELS[p] for p in app["pair_id"]], fontsize=10)
ax.set_xlabel("Requested permissions count")
ax.set_title("Total requested permissions by matched RU-EU pair", fontsize=16, pad=12)
ax.grid(axis="x", linestyle=":", alpha=0.4)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig(OUT / "fig6_1_total_permissions_dumbbell.png", dpi=300, bbox_inches="tight")
print(OUT / "fig6_1_total_permissions_dumbbell.png")
