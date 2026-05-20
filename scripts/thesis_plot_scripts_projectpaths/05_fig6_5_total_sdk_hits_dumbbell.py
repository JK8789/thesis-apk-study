
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

df = pd.read_csv(DATA / "data/dicts/mvnrepo/mvn_repo_summary.csv")
valcol = "maven_total_hits" if "maven_total_hits" in df.columns else ("hits_total" if "hits_total" in df.columns else None)
if valcol is None:
    cand = [c for c in df.columns if "hit" in c.lower() and "pair" not in c.lower()]
    valcol = cand[0]
gcol = "group" if "group" in df.columns else "region"
app = df.pivot_table(index="pair_id", columns=gcol, values=valcol, aggfunc="first").reset_index()
app = order_pairs(app)
y = np.arange(len(app))

fig, ax = plt.subplots(figsize=(11, 8))
for i, row in enumerate(app.itertuples(index=False)):
    ax.plot([row.ru, row.eu], [i, i], color="#D7CCC8", linewidth=2)
ax.scatter(app["ru"], y, s=90, color="#6D4C41", label="RU", marker="D")
ax.scatter(app["eu"], y, s=90, color="#26A69A", label="EU", marker="D")
ax.set_yticks(y)
ax.set_yticklabels([PAIR_LABELS[p] for p in app["pair_id"]], fontsize=10)
ax.set_xlabel("Detected Maven SDK hits")
ax.set_title("Total detected Maven SDK hits by matched pair", fontsize=16, pad=12)
ax.grid(axis="x", linestyle=":", alpha=0.35)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT / "fig6_5_total_sdk_hits_dumbbell.png", dpi=300, bbox_inches="tight")
print(OUT / "fig6_5_total_sdk_hits_dumbbell.png")
