
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

df = pd.read_csv(DATA / "dataset2/dataset2.csv")
pivot = df.pivot_table(index="apk_filename", columns="store", values="custom_permissions_count", aggfunc="first").reset_index().sort_values("apk_filename")
y = np.arange(len(pivot))
fig, ax = plt.subplots(figsize=(9,6))
for i, row in enumerate(pivot.itertuples(index=False)):
    ax.plot([row[1], row[2]], [i, i], color="#CFD8DC", linewidth=2)
ax.scatter(pivot["Google Play"], y, color="#8E24AA", s=70, label="Google Play", marker="o")
ax.scatter(pivot["RuStore"], y, color="#00897B", s=70, label="RuStore", marker="s")
ax.set_yticks(y)
ax.set_yticklabels(pivot["apk_filename"], fontsize=9)
ax.set_xlabel("Custom permissions count")
ax.set_title("Custom permissions by store", fontsize=16, pad=12)
ax.grid(axis="x", linestyle=":", alpha=0.35)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT / "fig6_14_custom_permissions_dot.png", dpi=300, bbox_inches="tight")
print(OUT / "fig6_14_custom_permissions_dot.png")
