
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
PAIR_LABELS={'maps':'Yandex Maps vs Google Maps','taxi':'Yandex Go Taxi vs Bolt','rail1':'RZD vs DB Navigator','rail2':'Yandex Trains vs Mobiliteit.lu',
'ecom1':'Ozon vs Amazon Shopping','ecom2':'Wildberries vs Zalando','ecom3':'Yandex Market vs bol','ecom4':'Avito vs Vinted','bank1':'Sberbank vs BGL',
'bank2':'Tinkoff vs ING Luxembourg','bank3':'Alfa Bank vs Revolut','bank4':'VTB vs BILnet','health':'EMIAS.INFO vs Doctena','social1':'VK vs Facebook',
'social2':'OK vs X','msg1':'MAX vs WhatsApp','msg2':'Yandex Telemost vs Telegram','gov1':'Gosuslugi vs MyGuichet.lu','gov2':'Nalogi FL vs impots.gouv','gov3':'Gosuslugi Biometria vs itsme'}
df=pd.read_csv(ROOT/'results/datasafety/datasafety_pairs_purpose.csv'); df.columns=[c.strip() for c in df.columns]
wide=df.pivot_table(index='pair_id',columns='region',values='shared_count',aggfunc='first').reset_index().dropna(subset=['ru','eu'])
wide['diff_ru_minus_eu']=wide['ru']-wide['eu']
wide=wide[wide['diff_ru_minus_eu']!=0].copy().sort_values('diff_ru_minus_eu', ascending=False).reset_index(drop=True)
y=np.arange(len(wide))
fig,ax=plt.subplots(figsize=(10.8,7.0))
colors=np.where(wide['diff_ru_minus_eu']>0, '#54A24B', '#9436bf')
ax.hlines(y=y, xmin=0, xmax=wide['diff_ru_minus_eu'], color=colors, linewidth=2.4)
ax.scatter(wide['diff_ru_minus_eu'], y, color=colors, s=52, zorder=3)
for i,row in enumerate(wide.itertuples(index=False)):
    x=row.diff_ru_minus_eu
    ax.text(x+(0.12 if x>=0 else -0.12), i, f'{int(x)}', va='center', ha='left' if x>=0 else 'right', fontsize=9)
ax.axvline(0,color='black',linewidth=1)
ax.set_yticks(y); ax.set_yticklabels([PAIR_LABELS.get(p,p) for p in wide['pair_id']],fontsize=10)
ax.set_xlabel('Difference in declared shared data categories (RU - EU)',fontsize=11)
ax.set_title('Difference in declared shared data categories by matched RU-EU app pair',fontsize=14,pad=10)
ax.grid(axis='x', linestyle=':', linewidth=0.8, alpha=0.18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
fig.tight_layout(); out=OUT/'fig6_12_shared_data_diff.png'; fig.savefig(out,dpi=300,bbox_inches='tight'); print(out)
