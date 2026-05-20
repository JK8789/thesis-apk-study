
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

# Figure 6.2 replacement
# Keep mirrored bars only here, as professor suggested it works well for strong disparity
df = pd.read_csv(DATA / "results/local/extracted_local_manifest_features and lists.csv")
gcol = "group" if "group" in df.columns else "region"
valcol = "dangerous_permissions_count"
app = df.pivot_table(index="pair_id", columns=gcol, values=valcol, aggfunc="first").reset_index()
app = order_pairs(app)
app["ru_neg"] = -app["ru"]
y = np.arange(len(app))

fig, ax = plt.subplots(figsize=(11, 8))
ax.barh(y, app["ru_neg"], color="#3949AB", label="RU")
ax.barh(y, app["eu"], color="#FB8C00", label="EU")
ax.axvline(0, color="#546E7A", linewidth=1)
ax.set_yticks(y)
ax.set_yticklabels([PAIR_LABELS[p] for p in app["pair_id"]], fontsize=10)
ticks = ax.get_xticks()
ax.set_xticklabels([str(abs(int(t))) if abs(t-round(t))<1e-6 else f"{abs(t):.0f}" for t in ticks])
for i, row in enumerate(app.itertuples(index=False)):
    ax.text(row.ru_neg - 0.3, i, f"{int(row.ru)}", va="center", ha="right", fontsize=9, color="#3949AB")
    ax.text(row.eu + 0.3, i, f"{int(row.eu)}", va="center", ha="left", fontsize=9, color="#FB8C00")
ax.set_xlabel("Dangerous permissions count")
ax.set_title("Dangerous permissions per matched pair (mirrored view)", fontsize=16, pad=12)
ax.grid(axis="x", linestyle=":", alpha=0.4)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig(OUT / "fig6_2_dangerous_permissions_mirrored.png", dpi=300, bbox_inches="tight")
print(OUT / "fig6_2_dangerous_permissions_mirrored.png")
