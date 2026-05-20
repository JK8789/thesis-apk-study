
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
PAIR_LABELS = {
    'maps':'Yandex Maps vs Google Maps','taxi':'Yandex Go Taxi vs Bolt','rail1':'RZD vs DB Navigator','rail2':'Yandex Trains vs Mobiliteit.lu',
    'ecom1':'Ozon vs Amazon Shopping','ecom2':'Wildberries vs Zalando','ecom3':'Yandex Market vs bol','ecom4':'Avito vs Vinted',
    'bank1':'Sberbank vs BGL','bank2':'Tinkoff vs ING Luxembourg','bank3':'Alfa Bank vs Revolut','bank4':'VTB vs BILnet',
    'health':'EMIAS.INFO vs Doctena','social1':'VK vs Facebook','social2':'OK vs X','msg1':'MAX vs WhatsApp','msg2':'Yandex Telemost vs Telegram',
    'gov1':'Gosuslugi vs MyGuichet.lu','gov2':'Nalogi FL vs impots.gouv','gov3':'Gosuslugi Biometria vs itsme',
}
pairs = pd.read_csv(ROOT / 'results/local/extracted_local_manifest_features and lists.csv')
cand = [c for c in pairs.columns if c.lower() in ['total_permissions_count','perm_count_local','perm_count']]
if cand:
    df = pairs[['pair_id','group',cand[0]]].rename(columns={cand[0]:'perm_count'})
else:
    local = pd.read_csv(ROOT / 'results/local/local_from_manifest.csv')
    df = pairs.merge(local[['sha256','perm_count_local']], on='sha256', how='inner')[['pair_id','group','perm_count_local']].rename(columns={'perm_count_local':'perm_count'})
wide = df.pivot_table(index='pair_id', columns='group', values='perm_count', aggfunc='first').reset_index().dropna(subset=['ru','eu'])
wide['abs_diff'] = (wide['ru']-wide['eu']).abs()
wide['pair_min'] = wide[['ru','eu']].min(axis=1)
wide = wide.sort_values(['abs_diff','pair_min'], ascending=[True,True]).reset_index(drop=True)
y = np.arange(len(wide))
ru_color, eu_color = '#3852B4', '#F08D39'
fig, ax = plt.subplots(figsize=(10.8,8.0))
for i, row in enumerate(wide.itertuples(index=False)):
    ax.plot([row.ru,row.eu],[i,i], color='#C9D1D9', linewidth=2, zorder=1)
ax.scatter(wide['ru'], y, s=70, marker='o', color=ru_color, label='RU', zorder=3)
ax.scatter(wide['eu'], y, s=70, marker='o', color=eu_color, label='EU', zorder=3)
for i, row in enumerate(wide.itertuples(index=False)):
    ax.text(row.ru-0.35, i+0.08, f'{int(row.ru)}', ha='right', va='bottom', fontsize=9, color=ru_color)
    ax.text(row.eu+0.35, i+0.08, f'{int(row.eu)}', ha='left', va='bottom', fontsize=9, color=eu_color)
ax.set_yticks(y); ax.set_yticklabels([PAIR_LABELS.get(p,p) for p in wide['pair_id']], fontsize=10)
ax.set_xlabel('Requested permissions count', fontsize=11)
ax.set_title('Total requested permissions by matched RU-EU pair', fontsize=14, pad=12)
ax.grid(axis='x', linestyle=':', linewidth=0.8, alpha=0.18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.legend(frameon=False, loc='upper center', bbox_to_anchor=(0.5, 1.02), ncol=2)
fig.tight_layout()
out = OUT / 'fig6_1_total_permissions_dumbbell.png'
fig.savefig(out, dpi=300, bbox_inches='tight'); print(out)
